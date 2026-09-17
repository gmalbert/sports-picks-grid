"""Fetch, validate, archive, and cache all sport exports.

The script deliberately preserves the last valid cache entry when a source
returns an error.  ``data_cache/status_manifest.json`` is the authoritative
health record consumed by the dashboard and Hermes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.data_quality import (
    STATUS_EXPORT_MISSING,
    STATUS_FETCH_FAILED,
    validate_export,
)

REPOS: dict[str, str] = {
    "baseball": "baseball-predictions",
    "hockey": "hockey-predictions",
    "nba": "nba-predictions",
    "nfl": "nfl-predictions",
    "mls": "mls-predictions",
    "epl": "premier-league",
    "laliga": "la-liga",
    "bundesliga": "bundesliga",
    "ligue1": "ligue-1",
    "rugby": "rugby",
    "ncaaf": "college-football-predictions",
    "tennis": "tennis-predictions",
    "ncaab": "march-madness",
    "cricket": "cricket",
    "tabletennis": "table-tennis",
    "boxing": "boxing",
    "darts": "darts",
}

DISPLAY_NAMES = {
    "baseball": "MLB", "hockey": "NHL", "nba": "NBA", "nfl": "NFL",
    "mls": "MLS", "epl": "EPL", "laliga": "LaLiga", "bundesliga": "Bundesliga",
    "ligue1": "Ligue1", "rugby": "Rugby", "ncaaf": "NCAAF", "tennis": "Tennis",
    "ncaab": "NCAAB", "cricket": "Cricket", "tabletennis": "TableTennis",
    "boxing": "Boxing", "darts": "Darts",
}

BASE_URL = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json"
PERF_URL = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/model_performance.json"
CONTENT_URL = "https://api.github.com/repos/gmalbert/{repo}/contents/data_files/best_bets_today.json?ref=main"
CACHE_DIR = Path("data_cache")
MANIFEST_FILE = CACHE_DIR / "status_manifest.json"


def atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def fetch_json(session: requests.Session, url: str) -> tuple[Any | None, int | None, str | None]:
    try:
        response = session.get(url, timeout=20)
        if response.status_code == 404:
            return None, 404, "HTTP 404"
        response.raise_for_status()
        return response.json(), response.status_code, None
    except requests.RequestException as exc:
        return None, None, str(exc)
    except ValueError as exc:
        return None, response.status_code if "response" in locals() else None, f"invalid JSON: {exc}"


def fetch_source_sha(session: requests.Session, repo: str) -> str:
    """Read the Git blob SHA when the public Contents API is available."""
    try:
        response = session.get(CONTENT_URL.format(repo=repo), timeout=10)
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("sha", ""))
    except (requests.RequestException, ValueError):
        return ""


def fetch_one(key: str, repo: str, session: requests.Session, now: datetime) -> dict[str, Any]:
    sport = DISPLAY_NAMES[key]
    data, http_status, error = fetch_json(session, BASE_URL.format(repo=repo))
    if error:
        status = STATUS_EXPORT_MISSING if http_status == 404 else STATUS_FETCH_FAILED
        return {
            "sport": sport, "repo": repo, "status": status, "errors": [error],
            "fetched_at": now.isoformat(), "cache_file": f"{key}.json",
            "last_valid_cache": (CACHE_DIR / f"{key}.json").exists(),
        }

    record = validate_export(data, sport, now=now, http_status=http_status)
    source_commit = ""
    if not record["errors"] and record["status"] not in {STATUS_EXPORT_MISSING, STATUS_FETCH_FAILED}:
        payload = record["data"]
        source_commit = fetch_source_sha(session, repo)
        payload["meta"]["source_commit"] = source_commit
        payload["meta"]["source_repo"] = repo
        payload["meta"]["source_url"] = BASE_URL.format(repo=repo)
        atomic_write(CACHE_DIR / f"{key}.json", payload)

        archive_date = now.date().isoformat()
        atomic_write(CACHE_DIR / "history" / archive_date / f"{key}.json", payload)

    return {
        "sport": sport, "repo": repo, "status": record["status"],
        "errors": record["errors"], "generated_at": record.get("generated_at", ""),
        "source_commit": source_commit,
        "age_hours": record.get("age_hours"), "bets_count": record.get("bets_count", 0),
        "fetched_at": now.isoformat(), "cache_file": f"{key}.json",
        "last_valid_cache": (CACHE_DIR / f"{key}.json").exists(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", help="Override UTC now for deterministic tests (ISO-8601).")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "aggregation_started_at": now.isoformat(),
        "aggregation_completed_at": None,
        "source_count": len(REPOS),
        "sources": {},
    }
    session = requests.Session()
    session.headers.update({"User-Agent": "sports-picks-grid-aggregator/1.0"})
    failures = 0
    for key, repo in REPOS.items():
        result = fetch_one(key, repo, session, now)
        manifest["sources"][key] = result
        if result["status"] in {STATUS_EXPORT_MISSING, STATUS_FETCH_FAILED}:
            failures += 1
        print(f"[{result['status'].upper():16}] {result['sport']:12} — {result.get('bets_count', 0)} bets")

    manifest["aggregation_completed_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write(MANIFEST_FILE, manifest)
    print(f"\nCompleted {len(REPOS) - failures}/{len(REPOS)} source fetches successfully.")
    if failures:
        print(f"Sources with fetch/export failures: {failures} (last valid cache was preserved where available)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
