import sys
from pathlib import Path
 
from provenance_analysis import analyze_events, load_events, load_registry, with_companions

from PySide6.QtWidgets import QApplication
from user_interface import choose_session


 
PROJECT = Path(__file__).resolve().parent.parent
file_path = None
EARLY_SIGNAL_RULES = {"FETCH_TO_MEMORY", "DEPENDENCY_WRITE_ATTEMPT", "MEMORY_APPROVAL_CLAIM"}
 
 
def print_trace(events):
    print("MCP Server Call Sequence Trace")
    print("------------------------------------")
    for event in events:
        print(event["server"].upper(), event["tool_name"])
        print(f"  Task: {event['task_id']}")
        print(f"  Sequence: {event['seq']}")
        print(f"  Resource: {event.get('target_resource')}")
        print(f"  Status: {event['result_status']}")
 
 
def print_split_findings(reports):
    # A finding has a "package" key only when it is tied to a specific dependency.
    for report in reports:
        print()
        print(f"Session: {report['session_id']} | Events: {report['event_count']} | Recommendation: {report['recommendation']}")
        dependency_findings = [f for f in report["findings"] if "package" in f]
        early_signals = [f for f in report["findings"] if "package" not in f and f["rule_id"] in EARLY_SIGNAL_RULES]
        boundary_findings = [f for f in report["findings"] if "package" not in f and f["rule_id"] not in EARLY_SIGNAL_RULES]
 
        print()
        print("Dependency Findings")
        print("------------------------------------")
        if not dependency_findings:
            print("  None for this session.")
        for finding in dependency_findings:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
            print(f"    Location: {finding['path']}")
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
 
        print()
        print("Early Signals (pre-manifest)")
        print("------------------------------------")
        if not early_signals:
            print("  None for this session.")
        for finding in early_signals:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
            for resource in finding.get("fetched_resources", []):
                print(f"    Fetched resource: {resource}")
            if finding.get("resource") or finding.get("path"):
                print(f"    Resource: {finding.get('resource') or finding.get('path')}")
 
        print()
        print("Other Agent Boundary Findings")
        print("------------------------------------")
        if not boundary_findings:
            print("  None for this session.")
        for finding in boundary_findings:
            print(f"  {finding['severity'].upper()} {finding['rule_id']}: {finding['message']}")
            print(f"    Task: {finding['task_id']}")
            print(f"    Evidence sequences: {finding['evidence_seq']}")
            if finding.get("path"):
                print(f"    Resource: {finding['path']}")
 
 
def main():
    file_path = choose_session()
    if not file_path:
        sys.exit("No session selected.")
    paths = with_companions([file_path])
    try:
        events = load_events(paths)
        reports = analyze_events(events, load_registry())
    except (OSError, ValueError) as exc:
        sys.exit(f"Dependency provenance analysis failed: {exc}")
    print("Files analysed: " + ", ".join(str(path.relative_to(PROJECT)) for path in paths))
    print()
    print_trace(events)
    print_split_findings(reports)
 
 
if __name__ == "__main__":
    main()
 