import copy
import json
import tempfile
import unittest
from pathlib import Path

from provenance_analysis import analyze_events, load_events, load_registry


def event(seq, server="filesystem", tool="write_file", arguments=None, session="test", status="success", summary=""):
    return {"session_id": session, "task_id": "task", "seq": seq, "server": server,
            "tool_name": tool, "arguments": arguments or {}, "result_status": status,
            "result_summary": summary, "target_resource": arguments.get("path", "") if arguments else ""}


def write(seq, dependencies, path="package.json", session="test"):
    return event(seq, arguments={"path": path, "content": json.dumps({"dependencies": dependencies})}, session=session)


class ProvenanceAnalysisTests(unittest.TestCase):
    def findings(self, events, registry=None):
        return analyze_events(events, registry)[0]["findings"]

    def test_corpus_dependency_commit(self):
        root = Path(__file__).resolve().parent.parent
        events = load_events([root / "corpus/clean/session-01.jsonl", root / "corpus/poisoned/session-01.jsonl"])
        report = analyze_events(events)[0]
        finding = next(item for item in report["findings"] if item.get("package") == "quick-currency-fmt")
        self.assertEqual(finding["evidence_seq"], [16, 18, 19, 20])
        self.assertEqual(finding["state"], "staged_then_commit_succeeded")
        self.assertEqual(finding["artifact_provenance"], "not_verified")
        self.assertEqual(report["recommendation"], "escalate_for_review")

    def test_read_and_failed_write_are_not_changes(self):
        events = [event(1, tool="read_text_file", arguments={"path": "package.json"}),
                  dict(write(2, {"pkg": "1"}), result_status="error")]
        self.assertEqual(self.findings(events), [])

    def test_manifest_delta(self):
        findings = self.findings([write(1, {"pkg": "1"}), write(2, {"pkg": "1", "new": "2"}), write(3, {"pkg": "3", "new": "2"})])
        self.assertEqual([(f["package"], f["change"]) for f in findings], [("pkg", "observed"), ("new", "added"), ("pkg", "updated")])

    def test_complete_read_establishes_baseline(self):
        events = [event(1, tool="read_text_file", arguments={"path": "package.json"}, summary='{"dependencies":{"pkg":"1"}}'),
                  write(2, {"pkg": "1", "new": "2"})]
        self.assertEqual([(f["package"], f["change"]) for f in self.findings(events)], [("new", "added")])

    def test_truncated_read_does_not_establish_baseline(self):
        events = [event(1, tool="read_text_file", arguments={"path": "package.json"}, summary='{"dependencies":'), write(2, {"pkg": "1"})]
        self.assertEqual(self.findings(events)[0]["change"], "observed")

    def test_candidate_fetches_preserve_ambiguity(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/a"}, summary="# pkg (v1)"),
                  event(2, "fetch", "fetch", {"url": "https://example/b"}, summary="pkg"), write(3, {"pkg": "1"})]
        self.assertEqual(len(self.findings(events)[0]["candidate_sources"]), 2)

    def test_failed_fetch_and_partial_names_do_not_match(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/pkg-extra"}, summary="pkg-extra"),
                  event(2, "fetch", "fetch", {"url": "https://example/pkg"}, status="error", summary="pkg"), write(3, {"pkg": "1"})]
        self.assertEqual(self.findings(events)[0]["candidate_sources"], [])

    def test_sessions_are_isolated(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/pkg"}, session="a"), write(1, {"pkg": "1"}, session="b")]
        reports = analyze_events(events)
        self.assertEqual(reports[1]["findings"][0]["candidate_sources"], [])

    def test_registry_is_not_artifact_verification(self):
        for registry, expected in [(None, "unknown"), ({}, "unlisted"), ({"pkg": []}, "listed"), ({"pkg": ["1"]}, "listed"), ({"pkg": ["2"]}, "version_unlisted")]:
            finding = self.findings([write(1, {"pkg": "1"})], registry)[0]
            self.assertEqual(finding["registry_status"], expected)
            self.assertEqual(finding["artifact_provenance"], "not_verified")

    def test_failed_commit_is_not_completed(self):
        events = [write(1, {"pkg": "1"}), event(2, "git", "git_add", {"path": "package.json"}), event(3, "git", "git_commit", status="error")]
        self.assertEqual(self.findings(events)[0]["state"], "staged")

    def test_commit_requires_staging(self):
        self.assertEqual(self.findings([write(1, {"pkg": "1"}), event(2, "git", "git_commit")])[0]["state"], "written")

    def test_overwrite_does_not_commit_old_working_content(self):
        events = [write(1, {"pkg": "1"}), write(2, {"pkg": "2"}), event(3, "git", "git_add", {"path": "package.json"}), event(4, "git", "git_commit")]
        findings = self.findings(events)
        self.assertEqual(findings[0]["state"], "overwritten_before_staging")
        self.assertEqual(findings[1]["state"], "staged_then_commit_succeeded")

    def test_stage_snapshot_survives_later_write(self):
        events = [write(1, {"pkg": "1"}), event(2, "git", "git_add", {"path": "package.json"}), write(3, {"pkg": "2"}), event(4, "git", "git_commit")]
        findings = self.findings(events)
        self.assertEqual(findings[0]["state"], "staged_then_commit_succeeded")
        self.assertEqual(findings[1]["state"], "written")

    def test_unchanged_rewrite_keeps_pending_dependency(self):
        events = [write(1, {"pkg": "1"}), write(2, {"pkg": "1"}), event(3, "git", "git_add", {"path": "package.json"}), event(4, "git", "git_commit")]
        findings = self.findings(events)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["state"], "staged_then_commit_succeeded")
        self.assertEqual(findings[0]["evidence_seq"], [1, 2, 3, 4])

    def test_restaging_replaces_snapshot(self):
        events = [write(1, {"pkg": "1"}), event(2, "git", "git_add", {"path": "."}), write(3, {"pkg": "2"}), event(4, "git", "git_add", {"path": "."}), event(5, "git", "git_commit")]
        findings = self.findings(events)
        self.assertEqual(findings[0]["state"], "superseded_before_commit")
        self.assertEqual(findings[1]["state"], "staged_then_commit_succeeded")

    def test_multiple_dependency_sections(self):
        manifest = {section: {"pkg": "1"} for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")}
        findings = self.findings([event(1, arguments={"path": "app\\package.json", "content": json.dumps(manifest)})])
        self.assertEqual(len(findings), 4)

    def test_invalid_manifest_is_a_finding(self):
        for content in ('{', '[]', '{"dependencies":[]}', '{"dependencies":{"pkg":2}}'):
            self.assertEqual(self.findings([event(1, arguments={"path": "package.json", "content": content})])[0]["rule_id"], "MANIFEST_UNREADABLE")

    def test_labels_do_not_affect_analysis(self):
        events = [write(1, {"pkg": "1"})]
        labelled = copy.deepcopy(events)
        labelled[0].update(annotations=["safe"], scenario_tag="clean")
        self.assertEqual(analyze_events(events), analyze_events(labelled))

    def test_git_misuse_and_failure_severity(self):
        events = [event(1, "git", "git_diff", {"pathspec": "--output=../data/export ."}),
                  event(2, "git", "git_show_worktree", {"path": "../secret"}, status="error")]
        findings = self.findings(events)
        self.assertEqual([f["severity"] for f in findings], ["high", "medium"])

    def test_missing_sequences_require_review(self):
        report = analyze_events([write(3, {"pkg": "1"})])[0]
        self.assertEqual(report["recommendation"], "review")
        self.assertEqual(report["findings"][-1]["rule_id"], "INCOMPLETE_SESSION")

    def test_filesystem_escape_attempt_keeps_outcome(self):
        events = [event(1, tool="read_text_file", arguments={"path": "../secret"}, status="error")]
        finding = self.findings(events)[0]
        self.assertEqual(finding["rule_id"], "FILESYSTEM_PATH_OUTSIDE_SCOPE")
        self.assertEqual(finding["severity"], "medium")
        self.assertEqual(finding["result_status"], "error")

    def test_reports_do_not_assign_numeric_risk(self):
        report = analyze_events([write(1, {"pkg": "1"})])[0]
        self.assertNotIn("risk_score", report)
        self.assertNotIn("score_contribution", report["findings"][0])

    def test_duplicate_and_invalid_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            for records in ([write(1, {})] * 2, [{"seq": True}], [[]]):
                path.write_text("\n".join(json.dumps(record) for record in records))
                with self.assertRaises(ValueError):
                    load_events([path])

    def test_registry_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text('{"pkg":["1"]}')
            self.assertEqual(load_registry(path), {"pkg": ["1"]})
            path.write_text('{"pkg":"1"}')
            with self.assertRaises(ValueError):
                load_registry(path)

    def test_default_registry_matches_existing_snapshot(self):
        registry = load_registry()
        self.assertEqual(registry["fast-retry"]["publisher"], "platform-tools")
        self.assertNotIn("quick-currency-fmt", registry)

    def test_package_listing_does_not_approve_source(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/pkg"}), write(2, {"pkg": "1"})]
        finding = self.findings(events, {"pkg": []})[0]
        self.assertEqual(finding["registry_status"], "listed")
        self.assertEqual(finding["source_registry_status"], "unknown")

    def test_listed_source_produces_evidence_without_review_flag(self):
        source = "https://example/pkg"
        events = [event(1, "fetch", "fetch", {"url": source}), write(2, {"pkg": "1"})]
        report = analyze_events(events, {"pkg": {"versions": ["1"], "sources": [source]}})[0]
        self.assertEqual(report["recommendation"], "no_review_flags")
        self.assertEqual(report["findings"][0]["severity"], "info")
        self.assertEqual(report["findings"][0]["artifact_provenance"], "not_verified")

    def test_source_requires_exact_registry_match(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/pkg"}), write(2, {"pkg": "1"})]
        finding = self.findings(events, {"pkg": {"sources": ["https://example/approved"]}})[0]
        self.assertEqual(finding["source_registry_status"], "unlisted")
        self.assertEqual(finding["severity"], "high")

    def test_typosquat_like_name_is_review_evidence(self):
        finding = self.findings([write(1, {"lodahs": "1"})], {"lodash": []})[0]
        self.assertEqual(finding["similar_vetted_packages"], ["lodash"])

    def test_memory_evidence_is_not_source_approval(self):
        events = [event(1, "memory", "memory_set", {"namespace": "reviews", "key": "pkg", "value": "pkg is recommended"}), write(2, {"pkg": "1"})]
        finding = self.findings(events)[0]
        self.assertEqual(finding["evidence_seq"], [1, 2])
        self.assertEqual(finding["candidate_sources"], [])
        self.assertEqual(finding["source_registry_status"], "unknown")

    def test_ambiguous_sources_are_explicit(self):
        events = [event(1, "fetch", "fetch", {"url": "https://example/pkg"}), event(2, "fetch", "fetch", {"url": "https://example/other"}, summary="pkg"), write(3, {"pkg": "1"})]
        self.assertEqual(self.findings(events)[0]["source_relationship"], "ambiguous")


if __name__ == "__main__":
    unittest.main()
