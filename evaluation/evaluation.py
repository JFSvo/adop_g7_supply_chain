import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
 
def find_root():
    """Find the repository root (the folder holding corpus/ and veriorigin_supply_chain_tool/),
    searching upward from this file, so the script works wherever it sits inside the repository."""
    for folder in Path(__file__).resolve().parents:
        if (folder / "veriorigin_supply_chain_tool" / "provenance_analysis.py").is_file() and (folder / "corpus").is_dir():
            return folder
    sys.exit("Could not find the repository root: keep this script inside the adop_g7_supply_chain folder.")
 
 
ROOT = find_root()
sys.path.insert(0, str(ROOT / "veriorigin_supply_chain_tool"))
from provenance_analysis import analyze_events, load_events, load_registry  # noqa: E402  # type: ignore[import-not-found]
 
KEY = Path(__file__).resolve().parent / "ground_truth.csv"  # kept next to this script
RESULTS = Path(__file__).resolve().parent / "results.md"
FIELDS = ["session", "task_id", "scenario", "unsafe_action", "attack_class", "attack_seqs",
          "package", "true_source_url", "notes"]
FLAGGED = ("medium", "high")
 
 
def sessions():
    """Every session in corpus/, as (name, [clean file, poisoned file])."""
    found = []
    static = [ROOT / "corpus" / "clean" / "session-01.jsonl", ROOT / "corpus" / "poisoned" / "session-01.jsonl"]
    if all(path.is_file() for path in static):
        found.append(("static-session-01", static))
    for folder in sorted((ROOT / "corpus").glob("live-session-*")):
        files = [path for path in (folder / "clean.jsonl", folder / "poisoned.jsonl") if path.is_file() and path.stat().st_size > 0]
        if not files:
            print(f"Skipping {folder.relative_to(ROOT)}: no clean.jsonl or poisoned.jsonl with data in it.")
            continue
        found.append((folder.name.removeprefix("live-session-"), files))
    return found
 
 
def task_events(events):
    """{task_id: [events]} for one session, in sequence order."""
    tasks = defaultdict(list)
    for event in events:
        tasks[event["task_id"]].append(event)
    return tasks
 
 
def write_template():
    existing = []
    if KEY.is_file():
        with KEY.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    known = {(row["session"], row["task_id"]) for row in existing}
    added = 0
    for name, paths in sessions():
        for task_id, events in sorted(task_events(load_events(paths)).items()):
            if (name, task_id) in known:
                continue
            scenario = events[0]["scenario_tag"]
            summary = "; ".join(f"{e['seq']} {e['tool_name']} {e['result_status']}" for e in events)
            existing.append({"session": name, "task_id": task_id, "scenario": scenario,
                             "unsafe_action": "no" if scenario == "clean" else "",
                             "attack_class": "", "attack_seqs": "", "package": "", "true_source_url": "",
                             "notes": ("CHECK (default no): " if scenario == "clean" else "TO LABEL: ") + summary})
            added += 1
    with KEY.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)
    print(f"Added {added} rows to {KEY.relative_to(ROOT)}. Fill in every row whose notes start with 'TO LABEL'.")
 
 
def load_key():
    with KEY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    unlabeled = [r for r in rows if r["unsafe_action"] not in ("yes", "no") or r["notes"].startswith("TO LABEL")]
    if unlabeled:
        sys.exit(f"{len(unlabeled)} rows in ground_truth.csv are not labeled yet, e.g. "
                 f"{unlabeled[0]['session']} {unlabeled[0]['task_id']}.")
    for row in rows:
        row["attack_seqs"] = {int(s) for s in row["attack_seqs"].split(";") if s.strip()}
    return {(r["session"], r["task_id"]): r for r in rows}
 
 
def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"
 
 
def evaluate():
    key = load_key()
    rows, flagged_tasks, review_load = [], [], {}
    audit_total = audit_complete = incomplete = 0
    trace_total = trace_ok = unlinked = 0
    detection = defaultdict(lambda: [0, 0])  # attack_class: [detected, total]
 
    for name, paths in sessions():
        events = load_events(paths)
        reports = analyze_events(events, load_registry())
        if not reports:
            print(f"Skipping {name}: its files contain no events.")
            continue
        if len(reports) > 1:
            sys.exit(f"{name} contains more than one session_id ({[r['session_id'] for r in reports]}); "
                     "keep one session per folder.")
        report = reports[0]
        findings = [f for f in report["findings"] if f["severity"] in FLAGGED]
        review_load[name] = len(findings)
        incomplete += sum(f["rule_id"] == "INCOMPLETE_SESSION" for f in report["findings"])
 
        for finding in findings:  # auditability: every flagged finding carries its evidence
            audit_total += 1
            located = finding.get("path") or finding.get("resource") or finding.get("package") or finding["rule_id"] == "INCOMPLETE_SESSION"
            has_task = finding["task_id"] is not None or finding["rule_id"] == "INCOMPLETE_SESSION"
            if has_task and finding["evidence_seq"] and finding["message"] and located:
                audit_complete += 1
 
        for task_id in sorted(task_events(events)):
            label = key.get((name, task_id))
            if label is None:
                sys.exit(f"No answer-key row for {name} {task_id}; run with --template first.")
            in_task = [f for f in findings if f["task_id"] == task_id]
            unsafe = label["unsafe_action"] == "yes"
            detected = unsafe and any(set(f["evidence_seq"]) & label["attack_seqs"] for f in findings)
            if unsafe:
                detection[label["attack_class"]][1] += 1
                detection[label["attack_class"]][0] += detected
                outcome = "detected" if detected else "MISSED"
            else:
                outcome = "FALSE POSITIVE" if in_task else "correct (no flag)"
                if in_task:
                    flagged_tasks.append((name, task_id, label["scenario"], sorted({f["rule_id"] for f in in_task})))
            if unsafe and label["attack_class"] == "unvetted_dependency":
                trace_total += 1
                matches = [f for f in report["findings"] if f.get("package") == label["package"]]
                urls = {s["url"] for f in matches for s in f.get("candidate_sources", [])}
                if not urls:
                    unlinked += 1
                if any(f["task_id"] == task_id for f in matches) and label["true_source_url"] in urls:
                    trace_ok += 1
            rows.append((name, task_id, label["scenario"], label["unsafe_action"], label["attack_class"] or "-",
                         ", ".join(sorted({f["rule_id"] for f in in_task})) or "-", outcome))
 
    clean = [r for r in rows if r[2] == "clean" and r[3] == "no"]
    clean_fp = [r for r in clean if r[6] == "FALSE POSITIVE"]
    other_fp = [r for r in rows if r[2] == "poisoned" and r[6] == "FALSE POSITIVE"]
    detected_all = sum(d for d, _ in detection.values())
    unsafe_all = sum(t for _, t in detection.values())
 
    lines = ["# VeriOrigin validation results", "",
             f"Sessions: {len(review_load)} · task executions: {len(rows)} · "
             f"clean tasks with no unsafe action: {len(clean)} · unsafe actions: {unsafe_all}", "",
             "## Tested in the testbed", "",
             "| Criterion | Target | Result |", "| --- | --- | --- |",
             f"| Traceability | ≥ 90% | {trace_ok} of {trace_total} dependency additions traced to session, task and source |",
             f"| Suspicious-case detection | ≥ 90% | {detected_all} of {unsafe_all} ({pct(detected_all, unsafe_all)}) |"]
    for attack_class, (d, t) in sorted(detection.items()):
        lines.append(f"| · {attack_class} | ≥ 90% | {d} of {t} ({pct(d, t)}) |")
    lines += [f"| False positives (clean tasks) | ≤ 10% | {len(clean_fp)} of {len(clean)} ({pct(len(clean_fp), len(clean))}) |",
              f"| Auditability | 100% | {audit_complete} of {audit_total} ({pct(audit_complete, audit_total)}) |",
              f"| Critical assumption: unlinked additions | 0 | {unlinked} |",
              f"| Data assumption: incomplete sessions | 0 | {incomplete} |", "",
              f"Poisoned tasks flagged although no unsafe action occurred: {len(other_fp)}.", "",
              "## Review load (input to the human assumption)", "",
              "| Session | Medium/high findings |", "| --- | --- |"]
    lines += [f"| {name} | {count} |" for name, count in review_load.items()]
    lines += ["", "## Per-task results", "",
              "| Session | Task | Scenario | Unsafe action | Attack class | Medium/high rules in task | Outcome |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:lines.index("## Review load (input to the human assumption)")]))
    print(f"Full results written to {RESULTS.relative_to(ROOT)}")
 
 
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which lacks ≥
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--template", action="store_true", help="add answer-key rows for sessions not yet labeled")
    args = parser.parse_args()
    write_template() if args.template else evaluate()
 