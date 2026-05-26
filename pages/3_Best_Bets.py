"""
pages/3_Best_Bets.py — Elite and Strong picks only, rendered as cards.
"""
import pandas as pd
import streamlit as st
from datetime import date

from utils.formatter import apply_settings, sort_by_tier, TIER_EMOJI, SPORT_EMOJI, format_confidence, format_edge, format_odds, _format_time

df: pd.DataFrame = st.session_state.get("all_bets_df", pd.DataFrame())
view_df = apply_settings(df)  # today + next 7 days, filtered by user settings

today = date.today()

st.header("🔥 Best Bets")
st.caption("Elite and Strong picks across all active sports — curated for highest confidence.")

if view_df.empty:
    st.info("No picks available for today.")
    st.stop()

best = view_df[view_df["tier"].isin(["Elite", "Strong"])].copy()
best = sort_by_tier(best)

if best.empty:
    st.info("No Elite or Strong bets today. Check the Today's Picks page for Good-tier picks.")
    st.stop()

st.caption(f"{len(best)} high-confidence pick{'s' if len(best) != 1 else ''}")
st.divider()

for _, row in best.iterrows():
    tier      = row.get("tier", "Good")
    sport     = row.get("sport", "")
    badge     = TIER_EMOJI.get(tier, "⚪")
    icon      = SPORT_EMOJI.get(sport, "🎯")
    conf      = row.get("confidence")
    edge      = row.get("edge")
    odds      = row.get("odds")
    game_time = row.get("game_time")
    league    = row.get("league")
    game_date = row.get("game_date")

    with st.container(border=True):
        # Header row: tier badge | sport | date (if not today) | time
        header_parts = [f"**{badge} {tier}**", f"{icon} {sport}"]
        if league and str(league) not in ("nan", "None", ""):
            header_parts.append(f"*{league}*")
        if game_date:
            date_str = game_date.strftime("%b %d, %Y") if hasattr(game_date, "strftime") else str(game_date)
            header_parts.append(f"📆 {date_str}")
        time_str = _format_time(game_time)
        if time_str and time_str != "—":
            header_parts.append(f"🕐 {time_str}")
        st.markdown("  ·  ".join(header_parts))

        c1, c2, c3 = st.columns([2, 3, 2])

        with c1:
            st.markdown(f"**{row.get('game', 'Unknown Matchup')}**")
            st.markdown(f"Bet: `{row.get('bet_type', '')}`")
            odds_str = format_odds(odds)
            if odds_str != "—":
                st.markdown(f"Odds: `{odds_str}`")

        with c2:
            pick = row.get("pick", "")
            st.markdown(f"### {pick}")
            notes = row.get("notes")
            if notes and str(notes) not in ("nan", "None", ""):
                st.caption(str(notes))

        with c3:
            if conf is not None and not pd.isna(conf):
                st.metric("Confidence", format_confidence(conf))
            if edge is not None and not pd.isna(edge):
                st.metric("Edge", format_edge(edge))
