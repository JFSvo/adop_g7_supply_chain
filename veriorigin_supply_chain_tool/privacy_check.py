import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "veriorigin_supply_chain_tool"))
from provenance_analysis import analyze_events, load_baseline_manifest, load_events, load_registry, with_companions  # noqa: E402
from privacy_filter import filter_event, filter_report, load_allowlist  # noqa: E402

HOME = re.compile(r"(?i)(?:[a-z]:)?[\\/]+(?:users|home)[\\/]+(?!<home>)[^\\/\"'\n]+")


def field_violations(report, events, allowlist):
    report_ok, finding_ok = set(allowlist["report_fields"]) | {"privacy"}, set(allowlist["finding_fields"])
    nested, trace_ok = allowlist.get("nested_fields", {}), set(allowlist["trace_fields"])
    bad = {f"report.{k}" for k in report if k not in report_ok}
    for finding in report["findings"]:
        bad |= {f"finding.{k}" for k in finding if k not in finding_ok}
        for field, allowed in nested.items():
            for item in finding.get(field, []):
                bad |= {f"finding.{field}.{k}" for k in item if k not in allowed}
    for event in events:
        bad |= {f"trace.{k}" for k in event if k not in trace_ok}
    return bad


def main():
    allowlist = load_allowlist()
    sessions = sorted(ROOT.glob("corpus/live-session-*/poisoned.jsonl")) + [ROOT / "corpus/poisoned/session-01.jsonl"]
    print(f"Policy {allowlist['policy_version']}\n")
    print("| Session | Raw home paths | Output home paths | Non-allowlisted fields shown | Fields withheld |")
    print("| --- | --- | --- | --- | --- |")
    failures = 0
    for path in sessions:
        raw_events = load_events(with_companions([path]))
        raw_hits = len(HOME.findall(json.dumps(raw_events)))
        reports = analyze_events(raw_events, load_registry(), load_baseline_manifest())
        shown_reports = [filter_report(r) for r in reports]
        shown_events = [filter_event(e) for e in raw_events]
        output = json.dumps({"reports": shown_reports, "trace": shown_events})
        out_hits = len(HOME.findall(output))
        bad = set().union(*(field_violations(r, shown_events, allowlist) for r in shown_reports))
        withheld = sorted(set().union(*(r["privacy"]["withheld_fields"] for r in shown_reports)))
        failures += out_hits + len(bad)
        name = reports[0]["session_id"] if reports else path.parent.name
        print(f"| {name} | {raw_hits} | {out_hits} | {len(bad)} | {', '.join(withheld) or '-'} |")
    print(f"\nRESULT: {'PASS' if failures == 0 else 'FAIL'} ({len(sessions)} sessions)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())