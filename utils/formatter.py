"""
utils/formatter.py
------------------
Formatting helpers for the picks DataFrame.
"""
import copy
import pandas as pd
from datetime import date, timedelta
from datetime import datetime as _dt

TIER_EMOJI: dict[str, str] = {
    "Elite":    "🔥",
    "Strong":   "✅",
    "Good":     "➡",
    "Standard": "⚪",
}

SPORT_EMOJI: dict[str, str] = {
    "NFL":         "🏈",
    "NHL":         "🏒",
    "NBA":         "🏀",
    "MLB":         "⚾",
    "MLS":         "⚽",
    "EPL":         "⚽",
    "LaLiga":      "⚽",
    "Bundesliga":  "⚽",
    "Ligue1":      "⚽",
    "Rugby":       "🏉",
    "NCAAF":       "🏈",
    "Tennis":      "🎾",
    "NCAAB":       "🏀",
    "Cricket":     "🏏",
    "TableTennis": "🏓",
    "Boxing":      "🥊",
    "Darts":       "🎯",
}

TIER_ORDER = ["Elite", "Strong", "Good", "Standard"]

# ── Default filter settings ────────────────────────────────────────────────
# These are the out-of-the-box values. Users can override them via the
# Settings page; values are persisted in st.session_state["settings"].
DEFAULT_SETTINGS: dict = {
    "min_confidence": 0.0,
    "min_edge": 0.0,
    "tiers": ["Elite", "Strong", "Good"],
    "max_picks": {
        # High-volume sports get lower defaults to avoid flooding the dashboard.
        # All other sports default to 50 (effectively uncapped for most days).
        "__default__": 50,
        "TableTennis": 20,
        "Cricket":     20,
        "Darts":       15,
        "Boxing":      15,
        "Tennis":      30,
    },
}


def apply_settings(df: pd.DataFrame, settings: dict | None = None) -> pd.DataFrame:
    """Return a filtered DataFrame respecting the user's settings.

    Applies (in order):
    1. upcoming_bets() — only games within the next 7 days
    2. Tier filter
    3. Global min-confidence threshold
    4. Global min-edge threshold
    5. Per-sport max-picks limit (top N by confidence)

    ``settings`` defaults to ``st.session_state["settings"]`` when running
    inside Streamlit, falling back to ``DEFAULT_SETTINGS`` otherwise.
    """
    if settings is None:
        try:
            import streamlit as _st
            settings = _st.session_state.get("settings", DEFAULT_SETTINGS)
        except Exception:
            settings = DEFAULT_SETTINGS

    # 1. Time window
    out = upcoming_bets(df)
    if out.empty:
        return out

    # 2. Tiers
    tiers = settings.get("tiers", DEFAULT_SETTINGS["tiers"]) or DEFAULT_SETTINGS["tiers"]
    if "tier" in out.columns:
        out = out[out["tier"].isin(tiers)]

    # 3. Min confidence
    min_conf = float(settings.get("min_confidence", 0.0))
    if min_conf > 0 and "confidence" in out.columns:
        out = out[out["confidence"].fillna(0) >= min_conf]

    # 4. Min edge
    min_edge = float(settings.get("min_edge", 0.0))
    if min_edge > 0 and "edge" in out.columns:
        out = out[out["edge"].fillna(0) >= min_edge]

    if out.empty:
        return out

    # 5. Per-sport pick limits (top N by confidence within each sport)
    max_picks_cfg: dict = {**DEFAULT_SETTINGS["max_picks"], **settings.get("max_picks", {})}
    default_max: int = int(max_picks_cfg.get("__default__", 50))

    if "sport" in out.columns:
        pieces = []
        for sport, grp in out.groupby("sport", sort=False):
            n = int(max_picks_cfg.get(sport, default_max))
            if len(grp) > n and "confidence" in grp.columns:
                grp = grp.sort_values("confidence", ascending=False).head(n)
            pieces.append(grp)
        out = pd.concat(pieces) if pieces else out.iloc[:0]

    return out


def today_bets(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to today's bets only."""
    if df.empty or "game_date" not in df.columns:
        return df.copy() if not df.empty else df
    today = date.today()
    return df[df["game_date"] == today].copy()


def upcoming_bets(df: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    """Filter to today's and upcoming bets (within the next `days` days)."""
    if df.empty or "game_date" not in df.columns:
        return df.copy() if not df.empty else df
    today = date.today()
    cutoff = today + timedelta(days=days)
    return df[(df["game_date"] >= today) & (df["game_date"] <= cutoff)].copy()


def sort_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by tier (Elite first) then by confidence descending."""
    if df.empty:
        return df
    tier_rank = {t: i for i, t in enumerate(TIER_ORDER)}
    out = df.copy()
    out["_tier_rank"] = out["tier"].map(tier_rank).fillna(99)
    out = out.sort_values(["_tier_rank", "confidence"], ascending=[True, False])
    return out.drop(columns=["_tier_rank"])


def format_confidence(c) -> str:
    if c is None or (isinstance(c, float) and pd.isna(c)):
        return "—"
    return f"{float(c) * 100:.1f}%"


def format_edge(e) -> str:
    if e is None or (isinstance(e, float) and pd.isna(e)):
        return "—"
    raw = float(e)
    # If abs value > 1, the value is already in percentage form (e.g. 17.5 → "17.5%")
    # rather than decimal form (e.g. 0.175 → "17.5%").  No real edge can exceed ±100%.
    val = raw if abs(raw) > 1 else raw * 100
    val = max(-99.9, min(99.9, val))  # guard against any remaining data corruption
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def tier_badge(tier: str) -> str:
    emoji = TIER_EMOJI.get(tier, "⚪")
    return f"{emoji} {tier}"


def format_odds(o) -> str:
    """Format American odds integer as +135 or -140."""
    try:
        v = int(float(o))
        return f"+{v}" if v >= 0 else str(v)
    except (TypeError, ValueError):
        return "—"


def display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready DataFrame with renamed and formatted columns."""
    if df.empty:
        return df

    col_map = {
        "game_date":  "Date",
        "sport":      "Sport",
        "tier":       "Tier",
        "game":       "Game",
        "game_time":  "Time",
        "bet_type":   "Bet Type",
        "pick":       "Pick",
        "confidence": "Confidence",
        "edge":       "Edge",
        "odds":       "Odds",
        "league":     "League",
    }
    present = [c for c in col_map if c in df.columns]
    out = df[present].copy()
    out = out.rename(columns={c: col_map[c] for c in present})

    if "Sport" in out.columns:
        out["Sport"] = out["Sport"].apply(
            lambda s: f"{SPORT_EMOJI.get(s, '🎯')} {s}" if pd.notna(s) and s else s
        )
    if "Confidence" in out.columns:
        out["Confidence"] = out["Confidence"].apply(format_confidence)
    if "Edge" in out.columns:
        out["Edge"] = out["Edge"].apply(format_edge)
    if "Odds" in out.columns:
        out["Odds"] = out["Odds"].apply(format_odds)
    if "Tier" in out.columns:
        out["Tier"] = out["Tier"].apply(tier_badge)
    if "Date" in out.columns:
        out["Date"] = out["Date"].apply(
            lambda d: d.strftime("%b %d, %Y") if hasattr(d, "strftime") else (str(d) if d else "—")
        )
    if "Time" in out.columns:
        out["Time"] = out["Time"].apply(_format_time)

    return out


def _format_time(t) -> str:
    """Normalize game_time to a human-readable time string.

    Handles:
      - Plain strings already formatted: "7:05 PM ET" → returned as-is
      - ISO datetime strings: "2026-05-02T19:00:00Z" → "7:00 PM UTC"
      - NaN / None → "—"
    """
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return "—"
    s = str(t).strip()
    if not s or s in ("nan", "None"):
        return "—"
    # If it looks like an ISO datetime (contains 'T'), parse and reformat
    if "T" in s:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M"):
            try:
                dt = _dt.strptime(s.rstrip("Z").split("+")[0], fmt.rstrip("Z"))
                hour = dt.strftime("%I").lstrip("0") or "12"
                minute = dt.strftime("%M")
                ampm = dt.strftime("%p")
                time_str = f"{hour}:{minute} {ampm} UTC" if minute != "00" else f"{hour} {ampm} UTC"
                return time_str
            except ValueError:
                continue
        # fallback: strip the date portion
        return s.split("T")[1].rstrip("Z")[:5]
    return s
