"""Canonical source-status and export validation helpers.

The dashboard consumes exports from independent repositories.  Empty ``bets``
is not sufficient to describe source health, so this module keeps source
status, freshness, and validation decisions explicit and testable.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

STATUS_OK = "ok"
STATUS_NO_PICKS = "no_picks"
STATUS_OFF_SEASON = "off_season"
STATUS_PIPELINE_PENDING = "pipeline_pending"
STATUS_PIPELINE_FAILED = "pipeline_failed"
STATUS_EXPORT_MISSING = "export_missing"
STATUS_FETCH_FAILED = "fetch_failed"
STATUS_STALE = "stale"

VALID_STATUSES = {
    STATUS_OK,
    STATUS_NO_PICKS,
    STATUS_OFF_SEASON,
    STATUS_PIPELINE_PENDING,
    STATUS_PIPELINE_FAILED,
    STATUS_EXPORT_MISSING,
    STATUS_FETCH_FAILED,
    STATUS_STALE,
}

TIER_DEFINITION = "edge-v1"
TIER_THRESHOLDS = {
    "Elite": 0.06,
    "Strong": 0.03,
    "Good": 0.01,
    "Standard": 0.0,
}

# A daily source should normally be no older than this.  Off-season exports
# are allowed to be older when they explicitly identify that state.
DEFAULT_FRESHNESS_HOURS = 36
FRESHNESS_HOURS: dict[str, int] = {
    "TableTennis": 18,
    "Cricket": 18,
    "Darts": 18,
    "Tennis": 18,
}


def parse_timestamp(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def infer_status(meta: dict[str, Any], bets: list[dict[str, Any]]) -> str:
    explicit = str(meta.get("status", "")).strip().lower()
    if explicit in VALID_STATUSES:
        return explicit

    notes = str(meta.get("notes", "")).lower()
    if "off-season" in notes or "off season" in notes:
        return STATUS_OFF_SEASON
    if "not found" in notes or "pending" in notes or "may not have run" in notes:
        return STATUS_PIPELINE_PENDING
    if "failed" in notes or "error" in notes:
        return STATUS_PIPELINE_FAILED
    return STATUS_OK if bets else STATUS_NO_PICKS


def validate_export(
    data: Any,
    sport: str,
    *,
    now: datetime | None = None,
    http_status: int | None = None,
) -> dict[str, Any]:
    """Validate and normalize one source export into a status record.

    ``bets`` may contain nullable market fields because some source models do
    not publish odds or edge.  Structural fields are still required so the
    dashboard cannot silently ingest malformed rows.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    errors: list[str] = []

    if http_status == 404:
        return {"sport": sport, "status": STATUS_EXPORT_MISSING, "errors": ["HTTP 404: export file missing"]}
    if not isinstance(data, dict):
        return {"sport": sport, "status": STATUS_PIPELINE_FAILED, "errors": ["export is not a JSON object"]}

    meta = data.get("meta")
    bets = data.get("bets")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
        meta = {}
    if not isinstance(bets, list):
        errors.append("bets must be an array")
        bets = []

    generated_at = parse_timestamp(meta.get("generated_at"))
    if generated_at is None:
        errors.append("meta.generated_at must be a valid ISO-8601 timestamp")

    for index, bet in enumerate(bets):
        if not isinstance(bet, dict):
            errors.append(f"bets[{index}] must be an object")
            continue
        for field in ("game_date", "pick", "confidence", "edge", "odds", "tier"):
            if field not in bet:
                errors.append(f"bets[{index}] missing {field}")
        if bet.get("game_date") is not None:
            try:
                date.fromisoformat(str(bet["game_date"]))
            except ValueError:
                errors.append(f"bets[{index}].game_date is invalid")
        if bet.get("tier") not in {"Elite", "Strong", "Good", "Standard"}:
            errors.append(f"bets[{index}].tier is invalid")
        edge = bet.get("edge")
        if isinstance(edge, (int, float)) and edge == edge:
            edge_value = edge / 100 if abs(edge) > 1 else edge
            expected = next(
                tier for tier, threshold in TIER_THRESHOLDS.items()
                if edge_value >= threshold
            )
            if bet.get("tier") != expected:
                errors.append(
                    f"bets[{index}].tier={bet.get('tier')} disagrees with edge-v1 ({expected})"
                )

    status = infer_status(meta, bets)
    age_hours: float | None = None
    if generated_at is not None:
        age_hours = max(0.0, (now - generated_at).total_seconds() / 3600)
        threshold = FRESHNESS_HOURS.get(sport, DEFAULT_FRESHNESS_HOURS)
        if status in {STATUS_OK, STATUS_NO_PICKS} and age_hours > threshold:
            status = STATUS_STALE

    if errors:
        status = STATUS_PIPELINE_FAILED

    normalized_meta = {
        **meta,
        "sport": sport,
        "generated_at": meta.get("generated_at", ""),
        "status": status,
        "tier_definition": meta.get("tier_definition", TIER_DEFINITION),
        "lookahead_days": meta.get("lookahead_days", 7),
        "dashboard_lookahead_days": 7,
        "source_commit": meta.get("source_commit", ""),
    }
    return {
        "sport": sport,
        "status": status,
        "errors": errors,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "generated_at": normalized_meta["generated_at"],
        "bets_count": len(bets),
        "data": {"meta": normalized_meta, "bets": bets},
    }


def status_label(status: str) -> str:
    return {
        STATUS_OK: "Current",
        STATUS_NO_PICKS: "No qualifying picks today",
        STATUS_OFF_SEASON: "Off-season",
        STATUS_PIPELINE_PENDING: "Pipeline has not produced today's data",
        STATUS_PIPELINE_FAILED: "Pipeline failed",
        STATUS_EXPORT_MISSING: "Export file missing",
        STATUS_FETCH_FAILED: "Fetch failed; last valid snapshot retained",
        STATUS_STALE: "Source is stale",
    }.get(status, "Unknown source status")
