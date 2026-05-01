"""
utils/formatter.py
------------------
Formatting helpers for the picks DataFrame.
"""
import pandas as pd
from datetime import date, timedelta

TIER_EMOJI: dict[str, str] = {
    "Elite":    "🔥",
    "Strong":   "✅",
    "Good":     "➡",
    "Standard": "⚪",
}

SPORT_EMOJI: dict[str, str] = {
    "NFL":        "🏈",
    "NHL":        "🏒",
    "NBA":        "🏀",
    "MLB":        "⚾",
    "MLS":        "⚽",
    "EPL":        "⚽",
    "LaLiga":     "⚽",
    "Bundesliga": "⚽",
    "Ligue1":     "⚽",
    "Rugby":      "🏉",
    "NCAAF":      "🏈",
    "Tennis":     "🎾",
    "NCAAB":      "🏀",
}

TIER_ORDER = ["Elite", "Strong", "Good", "Standard"]


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
    val = float(e) * 100
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

    return out
