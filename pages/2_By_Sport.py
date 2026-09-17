"""
pages/2_By_Sport.py — Filter picks by sport.
"""
import pandas as pd
import streamlit as st

from utils.fetcher import REPOS, get_source_statuses
from utils.data_quality import status_label
from utils.formatter import apply_settings, sort_by_tier, display_columns, SPORT_EMOJI

df: pd.DataFrame = st.session_state.get("all_bets_df", pd.DataFrame())

st.header("🏆 Picks by Sport")

sports = list(REPOS)
statuses = get_source_statuses()

# Prefix sport names with emoji for display
sport_labels = {s: f"{SPORT_EMOJI.get(s, '🎯')} {s}" for s in sports}
label_to_sport = {v: k for k, v in sport_labels.items()}

selected_label = st.selectbox(
    "Select Sport",
    options=list(sport_labels.values()),
)
selected = label_to_sport[selected_label]

# Apply global settings first, then filter to the selected sport
all_filtered = apply_settings(df)
view_df = all_filtered[all_filtered["sport"] == selected] if "sport" in all_filtered.columns else pd.DataFrame()

# Last model run timestamp (now populated by fetcher from JSON meta)
if "generated_at" in df.columns:
    sport_gen = df[df["sport"] == selected]["generated_at"].max()
    if sport_gen and str(sport_gen) not in ("nan", "None", ""):
        st.caption(f"Last model run: {sport_gen}")

source_status = statuses.get(selected, {})
status = source_status.get("status", "unknown")
st.caption(f"Source status: {status_label(status)}")
if source_status.get("age_hours") is not None:
    st.caption(f"Source age: {source_status['age_hours']:.1f} hours")
if source_status.get("errors"):
    st.warning("; ".join(source_status["errors"]))

st.divider()

if view_df.empty:
    # Show most recent picks even if not today (off-season / no games)
    sport_df_raw = df[df["sport"] == selected] if "sport" in df.columns else pd.DataFrame()
    recent = sport_df_raw.sort_values("game_date", ascending=False).head(20) if not sport_df_raw.empty else pd.DataFrame()
    if recent.empty:
        st.info(f"No picks for {selected}. The sport may be in off-season.")
    else:
        latest_date = recent["game_date"].iloc[0]
        st.info(f"No picks for today or upcoming. Showing most recent picks ({latest_date}).")
        st.dataframe(
            display_columns(sort_by_tier(recent)),
            width='stretch',
            hide_index=True,
        )
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Picks", len(view_df))
    col2.metric("🔥 Elite",  int((view_df["tier"] == "Elite").sum()))
    col3.metric("✅ Strong", int((view_df["tier"] == "Strong").sum()))

    st.dataframe(
        display_columns(sort_by_tier(view_df)),
        width='stretch',
        hide_index=True,
    )
