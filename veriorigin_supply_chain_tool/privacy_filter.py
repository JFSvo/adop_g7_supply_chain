import json
import re
from pathlib import Path
from resources import bundled_path

# VeriOrigin privacy fileter: Designed to withold fields not on the approved allowlist (privacy_allowlist.json)
# Covers NIST privacy framework controls P-01 and P-02 

ALLOWLIST_PATH = bundled_path("veriorigin_supply_chain_tool", "privacy_allowlist.json")
REASON_CODE = "FIELD_NOT_ALLOWLISTED"

# P-02: a home folder names the developer, e.g. C:/Users/<name>/... or /home/<name>/...
HOME_FOLDER = re.compile(r"(?i)(?:[a-z]:)?[\\/](?:users|home)[\\/][^\\/\"'\n]+")


def load_allowlist(path=None):
    with Path(path or ALLOWLIST_PATH).open(encoding="utf-8") as handle:
        return json.load(handle)


def mask_identity(value):
    """Replace home-folder paths in any string, list or dict with <home> (P-02)."""
    if isinstance(value, str):
        return HOME_FOLDER.sub("<home>", value)
    if isinstance(value, list):
        return [mask_identity(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_identity(item) for key, item in value.items()}
    return value


def _keep(record, allowed, withheld, prefix=""):
    for key in record:
        if key not in allowed:
            withheld.add(prefix + key)
    return {key: mask_identity(record[key]) for key in record if key in allowed}

# Returns a copy of a report containing only allowlisted fields, with identities masked (P-01, P-02)
def filter_report(report, allowlist=None):
    allowlist = allowlist or load_allowlist()
    nested = allowlist.get("nested_fields", {})
    withheld = set()
    filtered = _keep(report, set(allowlist["report_fields"]), withheld)
    findings = []
    for finding in report.get("findings", []):
        kept = _keep(finding, set(allowlist["finding_fields"]), withheld, "finding.")
        for field, allowed in nested.items():
            if field in kept:
                kept[field] = [_keep(item, set(allowed), withheld, f"finding.{field}.") for item in finding[field]]
        findings.append(kept)
    filtered["findings"] = findings
    filtered["privacy"] = {"policy_version": allowlist["policy_version"], "reason_code": REASON_CODE,
                           "withheld_fields": sorted(withheld)}
    return filtered

# Return only the allowlisted fields of a raw log event for the trace view 
def filter_event(event, allowlist=None):
    allowlist = allowlist or load_allowlist()
    return {key: mask_identity(event[key]) for key in allowlist["trace_fields"] if key in event}