import argparse
import json
import posixpath
import re
from pathlib import Path
from urllib.parse import unquote


def load_events(paths):
    events = []
    seen = set()
    for path in paths:
        path = Path(path)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                  continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("record must be an object")
                for field in ("session_id", "task_id", "server", "tool_name", "result_status"):
                    if not isinstance(event.get(field), str) or not event[field]:
                        raise ValueError(f"invalid {field}")
                if type(event.get("seq")) is not int or event["seq"] < 1:
                    raise ValueError("invalid sequence")
                if not isinstance(event.get("arguments"), dict):
                    raise ValueError("invalid arguments")
                if event["result_status"] not in ("success", "error", "blocked"):
                    raise ValueError("invalid result status")
                if not isinstance(event.get("result_summary", ""), str):
                    raise ValueError("invalid result summary")
                identity = (event["session_id"], event["seq"])
                if identity in seen:
                    raise ValueError("duplicate session sequence")
                seen.add(identity)
                events.append(event)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    return sorted(events, key=lambda event: (event["session_id"], event["seq"]))


def load_registry(path=None):
    path = Path(path) if path is not None else Path(__file__).resolve().parent.parent / "data/mock-web/vetted-source-registry.md"
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        entries = re.findall(r"^\s*-\s+([^\s]+)\s+\(([^)]+)\)\s*$", content, re.MULTILINE)
        if not entries:
            raise ValueError("registry contains no package approval entries")
        return {package: {"publisher": publisher, "versions": [], "sources": []} for package, publisher in entries}
    registry = json.loads(content)
    if not isinstance(registry, dict):
        raise ValueError("registry must map package names to approval entries")
    for package, approval in registry.items():
        if not isinstance(package, str) or not package:
            raise ValueError("invalid registry package")
        if isinstance(approval, list):
            versions, sources = approval, []
        elif isinstance(approval, dict):
            versions, sources = approval.get("versions", []), approval.get("sources", [])
            if not isinstance(approval.get("publisher", ""), str):
                raise ValueError("invalid publisher")
        else:
            raise ValueError("invalid registry entry")
        for entries in (versions, sources):
            if not isinstance(entries, list) or not all(isinstance(entry, str) and entry for entry in entries):
                raise ValueError("registry versions and sources must be string lists")
    return registry


def resource_path(event):
    return posixpath.normpath(str(event["arguments"].get("path") or event.get("target_resource") or "").replace("\\", "/"))


def requires_scope_review(path):
    normalized = posixpath.normpath(str(path).replace("\\", "/"))
    return normalized == ".." or normalized.startswith("../") or normalized.startswith("/") or bool(re.match(r"^[A-Za-z]:", normalized))


def parse_manifest(content):
    manifest = json.loads(content)
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    dependencies = {}
    for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        entries = manifest.get(section, {})
        if not isinstance(entries, dict):
            raise ValueError(f"{section} must be an object")
        for package, version in entries.items():
            if not isinstance(version, str):
                raise ValueError(f"invalid version for {package}")
            dependencies[(section, package)] = version
    return dependencies


def check_registry(package, version, sources, registry):
    if registry is None:
        return "unknown", "unknown"
    if package not in registry:
        return "unlisted", "unknown"
    approval = registry[package]
    versions = approval if isinstance(approval, list) else approval.get("versions", [])
    approved_sources = [] if isinstance(approval, list) else approval.get("sources", [])
    status = "listed" if not versions or version in versions else "version_unlisted"
    urls = {source["url"] for source in sources}
    source_status = "unknown" if not approved_sources or not urls else "listed" if urls.issubset(set(approved_sources)) else "unlisted"
    return status, source_status


def similar_package(package, approved):
    if abs(len(package) - len(approved)) > 1:
        return False
    if len(package) == len(approved):
        differences = [index for index, (left, right) in enumerate(zip(package, approved)) if left != right]
        return len(differences) == 1 or (len(differences) == 2 and differences[1] == differences[0] + 1 and package[differences[0]] == approved[differences[1]] and package[differences[1]] == approved[differences[0]])
    shorter, longer = sorted((package, approved), key=len)
    return any(longer[:index] + longer[index + 1:] == shorter for index in range(len(longer)))


def analyze_events(events, registry=None):
    sessions = {}
    for event in sorted(events, key=lambda item: (item["session_id"], item["seq"])):
        state = sessions.setdefault(event["session_id"], {
            "findings": [], "fetches": [], "memory": [], "manifests": {}, "pending": {}, "staged": {}, "sequences": [],
        })
        state["sequences"].append(event["seq"])
        arguments = event["arguments"]
        successful = event["result_status"] == "success"
        tool = event["tool_name"]

        def add(rule, severity, message, evidence, **details):
            finding = {"rule_id": rule, "severity": severity, "task_id": event["task_id"],
                       "message": message, "evidence_seq": sorted(set(evidence)), **details}
            state["findings"].append(finding)
            return finding

        if event["server"] == "fetch" and tool == "fetch" and successful:
            state["fetches"].append(event)

        if event["server"] == "filesystem" and arguments.get("path") and requires_scope_review(arguments["path"]):
            add("FILESYSTEM_PATH_OUTSIDE_SCOPE", "high" if successful else "medium",
                "Filesystem requested an external or absolute path requiring scope review.", [event["seq"]],
                result_status=event["result_status"], path=arguments["path"])

        if event["server"] == "git":
            if tool in ("git_show_worktree", "git_init"):
                path = str(arguments.get("path") or arguments.get("target_path") or "").replace("\\", "/")
                if requires_scope_review(path):
                    add("GIT_PATH_OUTSIDE_SCOPE", "high" if successful else "medium",
                        "Git requested an external or absolute path requiring scope review.", [event["seq"]],
                        result_status=event["result_status"], path=path)
            if tool == "git_diff" and any(token.startswith("-") for token in str(arguments.get("pathspec", "")).split()):
                add("GIT_PATHSPEC_FLAGS", "high" if successful else "medium",
                    "Git pathspec contains command-line flags.", [event["seq"]], result_status=event["result_status"])
            if tool == "git_add" and successful:
                path = resource_path(event)
                for pending_path, findings in state["pending"].items():
                    if path == "." or pending_path == path or pending_path.startswith(path.rstrip("/") + "/"):
                        for previous in state["staged"].get(pending_path, []):
                            if previous not in findings:
                                previous["state"] = "superseded_before_commit"
                        state["staged"][pending_path] = list(findings)
                        for finding in findings:
                            finding["state"] = "staged"
                            finding["evidence_seq"].append(event["seq"])
            if tool == "git_commit":
                for findings in state["staged"].values():
                    for finding in findings:
                        if successful:
                            finding["state"] = "staged_then_commit_succeeded"
                        finding["evidence_seq"].append(event["seq"])
                if successful:
                    for path, findings in state["staged"].items():
                        if state["pending"].get(path) == findings:
                            state["pending"].pop(path, None)
                    state["staged"].clear()

        if event["server"] == "filesystem" and tool == "read_text_file" and successful and posixpath.basename(resource_path(event)) == "package.json":
            try:
                state["manifests"][resource_path(event)] = parse_manifest(event.get("result_summary", ""))
            except (ValueError, TypeError):
                pass

        if event["server"] == "filesystem" and tool == "write_file" and successful and posixpath.basename(resource_path(event)) == "package.json":
            path = resource_path(event)
            pending = state["pending"].get(path, [])
            try:
                dependencies = parse_manifest(arguments.get("content", ""))
            except (ValueError, TypeError) as exc:
                add("MANIFEST_UNREADABLE", "medium", str(exc), [event["seq"]], path=path)
                state["manifests"].pop(path, None)
                state["pending"][path] = []
                continue
            previous = state["manifests"].get(path)
            for previous_finding in pending:
                identity = (previous_finding["section"], previous_finding["package"])
                if dependencies.get(identity) != previous_finding["requested_version"] and previous_finding["state"] == "written":
                    previous_finding["state"] = "overwritten_before_staging"
            findings = []
            for (section, package), version in sorted(dependencies.items()):
                if previous is not None and previous.get((section, package)) == version:
                    for previous_finding in pending:
                        if previous_finding["section"] == section and previous_finding["package"] == package and previous_finding["requested_version"] == version:
                            previous_finding["evidence_seq"].append(event["seq"])
                            findings.append(previous_finding)
                    continue
                change = "observed" if previous is None else "updated" if (section, package) in previous else "added"
                pattern = re.compile(r"(?<![A-Za-z0-9@/_.-])" + re.escape(package) + r"(?![A-Za-z0-9/_.-])")
                url_pattern = re.compile(r"(?<![A-Za-z0-9@_.-])" + re.escape(package) + r"(?![A-Za-z0-9_.-])")
                candidates = [fetch for fetch in state["fetches"]
                              if pattern.search(fetch.get("result_summary", "")) or url_pattern.search(unquote(str(fetch["arguments"].get("url", ""))))]
                sources = [{"url": fetch["arguments"].get("url"), "seq": fetch["seq"], "task_id": fetch["task_id"], "timestamp": fetch.get("timestamp")} for fetch in candidates]
                status, source_status = check_registry(package, version, sources, registry)
                memories = [memory for memory in state["memory"] if pattern.search(str(memory["arguments"].get("value", "")))]
                similar = [approved for approved in (registry or {}) if approved != package and similar_package(package, approved)] if status == "unlisted" else []
                severity = "high" if status in ("unlisted", "version_unlisted") or source_status == "unlisted" else "info" if status == "listed" and source_status == "listed" else "medium"
                rule = "DEPENDENCY_NOT_VETTED" if severity == "high" else "DEPENDENCY_DOCUMENTATION_LISTED" if severity == "info" else "DEPENDENCY_PROVENANCE_UNKNOWN"
                message = f"{package} has listed documentation evidence; artifact provenance remains unverified." if severity == "info" else f"{package} requires dependency provenance review."
                finding = add(rule, severity, message,
                              [event["seq"], *[fetch["seq"] for fetch in candidates], *[memory["seq"] for memory in memories]], package=package,
                              requested_version=version, section=section, path=path, change=change,
                              state="written", registry_status=status, source_registry_status=source_status,
                              source_relationship="unknown" if not sources else "candidate" if len(sources) == 1 else "ambiguous",
                              candidate_sources=sources, similar_vetted_packages=similar,
                              memory_evidence=[{"seq": memory["seq"], "resource": memory.get("target_resource"), "task_id": memory["task_id"]} for memory in memories],
                              artifact_provenance="not_verified")
                findings.append(finding)
            state["manifests"][path] = dependencies
            state["pending"][path] = findings

        if event["server"] == "memory" and tool == "memory_set" and successful:
            state["memory"].append(event)
            value = str(arguments.get("value", ""))
            if re.search(r"\b(safe to add|vetted publisher|approved dependency)\b", value, re.IGNORECASE):
                fetches = [fetch for fetch in state["fetches"] if fetch["task_id"] == event["task_id"]]
                add("MEMORY_APPROVAL_CLAIM", "medium", "Stored approval language is an agent claim requiring independent verification.",
                    [event["seq"], *[fetch["seq"] for fetch in fetches]], resource=event.get("target_resource"))

    reports = []
    for session_id, state in sorted(sessions.items()):
        findings = state["findings"]
        sequences = state["sequences"]
        incomplete = bool(sequences and (sequences[0] != 1 or any(right != left + 1 for left, right in zip(sequences, sequences[1:]))))
        if incomplete:
            findings.append({"rule_id": "INCOMPLETE_SESSION", "severity": "medium", "task_id": None,
                             "message": "Session sequence is incomplete; missing calls may affect conclusions.", "evidence_seq": []})
        for finding in findings:
            finding["evidence_seq"] = sorted(set(finding["evidence_seq"]))
        recommendation = "escalate_for_review" if any(finding["severity"] == "high" for finding in findings) else "review" if any(finding["severity"] == "medium" for finding in findings) else "no_review_flags"
        reports.append({"session_id": session_id, "event_count": len(sequences),
                        "recommendation": recommendation, "findings": findings})
    return reports


def print_reports(reports):
    print("\nDependency Provenance Findings")
    print("------------------------------------")
    for report in reports:
        print(f"Session: {report['session_id']} | Recommendation: {report['recommendation']}")
        for finding in report["findings"]:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
            if "package" in finding:
                print(f"    Manifest: {finding['path']}")
                print(f"    Package: {finding['package']} {finding['requested_version']} | {finding['change']} | {finding['state']}")
                print(f"    Package registry: {finding['registry_status']} | Source registry: {finding['source_registry_status']}")
                print(f"    Artifact provenance: {finding['artifact_provenance']}")
                print(f"    Source relationship: {finding['source_relationship']}")
                for source in finding["candidate_sources"]:
                    print(f"    Candidate source: {source['url']} (sequence {source['seq']})")
                for memory in finding["memory_evidence"]:
                    print(f"    Memory evidence: {memory['resource']} (sequence {memory['seq']})")
                if finding["similar_vetted_packages"]:
                    print(f"    Similar vetted names requiring review: {finding['similar_vetted_packages']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        reports = analyze_events(load_events(args.paths), load_registry(args.registry))
        if args.output:
            args.output.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
        print_reports(reports)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Analysis failed: {exc}\n")


if __name__ == "__main__":
    main()