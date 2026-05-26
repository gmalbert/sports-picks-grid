"""
scripts/fetch_all_picks.py
--------------------------
Pre-fetches best_bets_today.json from every sport repo into data_cache/.
Run by the aggregator GitHub Action at 12:00 PM UTC daily.

Also fetches model_performance.json if available.

Usage:
    python scripts/fetch_all_picks.py
"""
import json
import sys
from pathlib import Path

import requests

REPOS: dict[str, str] = {
    "baseball":    "baseball-predictions",
    "hockey":      "hockey-predictions",
    "nba":         "nba-predictions",
    "nfl":         "nfl-predictions",
    "mls":         "mls-predictions",
    "epl":         "premier-league",
    "laliga":      "la-liga",
    "bundesliga":  "bundesliga",
    "ligue1":      "ligue-1",
    "rugby":       "rugby",
    "ncaaf":       "college-football-predictions",
    "tennis":      "tennis-predictions",
    "ncaab":       "march-madness",
    "cricket":     "cricket",
    "tabletennis": "table-tennis",
    "boxing":      "boxing",
    "darts":       "darts",
}

BASE_URL  = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/{filename}"
CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

failures: list[str] = []

for key, repo in REPOS.items():
    # best_bets_today.json
    url = BASE_URL.format(repo=repo, filename="best_bets_today.json")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = CACHE_DIR / f"{key}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        count = len(data.get("bets", []))
        print(f"[OK]   {key:12s} — {count} bets cached")
    except Exception as e:
        print(f"[WARN] {key:12s} — {e}")
        failures.append(key)

    # model_performance.json (optional — don't count as failure if missing)
    perf_url = BASE_URL.format(repo=repo, filename="model_performance.json")
    try:
        r = requests.get(perf_url, timeout=15)
        r.raise_for_status()
        perf_out = CACHE_DIR / f"{key}_performance.json"
        perf_out.write_text(json.dumps(r.json(), indent=2, ensure_ascii=False))
        print(f"       {key:12s} — performance data cached")
    except Exception:
        pass  # performance file is optional

print(f"\nDone. {len(REPOS) - len(failures)}/{len(REPOS)} repos fetched successfully.")
if failures:
    print(f"Failed: {', '.join(failures)}")
    # Non-zero exit only if ALL repos failed — partial failure is acceptable
    if len(failures) == len(REPOS):
        sys.exit(1)
