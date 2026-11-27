# VeriOrigin decision log: the record of each Approve/Escalate decision.

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = Path(__file__).resolve().parent.parent / "decisions" / "decision_log.jsonl"
DECISIONS = ("approve", "escalate")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")  # a role ID such as seclead-01, not a person's name

# Session folder plus file name, e.g. live-session-x/poisoned.jsonl, never the full local path
def file_label(path):
    path = Path(path)
    return f"{path.parent.name}/{path.name}"


def hash_files(paths):
    return {file_label(path): hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}


def record_decision(card, decision, reviewer_id, analyzed_paths, policy_version, log_path=None):
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    if not REVIEWER_ID.match(reviewer_id or ""):
        raise ValueError("reviewer_id must be a role ID such as seclead-01, not a name")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reviewer_id": reviewer_id,
        "decision": decision,
        "session_id": card["session_id"],
        "package": card["package"],
        "version": card["version"],
        "score": card["score"],
        "suggested_action": card["suggested_action"],
        "evidence_seq": card["evidence_seq"],
        "allowlist_version": policy_version,
        "log_sha256": hash_files(analyzed_paths),
    }
    log_path = Path(log_path or DEFAULT_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def read_decisions(log_path=None):
    log_path = Path(log_path or DEFAULT_LOG)
    if not log_path.is_file():
        return []
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


# True if the log files still match the hashes recorded with the decision."""
def logs_unchanged(entry, analyzed_paths):
    return hash_files(analyzed_paths) == entry["log_sha256"]
