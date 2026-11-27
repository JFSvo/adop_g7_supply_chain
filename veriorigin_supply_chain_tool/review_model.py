# VeriOrigin review model: one card per dependency, with an explainable 0-100 risk score.

SEVERITY_POINTS = {"high": 50, "medium": 25, "info": 0}
REGISTRY_POINTS = {"unlisted": 25, "version_unlisted": 15, "unknown": 10, "listed": 0}
SOURCE_POINTS = {"unlisted": 15, "unknown": 10, "listed": 0}
REACH_POINTS = {"staged_then_commit_succeeded": 10, "staged": 5}  # how far the change got toward the build
ESCALATE_AT, REVIEW_AT = 50, 25


# Return (score, breakdown) for the findings that concern one dependency
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