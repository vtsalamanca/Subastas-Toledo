"""Diagnóstico estructurado y no destructivo del rastreador."""
from collections import Counter
from datetime import datetime, timezone

def diagnose(status, candidates):
    sources = status.get("sources", [])
    detail = status.get("portal_details", {})
    issues = []
    for source in sources:
        state = source.get("status", "unknown")
        if state not in ("checked", "checked_announcements"):
            issues.append({"code": "SOURCE_INCOMPLETE", "source": source.get("id"), "severity": "warning", "detail": source.get("reason", state)})
        if source.get("errors"):
            issues.append({"code": "SOURCE_ERRORS", "source": source.get("id"), "severity": "error", "count": len(source["errors"])})
    if detail.get("failed", 0):
        issues.append({"code": "DETAIL_FETCH_FAILURE", "severity": "error", "count": detail["failed"]})
    if detail.get("attempted", 0) != detail.get("readable", 0):
        issues.append({"code": "DETAIL_COVERAGE_GAP", "severity": "warning",
                       "attempted": detail.get("attempted", 0), "readable": detail.get("readable", 0)})
    if not status.get("verified_listings", 0):
        issues.append({"code": "NO_VERIFIED_PROPERTIES", "severity": "warning",
                       "detail": "No equivale a ausencia de inmuebles"})
    by_state = dict(Counter(str(x.get("detalle_estado", "not_attempted")) for x in candidates))
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "complete": not issues, "issues": issues, "detail_states": by_state,
            "candidate_count": len(candidates), "verified_count": status.get("verified_listings", 0),
            "recommended_next_step": "Revisar SOURCE_ERRORS y DETAIL_FETCH_FAILURE antes de declarar cobertura"}
