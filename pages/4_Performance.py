"""
pages/4_Performance.py — Model report cards per sport.

Reads model_performance.json from each sport repo via the same GitHub raw URL pattern
used for best_bets_today.json. Falls back gracefully when data is unavailable.
"""
import pandas as pd
import streamlit as st

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
st.caption("Season-to-date win rates and ROI across all Betting Oracle models.")
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
    st.dataframe(perf_df, use_container_width=True, hide_index=True)
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
        st.link_button(f"{icon} {sport}", url, use_container_width=True)
