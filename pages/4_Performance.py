"""
pages/4_Performance.py — Model report cards per sport.

Reads model_performance.json from each sport repo via the same GitHub raw URL pattern
used for best_bets_today.json. Falls back gracefully when data is unavailable.
"""
import pandas as pd
import streamlit as st
import json
from pathlib import Path

from utils.fetcher import REPOS, load_performance
from utils.formatter import SPORT_EMOJI

SPORT_APP_URLS: dict[str, str] = {
    "MLB":        "https://baseball-predictions.streamlit.app",
    "NHL":        "https://hockey-predictions.streamlit.app",
    "NBA":        "https://nba-predictions.streamlit.app",
    "NFL":        "https://nfl-predictions.streamlit.app",
    "MLS":        "https://mls-predictions.streamlit.app",
    "EPL":        "https://premier-league-predictions.streamlit.app",
    "LaLiga":     "https://la-liga-linea.streamlit.app",
    "Bundesliga": "https://bundesliga-predictions.streamlit.app",
    "Ligue1":     "https://ligue1-predictions.streamlit.app",
    "Rugby":      "https://scrumbet.streamlit.app",
    "NCAAF":      "https://college-football-predictions.streamlit.app",
    "Tennis":     "https://tennis-predictions.streamlit.app",
    "NCAAB":      "https://march-madness-predictions.streamlit.app",
}

st.header("📊 Model Performance")
st.caption("Validated performance metrics from settled, archived picks. Unsettled picks are never counted as losses.")
st.divider()

aggregate_performance = Path("data_files/model_performance.json")
if aggregate_performance.exists():
    try:
        local_perf = json.loads(aggregate_performance.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        local_perf = {}
    if local_perf.get("status") == "unavailable":
        st.info(
            "Historical grading is configured, but no settled-results input is available yet. "
            "Accuracy and ROI will remain unpublished until results are supplied."
        )
    elif local_perf.get("groups"):
        st.subheader("Validated Archive Grading")
        local_rows = []
        for group in local_perf["groups"].values():
            local_rows.append({
                "Sport": group.get("sport", "—"),
                "Tier": group.get("tier", "—"),
                "Settled Bets": group.get("settled_bets", 0),
                "Wins": group.get("wins", 0),
                "Win Rate": f"{group['win_rate'] * 100:.1f}%" if group.get("win_rate") is not None else "—",
                "Profit (u)": f"{group.get('profit_units', 0):+.2f}",
                "ROI": f"{group['roi'] * 100:.1f}%" if group.get("roi") is not None else "—",
            })
        st.dataframe(pd.DataFrame(local_rows), width="stretch", hide_index=True)
    st.divider()

rows = []
for sport, (cache_key, repo) in REPOS.items():
    perf = load_performance(cache_key, repo)
    if not perf:
        continue
    season  = perf.get("season", "—")
    updated = perf.get("last_updated", "—")
    for bet_type, stats in perf.get("bet_types", {}).items():
        rows.append({
            "Sport":     f"{SPORT_EMOJI.get(sport, '🎯')} {sport}",
            "Season":    season,
            "Bet Type":  bet_type,
            "Bets":      stats.get("total_bets", "—"),
            "Win Rate":  f"{stats.get('win_rate', 0) * 100:.1f}%" if stats.get("win_rate") is not None else "—",
            "ROI":       f"{'+' if stats.get('roi', 0) >= 0 else ''}{stats.get('roi', 0) * 100:.1f}%" if stats.get("roi") is not None else "—",
            "Avg Edge":  f"+{stats.get('avg_edge', 0) * 100:.1f}%" if stats.get("avg_edge") is not None else "—",
            "Updated":   updated,
        })

if rows:
    perf_df = pd.DataFrame(rows)
    st.dataframe(perf_df, width='stretch', hide_index=True)
else:
    st.info(
        "Performance data is not yet available. Each sport repo needs a "
        "`data_files/model_performance.json` file committed by its nightly pipeline. "
        "See `docs/05-dashboard-app.md` for the schema."
    )

st.divider()

# ── Individual app links ──────────────────────────────────────────────────────
st.subheader("Open Individual Sport Apps")
cols = st.columns(4)
for idx, (sport, url) in enumerate(SPORT_APP_URLS.items()):
    icon = SPORT_EMOJI.get(sport, "🎯")
    with cols[idx % 4]:
        st.link_button(f"{icon} {sport}", url, width='stretch')
