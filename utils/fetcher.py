"""
utils/fetcher.py
----------------
Loads best_bets_today.json from each sport repo.

Priority order per sport:
  1. data_cache/{key}.json  — pre-fetched by the aggregator Action (no HTTP)
  2. GitHub raw URL         — live fetch, result cached by @st.cache_data(ttl=3600)
  3. Empty list             — if both fail (app degrades gracefully)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# repo_key → (cache_file_stem, github_repo_name)
REPOS: dict[str, tuple[str, str]] = {
    "MLB":        ("baseball",    "baseball-predictions"),
    "NHL":        ("hockey",      "hockey-predictions"),
    "NBA":        ("nba",         "nba-predictions"),
    "NFL":        ("nfl",         "nfl-predictions"),
    "MLS":        ("mls",         "mls-predictions"),
    "EPL":        ("epl",         "premier-league"),
    "LaLiga":     ("laliga",      "la-liga"),
    "Bundesliga": ("bundesliga",  "bundesliga"),
    "Ligue1":     ("ligue1",      "ligue-1"),
    "Rugby":      ("rugby",       "rugby"),
    "NCAAF":      ("ncaaf",       "college-football-predictions"),
    "Tennis":     ("tennis",      "tennis-predictions"),
    "NCAAB":      ("ncaab",       "march-madness"),
}

RAW_URL = (
    "https://raw.githubusercontent.com/gmalbert/{repo}/main"
    "/data_files/best_bets_today.json"
)
CACHE_DIR = Path("data_cache")


@st.cache_data(ttl=3600)
def load_all_bets() -> pd.DataFrame:
    """Load bets from all sport repos and return a flat DataFrame."""
    all_bets: list[dict] = []
    for sport, (cache_key, repo) in REPOS.items():
        bets = _load_sport(cache_key, repo)
        # Ensure sport field is set consistently from our key
        for b in bets:
            b.setdefault("sport", sport)
        all_bets.extend(bets)

    if not all_bets:
        return pd.DataFrame()

    df = pd.DataFrame(all_bets)
    df["game_date"] = pd.to_datetime(df.get("game_date"), errors="coerce").dt.date
    df["confidence"] = pd.to_numeric(df.get("confidence"), errors="coerce")
    df["edge"] = pd.to_numeric(df.get("edge"), errors="coerce")
    df["odds"] = pd.to_numeric(df.get("odds"), errors="coerce")
    # Keep generated_at as a plain string (ISO timestamp from meta)
    if "generated_at" not in df.columns:
        df["generated_at"] = ""
    return df


def _load_sport(cache_key: str, repo: str) -> list[dict]:
    """Try local cache first, then GitHub raw URL."""
    data: dict | None = None

    # 1. Local data_cache file
    local = CACHE_DIR / f"{cache_key}.json"
    if local.exists():
        try:
            data = json.loads(local.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2. GitHub raw URL
    if data is None:
        try:
            url = RAW_URL.format(repo=repo)
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []

    if not isinstance(data, dict):
        return []

    # Stamp each bet with meta fields so pages can reference them
    meta = data.get("meta", {})
    generated_at = meta.get("generated_at", "")
    meta_sport = meta.get("sport", "")

    bets = data.get("bets", [])
    for b in bets:
        b.setdefault("generated_at", generated_at)
        b.setdefault("meta_sport", meta_sport)
    return bets


def load_performance(cache_key: str, repo: str) -> dict:
    """
    Load model_performance.json for a sport repo.
    Returns an empty dict if unavailable.
    """
    local = CACHE_DIR / f"{cache_key}_performance.json"
    if local.exists():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except Exception:
            pass

    perf_url = (
        f"https://raw.githubusercontent.com/gmalbert/{repo}/main"
        "/data_files/model_performance.json"
    )
    try:
        r = requests.get(perf_url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def get_cache_age() -> str | None:
    """Return a human-readable string describing how old the local cache is."""
    if not CACHE_DIR.exists():
        return None
    files = list(CACHE_DIR.glob("*.json"))
    if not files:
        return None
    newest = max(files, key=lambda f: f.stat().st_mtime)
    mtime = datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc)
    delta = datetime.now(timezone.utc) - mtime
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m ago"
    return f"{minutes}m ago"
