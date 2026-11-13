import sys
from pathlib import Path
 
from provenance_analysis import analyze_events, load_events, load_registry, with_companions
 
from PySide6.QtWidgets import QApplication
from user_interface import VeriOrigin_UI
 
 
 
PROJECT = Path(__file__).resolve().parent.parent
file_path = None
EARLY_SIGNAL_RULES = {"FETCH_TO_MEMORY", "DEPENDENCY_WRITE_ATTEMPT", "MEMORY_APPROVAL_CLAIM"}
RECOMMENDATION_LABELS = {
    "escalate_for_review": "ESCALATE FOR REVIEW (at least one high-severity finding)",
    "review": "REVIEW (medium-severity findings only)",
    "no_review_flags": "PROCEED (no review flags)",
}
 
def on_file_selected(window, path):
    paths = with_companions([path])
    try:
        events = load_events(paths)
        reports = analyze_events(events, load_registry())
    except (OSError, ValueError) as exc:
        print(f"Dependency provenance analysis failed: {exc}")
        return
    window.set_text_sections(print_trace(events))
    window.set_text_sections(print_split_findings(reports))
 
def print_trace(events):
    findings = {"Trace": []}
    lines = findings["Trace"]
    lines.append("MCP Server Call Sequence Trace")
    lines.append("------------------------------------")
    for event in events:
        lines.append(event["server"].upper() + " " + event["tool_name"])
        lines.append(f"  Task: {event['task_id']}")
        lines.append(f"  Sequence: {event['seq']}")
        lines.append(f"  Resource: {event.get('target_resource')}")
        lines.append(f"  Status: {event['result_status']}")
    
    return findings
 
 
def print_split_findings(reports):
    # A finding has a "package" key only when it is tied to a specific dependency.
    findings = {"Dependency Findings": [], "Early Signals": [], "Boundary Findings": []}
    for report in reports:
        dependency_findings = [f for f in report["findings"] if "package" in f]
        early_signals = [f for f in report["findings"] if "package" not in f and f["rule_id"] in EARLY_SIGNAL_RULES]
        boundary_findings = [f for f in report["findings"] if "package" not in f and f["rule_id"] not in EARLY_SIGNAL_RULES]
        lines = findings["Dependency Findings"]
        # Decision summary first: this is what the supply chain lead reads before the detail.
        counts = {level: sum(f["severity"] == level for f in report["findings"]) for level in ("high", "medium", "info")}
        lines.append(f"RECOMMENDATION: {RECOMMENDATION_LABELS.get(report['recommendation'], report['recommendation'])}")
        lines.append(f"Session: {report['session_id']} | Events: {report['event_count']} | "
                     f"Findings: {counts['high']} high, {counts['medium']} medium, {counts['info']} info")
        lines.append("")
        lines.append("Dependency Findings")
        lines.append("------------------------------------")
        if not dependency_findings:
            lines.append("  None for this session.")
        for finding in dependency_findings:
            lines.append(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            lines.append(f"    Task: {finding['task_id']}")
            lines.append(f"    Evidence sequences: {finding['evidence_seq']}")
            lines.append(f"    Location: {finding['path']}")
            lines.append(f"    Package: {finding['package']} {finding['requested_version']} | {finding['change']} | {finding['state']}")
            lines.append(f"    Package registry: {finding['registry_status']} | Source registry: {finding['source_registry_status']}")
            lines.append(f"    Artifact provenance: {finding['artifact_provenance']}")
            lines.append(f"    Source relationship: {finding['source_relationship']}")
            for source in finding["candidate_sources"]:
                lines.append(f"    Candidate source: {source['url']} (sequence {source['seq']})")
            for memory in finding["memory_evidence"]:
                lines.append(f"    Memory evidence: {memory['resource']} (sequence {memory['seq']})")
            if finding["similar_vetted_packages"]:
                lines.append(f"    Similar vetted names requiring review: {finding['similar_vetted_packages']}")
 
        lines = findings["Early Signals"]
        lines.append("Early Signals (pre-manifest)")
        lines.append("------------------------------------")
        if not early_signals:
            lines.append("  None for this session.")
        for finding in early_signals:
            lines.append(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            lines.append(f"    Task: {finding['task_id']}")
            lines.append(f"    Evidence sequences: {finding['evidence_seq']}")
            for resource in finding.get("fetched_resources", []):
                lines.append(f"    Fetched resource: {resource}")
            if finding.get("resource") or finding.get("path"):
                lines.append(f"    Resource: {finding.get('resource') or finding.get('path')}")
 
        lines = findings["Boundary Findings"]
        lines.append("Other Agent Boundary Findings")
        lines.append("------------------------------------")
        if not boundary_findings:
            lines.append("  None for this session.")
        for finding in boundary_findings:
            lines.append(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            lines.append(f"    Task: {finding['task_id']}")
            lines.append(f"    Evidence sequences: {finding['evidence_seq']}")
            if finding.get("path"):
                lines.append(f"    Resource: {finding['path']}")
 
    return findings
 
 
def main():
    app = QApplication(sys.argv)
    window = VeriOrigin_UI()
    window.file_selected.connect(lambda path: on_file_selected(window, path))
    window.show()
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()
 