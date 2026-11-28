# VeriOrigin review model: one card per dependency, with an explainable 0-100 risk score.

SEVERITY_POINTS = {"high": 50, "medium": 25, "info": 0}
REGISTRY_POINTS = {"unlisted": 25, "version_unlisted": 15, "unknown": 10, "listed": 0}
SOURCE_POINTS = {"unlisted": 15, "unknown": 10, "listed": 0}
REACH_POINTS = {"staged_then_commit_succeeded": 10, "staged": 5}  # how far the change got toward the build
ESCALATE_AT, REVIEW_AT = 50, 25


# Return (score, breakdown) for the findings that concern one dependency."""
def risk_score(findings):
    severity = max((SEVERITY_POINTS.get(f.get("severity"), 0) for f in findings), default=0)
    registry = max((REGISTRY_POINTS.get(f.get("registry_status"), 10) for f in findings if "registry_status" in f), default=10)
    source = max((SOURCE_POINTS.get(f.get("source_registry_status"), 10) for f in findings if "source_registry_status" in f), default=10)
    reach = max((REACH_POINTS.get(f.get("state"), 0) for f in findings), default=0)
    breakdown = {"severity": severity, "registry": registry, "source": source, "reach": reach}
    return min(100, sum(breakdown.values())), breakdown


def suggested_action(score):
    return "escalate" if score >= ESCALATE_AT else "review" if score >= REVIEW_AT else "proceed"


# Group a report's findings by package and return one card per dependency, highest score first
def dependency_cards(report):
    grouped = {}
    for finding in report.get("findings", []):
        name = finding.get("package") or finding.get("attempted_package")
        if name:
            grouped.setdefault(name, []).append(finding)
    cards = []
    for name, findings in grouped.items():
        score, breakdown = risk_score(findings)
        main = max(findings, key=lambda f: SEVERITY_POINTS.get(f.get("severity"), 0))
        cards.append({
            "session_id": report.get("session_id"),
            "package": name,
            "version": main.get("requested_version"),
            "task_id": main.get("task_id"),
            "registry_status": main.get("registry_status", "unknown"),
            "source_registry_status": main.get("source_registry_status", "unknown"),
            "sources": [source.get("url") for source in main.get("candidate_sources", [])],
            "state": main.get("state", "attempted"),
            "evidence_seq": sorted({seq for f in findings for seq in f.get("evidence_seq", [])}),
            "rules": sorted({f["rule_id"] for f in findings}),
            "score": score,
            "breakdown": breakdown,
            "suggested_action": suggested_action(score),
        })
    return sorted(cards, key=lambda card: (-card["score"], card["package"]))


# Plain-language view for a non-technical reviewer

RULE_LABELS = {
    "DEPENDENCY_NOT_VETTED": "Dependency is not on the approved list",
    "DEPENDENCY_RECORDED_IN_MEMORY": "Agent saved an unapproved dependency to its memory",
    "DEPENDENCY_PROVENANCE_UNKNOWN": "Approved dependency, but where it came from is unknown",
    "DEPENDENCY_DOCUMENTATION_LISTED": "Approved dependency from an approved source",
    "DEPENDENCY_WRITE_ATTEMPT": "Agent tried to change the dependency list",
    "FETCH_TO_MEMORY": "Downloaded web content was saved to agent memory",
    "MEMORY_APPROVAL_CLAIM": "Agent memory claims something was approved",
    "FILESYSTEM_PATH_OUTSIDE_SCOPE": "Agent reached files outside the project",
    "GIT_PATH_OUTSIDE_SCOPE": "Agent used Git outside the project",
    "GIT_PATHSPEC_FLAGS": "Unusual Git options that could hide a command",
    "MEMORY_NAMESPACE_OUTSIDE_SCOPE": "Agent used memory outside its allowed area",
    "SENSITIVE_RESOURCE_ACCESS": "Agent opened a sensitive file",
    "SENSITIVE_DATA_TO_MEMORY": "Sensitive file content was saved to agent memory",
    "INCOMPLETE_SESSION": "The session log is incomplete",
    "MANIFEST_UNREADABLE": "The dependency list could not be read",
}

TOOL_LABELS = {
    "fetch": "Fetched page", "write_file": "Wrote file", "edit_file": "Edited file",
    "read_text_file": "Read file", "read_file": "Read file", "git_add": "Staged",
    "git_commit": "Committed", "git_init": "Created repository", "git_show": "Read from Git",
    "git_show_worktree": "Read from Git", "git_diff": "Compared files",
    "memory_set": "Saved to memory", "memory_get": "Read memory",
}

ACTION_LABELS = {"escalate": "ESCALATE", "review": "REVIEW", "proceed": "PROCEED"}


def rule_label(rule_id):
    return RULE_LABELS.get(rule_id, rule_id.replace("_", " ").capitalize())


def evidence_steps(card, events):
    """The card's evidence as ordered steps, e.g. [(16, 'Fetched page'), (18, 'Wrote file'), ...]."""
    by_seq = {event["seq"]: event for event in events}
    steps = []
    for seq in card["evidence_seq"]:
        event = by_seq.get(seq, {})
        label = TOOL_LABELS.get(event.get("tool_name"), event.get("tool_name") or "Step")
        if event.get("result_status") not in (None, "success"):
            label += " (failed)"
        steps.append((seq, label))
    return steps


def other_risks(report):
    """Medium and high findings not tied to a dependency, grouped into plain-language rows."""
    rows = {}
    for finding in report.get("findings", []):
        if finding.get("package") or finding.get("attempted_package") or finding["severity"] == "info":
            continue
        row = rows.setdefault(finding["rule_id"], {"label": rule_label(finding["rule_id"]), "severity": "medium",
                                                   "count": 0, "evidence_seq": set(), "places": set()})
        row["count"] += 1
        if finding["severity"] == "high":
            row["severity"] = "high"
        row["evidence_seq"].update(finding.get("evidence_seq", []))
        place = finding.get("path") or finding.get("resource")
        if place:
            row["places"].add(place)
    result = [dict(row, evidence_seq=sorted(row["evidence_seq"]), places=sorted(row["places"])) for row in rows.values()]
    return sorted(result, key=lambda row: (row["severity"] != "high", -row["count"], row["label"]))


def export_text(report, cards, risks, decisions, events):
    """Plain-language report for Export: the same content the reviewer sees on screen."""
    privacy = report.get("privacy", {})
    lines = [f"VeriOrigin review: session {report['session_id']}",
             f"Overall: {report['recommendation'].replace('_', ' ').upper()}",
             f"Privacy filter: {privacy.get('policy_version', 'not applied')}, "
             f"{len(privacy.get('withheld_fields', []))} field(s) withheld", "", "DEPENDENCIES"]
    if not cards:
        lines.append("  No dependency changes in this session.")
    for card in cards:
        b = card["breakdown"]
        lines += [f"  {card['package']} {card['version'] or ''}: score {card['score']}/100, "
                  f"suggested {ACTION_LABELS[card['suggested_action']]}",
                  f"    Score: severity {b['severity']} + registry {b['registry']} + source {b['source']} + reach {b['reach']}",
                  f"    Approved list: {card['registry_status']} | Source: {card['source_registry_status']}",
                  f"    Source pages: {', '.join(card['sources']) or 'none found'}",
                  "    Evidence: " + " -> ".join(f"#{seq} {label}" for seq, label in evidence_steps(card, events)),
                  "    Why: " + "; ".join(rule_label(rule) for rule in card["rules"])]
    lines += ["", "OTHER RISKS"]
    if not risks:
        lines.append("  None.")
    for risk in risks:
        lines.append(f"  {risk['severity'].upper()} {risk['label']} (x{risk['count']}), "
                     f"evidence {', '.join(f'#{s}' for s in risk['evidence_seq'])}")
    lines += ["", "DECISIONS"]
    mine = [d for d in decisions if d["session_id"] == report["session_id"]]
    if not mine:
        lines.append("  No decisions recorded yet.")
    for d in mine:
        lines.append(f"  {d['timestamp']} {d['reviewer_id']}: {d['decision'].upper()} {d['package']} (score {d['score']})")
    return "\n".join(lines)
