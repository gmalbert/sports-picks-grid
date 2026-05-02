"""
pages/2_By_Sport.py — Filter picks by sport.
"""
import pandas as pd
import streamlit as st

from utils.formatter import upcoming_bets, sort_by_tier, display_columns, SPORT_EMOJI

df: pd.DataFrame = st.session_state.get("all_bets_df", pd.DataFrame())

st.header("🏆 Picks by Sport")

if df.empty:
    st.info("No data loaded. Use the Refresh button in the sidebar.")
    st.stop()

sports = sorted(df["sport"].dropna().unique())
if not sports:
    st.info("No sports data available.")
    st.stop()

# Prefix sport names with emoji for display
sport_labels = {s: f"{SPORT_EMOJI.get(s, '🎯')} {s}" for s in sports}
label_to_sport = {v: k for k, v in sport_labels.items()}

selected_label = st.selectbox(
    "Select Sport",
    options=list(sport_labels.values()),
)
selected = label_to_sport[selected_label]

sport_df  = df[df["sport"] == selected]
view_df   = upcoming_bets(sport_df)  # today + next 7 days

# Last model run timestamp (now populated by fetcher from JSON meta)
if "generated_at" in df.columns:
    sport_gen = df[df["sport"] == selected]["generated_at"].max()
    if sport_gen and str(sport_gen) not in ("nan", "None", ""):
        st.caption(f"Last model run: {sport_gen}")

st.divider()

if view_df.empty:
    # Show most recent picks even if not today (off-season / no games)
    recent = sport_df.sort_values("game_date", ascending=False).head(20) if not sport_df.empty else pd.DataFrame()
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
