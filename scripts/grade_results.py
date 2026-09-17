"""Grade archived picks against settled results.

Input is intentionally provider-neutral.  Supply ``data_files/results.json``
or ``data_files/results.csv`` with rows containing ``sport``, ``game_date``,
``game``, ``pick``, and ``outcome`` (win/loss/push/void).  Optional ``odds``
uses American odds and is used to calculate flat-stake profit.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARCHIVE_DIR = Path("data_cache/history")
RESULTS_JSON = Path("data_files/results.json")
RESULTS_CSV = Path("data_files/results.csv")
OUTPUT = Path("data_files/graded_results.json")
PERFORMANCE = Path("data_files/model_performance.json")


def write_unavailable() -> None:
    PERFORMANCE.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE.write_text(json.dumps({
        "status": "unavailable",
        "grading": "flat-1u",
        "reason": "No settled results input was supplied.",
        "groups": {},
    }, indent=2) + "\n", encoding="utf-8")
    OUTPUT.write_text(json.dumps({
        "status": "unavailable",
        "results": [],
    }, indent=2) + "\n", encoding="utf-8")


def load_results() -> list[dict[str, Any]]:
    if RESULTS_JSON.exists():
        data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("results", [])
    if RESULTS_CSV.exists():
        with RESULTS_CSV.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    return []


def profit(odds: Any, outcome: str) -> float:
    if outcome in {"push", "void"}:
        return 0.0
    if outcome != "win":
        return -1.0
    try:
        value = float(odds)
    except (TypeError, ValueError):
        return 0.0
    return value / 100 if value > 0 else 100 / abs(value)


def archive_rows() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(ARCHIVE_DIR.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("meta", {})
        for bet in payload.get("bets", []):
            rows.append({
                **bet,
                "sport": meta.get("sport", path.stem),
                "published_at": meta.get("generated_at", ""),
                "archive_date": path.parent.name,
            })
    return rows


def main() -> int:
    results = load_results()
    if not results:
        write_unavailable()
        print("No settled results found; no performance metrics were published.")
        return 0
    by_key = {(str(r.get("sport")), str(r.get("game_date")), str(r.get("game")), str(r.get("pick"))): r for r in results}
    graded = []
    for bet in archive_rows():
        key = (str(bet.get("sport")), str(bet.get("game_date")), str(bet.get("game")), str(bet.get("pick")))
        result = by_key.get(key)
        if not result:
            continue
        outcome = str(result.get("outcome", "")).lower()
        if outcome not in {"win", "loss", "push", "void"}:
            continue
        graded.append({
            **bet,
            "outcome": outcome,
            "settled_at": result.get("settled_at", ""),
            "closing_odds": result.get("closing_odds"),
            "profit_units": profit(bet.get("odds"), outcome),
        })

    grouped = defaultdict(list)
    for row in graded:
        grouped[(row.get("sport"), row.get("tier"))].append(row)
    performance = {"generated_at": datetime.now(timezone.utc).isoformat(), "grading": "flat-1u", "groups": {}}
    for (sport, tier), rows in sorted(grouped.items()):
        settled = [row for row in rows if row["outcome"] in {"win", "loss"}]
        wins = sum(row["outcome"] == "win" for row in settled)
        units = sum(row["profit_units"] for row in rows)
        key = f"{sport}:{tier}"
        performance["groups"][key] = {
            "sport": sport, "tier": tier, "total_bets": len(rows),
            "settled_bets": len(settled), "wins": wins,
            "win_rate": wins / len(settled) if settled else None,
            "profit_units": round(units, 4),
            "roi": round(units / len(rows), 4) if rows else None,
        }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"results": graded}, indent=2) + "\n", encoding="utf-8")
    PERFORMANCE.write_text(json.dumps(performance, indent=2) + "\n", encoding="utf-8")
    print(f"Graded {len(graded)} settled picks across {len(performance['groups'])} groups.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
