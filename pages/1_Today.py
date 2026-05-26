"""
pages/1_Today.py — Today's Picks across all sports.
"""
import pandas as pd
import streamlit as st
from datetime import date

from utils.formatter import apply_settings, sort_by_tier, display_columns

df: pd.DataFrame = st.session_state.get("all_bets_df", pd.DataFrame())
view_df = apply_settings(df)  # today + up to 7 days ahead, filtered by user settings

today = date.today()
today_count = int((view_df["game_date"] == today).sum()) if not view_df.empty else 0
future_count = int((view_df["game_date"] > today).sum()) if not view_df.empty else 0

st.header(f"📅 Today's Picks — {today.strftime('%A, %B %d, %Y')}")
if future_count:
    st.caption(f"{today_count} pick{'s' if today_count != 1 else ''} today · {future_count} upcoming")

if view_df.empty:
    st.info(
        "No picks available for today. Models may not have run yet, "
        "or all sports are currently in their off-season."
    )
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Picks", len(view_df))
col2.metric("🔥 Elite",   int((view_df["tier"] == "Elite").sum()))
col3.metric("✅ Strong",  int((view_df["tier"] == "Strong").sum()))
col4.metric("Sports Active", int(view_df["sport"].nunique()))

st.divider()

# ── Picks by tier tabs ────────────────────────────────────────────────────────
tab_elite, tab_strong, tab_good, tab_all = st.tabs(
    ["🔥 Elite", "✅ Strong", "➡ Good", "All Picks"]
)

sorted_df  = sort_by_tier(view_df)
display_df = display_columns(sorted_df)

with tab_elite:
    elite = display_df[display_df["Tier"].str.contains("Elite", na=False)]
    if elite.empty:
        st.info("No Elite picks today.")
    else:
        st.dataframe(elite, width='stretch', hide_index=True)

with tab_strong:
    strong = display_df[display_df["Tier"].str.contains("Strong", na=False)]
    if strong.empty:
        st.info("No Strong picks today.")
    else:
        st.dataframe(strong, width='stretch', hide_index=True)

with tab_good:
    good = display_df[display_df["Tier"].str.contains("Good", na=False)]
    if good.empty:
        st.info("No Good picks today.")
    else:
        st.dataframe(good, width='stretch', hide_index=True)

with tab_all:
    if display_df.empty:
        st.info("No picks today.")
    else:
        st.dataframe(display_df, width='stretch', hide_index=True)
