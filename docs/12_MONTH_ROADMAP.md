# Sports Picks Grid — 12-Month Feature Roadmap

> Generated: 2026-07-31 | Horizon: August 2026 – July 2027

---

## Executive Summary

This roadmap transforms Sports Picks Grid from a read-only aggregator dashboard
into an intelligent betting portfolio manager with cross-sport correlation analysis,
user preference tracking, parlay builder, model performance leaderboards,
and an AI-powered daily briefing system.

---

## Q1 (Aug–Oct 2026) — Data Quality & User Experience

### Feature 1 — Data Freshness & Health Monitor

Real-time dashboard showing each sport repo's data freshness, last update time,
and data quality score. Alert when any sport is stale > 24 hours.

```python
# utils/health_monitor.py
import pandas as pd, requests
from datetime import datetime, timedelta
from utils.fetcher import REPOS

def check_all_sources_health() -> pd.DataFrame:
    """Check freshness and quality of all sport data sources."""
    rows = []
    for sport, (cache_key, repo_name) in REPOS.items():
        from utils.fetcher import _load_sport
        data = _load_sport(sport, cache_key, repo_name)
        if data is None or data.empty:
            status = "❌ NO DATA"
            freshness_hours = None
        else:
            gen_at = data.get("generated_at", pd.Series()).iloc[0] if "generated_at" in data.columns else None
            if gen_at:
                age = (datetime.utcnow() - pd.Timestamp(gen_at)).total_seconds() / 3600
                freshness_hours = round(age, 1)
                status = "✅ FRESH" if age < 24 else ("⚠️ STALE" if age < 48 else "❌ VERY STALE")
            else:
                freshness_hours = None
                status = "⚠️ NO TIMESTAMP"
        rows.append({
            "sport": sport, "status": status,
            "bets": len(data) if data is not None else 0,
            "freshness_hours": freshness_hours,
            "repo": repo_name,
        })
    return pd.DataFrame(rows)
```

### Feature 2 — Cross-Sport Correlation Warning

Detect when user has selected bets that are correlated (e.g., same
underdog team's ML + total — scoring correlation is high).

```python
# utils/correlation_detector.py
import pandas as pd
from itertools import combinations

KNOWN_CORRELATIONS = [
    ("MLB_moneyline", "MLB_total_over", 0.55),
    ("NFL_spread", "NFL_moneyline", 0.85),
    ("NBA_total_over", "NBA_moneyline_favorite", 0.40),
]

def detect_correlated_bets(picks: list[dict]) -> list[dict]:
    """Flag potentially correlated bet pairs."""
    warnings = []
    for pick_a, pick_b in combinations(picks, 2):
        for sport_bet1, sport_bet2, corr in KNOWN_CORRELATIONS:
            sport = pick_a.get("sport", "")
            if (sport == pick_b.get("sport") and
                sport_bet1.split("_")[1] in pick_a.get("bet_type", "") and
                sport_bet2.split("_")[1] in pick_b.get("bet_type", "") and
                pick_a.get("game") == pick_b.get("game")):
                warnings.append({
                    "pick_a": f"{pick_a['sport']} {pick_a['game']} {pick_a['bet_type']}",
                    "pick_b": f"{pick_b['sport']} {pick_b['game']} {pick_b['bet_type']}",
                    "correlation": corr,
                    "warning": f"These bets are ~{corr:.0%} correlated. Parlay value is reduced.",
                })
    return warnings
```

### Feature 3 — User Personalization (Preferred Sports & Tiers)

Allow users to set preferred sports, minimum edge thresholds, and
tier filters. Persist preferences via st.session_state + local storage.

```python
# utils/user_preferences.py
import streamlit as st
import json

DEFAULT_PREFS = {
    "preferred_sports": ["MLB", "NFL", "NBA", "NHL"],
    "min_edge": 0.03,
    "min_tier": "Good",
    "preferred_bet_types": ["moneyline", "spread", "total"],
    "show_elite_only": False,
}

def load_user_preferences() -> dict:
    if "user_prefs" not in st.session_state:
        st.session_state["user_prefs"] = DEFAULT_PREFS.copy()
    return st.session_state["user_prefs"]

def render_preferences_sidebar() -> dict:
    prefs = load_user_preferences()
    with st.sidebar.expander("⚙️ My Preferences", expanded=False):
        from utils.fetcher import REPOS
        prefs["preferred_sports"] = st.multiselect(
            "Sports", list(REPOS.keys()), default=prefs["preferred_sports"]
        )
        prefs["min_edge"] = st.slider("Min Edge %", 0, 15, int(prefs["min_edge"] * 100)) / 100
        prefs["show_elite_only"] = st.checkbox("Elite Picks Only", prefs["show_elite_only"])
    st.session_state["user_prefs"] = prefs
    return prefs
```

### Feature 4 — Smart Parlay Builder (Cross-Sport)

Enable users to build cross-sport parlays from today's picks.
Calculate combined probability, implied odds, and EV.

```python
# pages/parlay_builder.py
import streamlit as st, pandas as pd, numpy as np
from utils.formatter import upcoming_bets, sort_by_tier, format_odds

def render_parlay_builder() -> None:
    st.title("🎰 Parlay Builder")
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty:
        st.info("No picks available.")
        return

    today_df = upcoming_bets(df)
    elite = today_df[today_df["tier"].isin(["Elite", "Strong"])]

    selected = st.multiselect(
        "Add legs to parlay",
        options=[f"{r['sport']} | {r['game']} | {r['pick']} ({r['tier']})"
                 for _, r in elite.iterrows()],
        max_selections=8,
    )

    if len(selected) >= 2:
        legs = elite.iloc[[i for i, s in enumerate(
            [f"{r['sport']} | {r['game']} | {r['pick']} ({r['tier']})"
             for _, r in elite.iterrows()]
        ) if s in selected]]

        combined_prob = np.prod(legs["confidence"].clip(0.01, 0.99).values)
        # Estimate combined decimal odds
        dec_odds = np.prod(
            legs["odds"].apply(
                lambda o: (abs(o) / 100 + 1) if o < 0 else (o / 100 + 1)
            ).values
        )
        ev = combined_prob * dec_odds - 1.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Combined Probability", f"{combined_prob:.2%}")
        col2.metric("Parlay Payout", f"{dec_odds:.1f}x")
        col3.metric("Expected Value", f"{ev:+.2%}")

        if ev > 0:
            st.success("✅ Positive EV parlay!")
        else:
            st.warning("⚠️ Negative EV — proceed with caution.")
```

### Feature 5 — Model Accuracy Leaderboard (Across Sports)

Track which sport models are performing best by win rate, ROI, and
calibration error. Display a cross-sport performance league table.

```python
# pages/model_leaderboard.py
import streamlit as st, pandas as pd, plotly.express as px

def render_model_leaderboard() -> None:
    st.title("🏆 Model Performance Leaderboard")
    # Load performance data from each sport's best_bets_today.json meta
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty or "settled" not in df.columns:
        st.info("Performance data accumulates as picks are settled.")
        return

    settled = df[df["settled"] == True]
    if settled.empty:
        return

    by_sport = (
        settled.groupby("sport")
        .agg(
            picks=("game", "count"),
            win_rate=("win", "mean"),
            avg_edge=("edge", "mean"),
            roi=("pnl", lambda x: x.sum() / len(x)),
        )
        .reset_index()
        .sort_values("roi", ascending=False)
    )

    st.dataframe(
        by_sport.style.format({
            "win_rate": "{:.1%}", "avg_edge": "{:+.1%}", "roi": "{:+.3f}"
        }),
        width="stretch",
    )
    fig = px.bar(by_sport, x="sport", y="roi", color="win_rate",
                 color_continuous_scale="RdYlGn", template="plotly_dark",
                 title="ROI by Sport Model")
    st.plotly_chart(fig, width="stretch")
```

---

## Q2 (Nov 2026 – Jan 2027) — Intelligence Layer

### Feature 6 — Daily AI Briefing (GPT-4o-mini)

Generate a daily 200-word betting briefing: top picks with context,
cross-sport themes, and risk warnings.

```python
# utils/ai_briefing.py
import os, json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

BRIEFING_TEMPLATE = """
You are a sharp sports betting analyst. Today is {date}.
Here are today's top model picks across all sports:

{picks_summary}

Write a 150-word daily briefing covering:
1. Top 2-3 high-confidence bets with brief reasoning
2. Any notable injury/lineup news affecting picks
3. One risk to watch today

Style: direct, confident, data-driven. No hedging.
"""

def generate_daily_briefing(picks: pd.DataFrame, date: str) -> str:
    top_picks = picks.nlargest(5, "edge")[["sport", "game", "pick", "edge", "tier"]]
    summary = "\n".join(
        f"- {r['sport']}: {r['pick']} ({r['tier']}, edge {r['edge']:+.1%})"
        for _, r in top_picks.iterrows()
    )
    prompt = BRIEFING_TEMPLATE.format(date=date, picks_summary=summary)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250, temperature=0.5,
    )
    return resp.choices[0].message.content
```

### Feature 7 — Weather Impact Badges

When weather data is available, display a badge on NFL/MLB/Golf picks
indicating if weather is a significant factor (🌧️ Wind/Rain alert).

```python
# utils/weather_badges.py
import requests, os

OUTDOOR_SPORTS = {"MLB", "NFL", "Golf", "NCAAF"}

def get_weather_badge(game: dict, sport: str) -> str | None:
    if sport not in OUTDOOR_SPORTS:
        return None
    # Extract venue/location from game data
    venue_weather = game.get("weather_risk")
    if venue_weather is None:
        return None
    if venue_weather > 70:
        return "🌧️ High weather impact"
    elif venue_weather > 40:
        return "🌬️ Moderate wind"
    return None
```

### Feature 8 — Weekly Performance Summary Email

Send a weekly email summarizing all picks from the past week: wins,
losses, best model, worst model, and ROI breakdown.

```python
# scripts/weekly_summary_email.py
import smtplib, os, pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta

def send_weekly_summary(picks_history: pd.DataFrame, recipients: list[str]) -> None:
    last_week = picks_history[
        picks_history["date"] >= (date.today() - timedelta(days=7)).isoformat()
    ]
    if last_week.empty:
        return

    by_sport = (
        last_week.groupby("sport")
        .agg(bets=("game", "count"), wins=("win", "sum"), pnl=("pnl", "sum"))
        .reset_index()
    )
    total_pnl = last_week["pnl"].sum()

    rows_html = "".join(
        f"<tr><td>{r['sport']}</td><td>{r['bets']}</td>"
        f"<td>{r['wins']}/{r['bets']}</td>"
        f"<td style='color:{'green' if r['pnl']>0 else 'red'}'>{r['pnl']:+.2f}u</td></tr>"
        for _, r in by_sport.iterrows()
    )
    html = f"""<html><body>
    <h2>📊 Sports Picks Grid — Weekly Summary</h2>
    <h3>Total P&L: <span style="color:{'green' if total_pnl>0 else 'red'}">{total_pnl:+.2f}u</span></h3>
    <table border="1" cellpadding="8">
      <tr><th>Sport</th><th>Picks</th><th>Record</th><th>P&L</th></tr>
      {rows_html}
    </table>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Weekly Picks Summary ({date.today().isoformat()})"
    msg["From"] = os.environ["SMTP_FROM"]
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.sendmail(msg["From"], recipients, msg.as_string())
```

### Feature 9 — Value Calendar (Next 7 Days)

Extend the date window to 7 days and show a calendar view of upcoming
high-edge picks by day. Click a day to see that day's picks.

```python
# pages/value_calendar.py
import streamlit as st, pandas as pd
from datetime import date, timedelta
from utils.formatter import upcoming_bets, tier_badge

def render_value_calendar() -> None:
    st.title("📅 7-Day Value Calendar")
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty:
        return

    today = date.today()
    cols = st.columns(7)
    for i, col in enumerate(cols):
        day = today + timedelta(days=i)
        day_picks = df[df["game_date"] == day.isoformat()]
        elite = day_picks[day_picks["tier"] == "Elite"]
        with col:
            st.markdown(f"**{day.strftime('%a %d')}**")
            st.markdown(f"🔥 {len(elite)} Elite")
            st.markdown(f"✅ {len(day_picks[day_picks['tier']=='Strong'])} Strong")
            if st.button("View", key=f"day_{i}"):
                st.session_state["selected_date"] = day.isoformat()
```

### Feature 10 — Unit Bet Tracker (Personal ROI)

Let users log their own bets with stakes. Track personal ROI vs model ROI.
Display cumulative P&L chart and comparison.

```python
# pages/my_tracker.py
import streamlit as st, pandas as pd, plotly.express as px
from datetime import date

def render_my_tracker() -> None:
    st.title("💰 My Bet Tracker")
    if "my_bets" not in st.session_state:
        st.session_state["my_bets"] = []

    with st.form("log_bet"):
        col1, col2, col3 = st.columns(3)
        game = col1.text_input("Game/Event")
        pick = col2.text_input("Pick")
        odds = col3.number_input("Odds", value=-110)
        stake = st.number_input("Stake ($)", value=25.0)
        outcome = st.selectbox("Outcome", ["Pending", "Win", "Loss", "Push"])
        if st.form_submit_button("Log Bet"):
            pnl = 0.0
            if outcome == "Win":
                pnl = stake * ((100/abs(odds)+1) if odds < 0 else (odds/100+1)) - stake
            elif outcome == "Loss":
                pnl = -stake
            st.session_state["my_bets"].append({
                "date": str(date.today()), "game": game, "pick": pick,
                "odds": odds, "stake": stake, "outcome": outcome, "pnl": pnl
            })

    if st.session_state["my_bets"]:
        df = pd.DataFrame(st.session_state["my_bets"])
        df["cum_pnl"] = df["pnl"].cumsum()
        col1, col2 = st.columns(2)
        col1.metric("Total P&L", f"${df['pnl'].sum():+.2f}")
        col2.metric("Win Rate", f"{(df['outcome']=='Win').mean():.1%}")
        fig = px.line(df, x=df.index, y="cum_pnl",
                      title="My Cumulative P&L", template="plotly_dark")
        st.plotly_chart(fig, width="stretch")
```

---

## Q3 (Feb–Apr 2027) — Visual Analytics

### Feature 11 — Edge Distribution Heatmap (Sport × Tier)

Visualize the distribution of edges across sports and tiers as a heatmap.
Identify which sports consistently generate the most value.

```python
# pages/edge_heatmap.py
import streamlit as st, plotly.express as px, pandas as pd

def render_edge_heatmap() -> None:
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty:
        return
    pivot = (
        df.groupby(["sport", "tier"])["edge"]
        .mean()
        .reset_index()
        .pivot(index="sport", columns="tier", values="edge")
        .fillna(0)
    )
    fig = px.imshow(pivot * 100, color_continuous_scale="YlOrRd",
                    title="Average Edge % by Sport & Tier",
                    template="plotly_dark", text_auto=".1f")
    st.plotly_chart(fig, width="stretch")
```

### Feature 12 — Pick Volume Over Time Chart

Track how many picks each sport generates daily/weekly. Identify slow
periods (offseason) vs peak periods.

```python
# pages/pick_volume.py
import streamlit as st, plotly.express as px, pandas as pd

def render_pick_volume() -> None:
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty or "generated_at" not in df.columns:
        return
    df["date"] = pd.to_datetime(df["generated_at"]).dt.date
    volume = df.groupby(["date", "sport"]).size().reset_index(name="picks")
    fig = px.area(volume, x="date", y="picks", color="sport",
                   title="Daily Pick Volume by Sport", template="plotly_dark")
    st.plotly_chart(fig, width="stretch")
```

### Feature 13 — Confidence Distribution per Sport

Show histogram of model confidence (0.50–1.00) for each sport's picks.
Well-calibrated models should show a spread; overfit models cluster at extremes.

```python
# pages/confidence_dist.py
import streamlit as st, plotly.express as px

def render_confidence_distributions() -> None:
    df = st.session_state.get("all_bets_df", pd.DataFrame())
    if df.empty:
        return
    sport = st.selectbox("Select Sport", sorted(df["sport"].unique()))
    sport_df = df[df["sport"] == sport]
    fig = px.histogram(sport_df, x="confidence", nbins=20, color="tier",
                        title=f"{sport} Confidence Distribution",
                        template="plotly_dark")
    st.plotly_chart(fig, width="stretch")
```

### Feature 14 — Daily Briefing Card on Home Page

Add a visually prominent "Today's Best Bet" card to the home page.
Pull the single highest-edge Elite pick across all sports.

```python
# pages/1_Today.py (add to top of render)
def render_top_pick_card(df: pd.DataFrame) -> None:
    best = df[df["tier"] == "Elite"].nlargest(1, "edge")
    if best.empty:
        return
    r = best.iloc[0]
    with st.container(border=True):
        st.markdown("### 🔥 Today's Best Pick")
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(f"**{r['sport']}**")
        col2.markdown(f"**{r['game']}**")
        col3.metric("Pick", r["pick"])
        col4.metric("Edge", f"{r['edge']:+.1%}")
        st.caption(f"Odds: {r.get('odds', 'N/A')} | Model Conf: {r.get('confidence', 0):.1%} | {r.get('notes', '')}")
```

### Feature 15 — Sport Season Calendar

Display which sports are in-season vs off-season. When a sport enters
its season, re-enable its data feed. Prevents stale picks from appearing.

```python
# utils/season_calendar.py
from datetime import date

SEASON_WINDOWS = {
    "MLB":    [(date(2026, 3, 26), date(2026, 10, 5))],
    "NFL":    [(date(2026, 9, 7), date(2027, 2, 8))],
    "NBA":    [(date(2026, 10, 21), date(2027, 6, 20))],
    "NHL":    [(date(2026, 10, 8), date(2027, 6, 25))],
    "NCAAF":  [(date(2026, 8, 27), date(2027, 1, 12))],
    "NCAAB":  [(date(2026, 11, 4), date(2027, 4, 7))],
    "Golf":   [(date(2026, 1, 1), date(2026, 12, 31))],
    "Tennis": [(date(2026, 1, 1), date(2026, 12, 31))],
    "EPL":    [(date(2026, 8, 15), date(2027, 5, 30))],
    "MLS":    [(date(2026, 2, 27), date(2026, 12, 7))],
    "Cricket": [(date(2026, 1, 1), date(2026, 12, 31))],
}

def is_in_season(sport: str, as_of: date | None = None) -> bool:
    as_of = as_of or date.today()
    windows = SEASON_WINDOWS.get(sport, [])
    return any(start <= as_of <= end for start, end in windows)

def filter_in_season_sports(sports: list[str]) -> list[str]:
    return [s for s in sports if is_in_season(s)]
```

---

## Q4 (May–Jul 2027) — Automation & Platform

### Feature 16 — Discord Bot Integration

Post daily picks to a Discord server via webhook. Format as rich embeds
with sport emoji, pick details, and tier badge.

```python
# scripts/discord_bot.py
import requests, os, pandas as pd
from utils.formatter import tier_badge

SPORT_EMOJI = {
    "MLB": "⚾", "NFL": "🏈", "NBA": "🏀", "NHL": "🏒",
    "Golf": "⛳", "Tennis": "🎾", "Soccer": "⚽", "Cricket": "🏏",
}

def post_daily_picks_to_discord(df: pd.DataFrame) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return

    elite = df[df["tier"] == "Elite"].head(5)
    if elite.empty:
        return

    embeds = []
    for _, r in elite.iterrows():
        emoji = SPORT_EMOJI.get(r["sport"], "🎯")
        embeds.append({
            "title": f"{emoji} {r['sport']} — {r['game']}",
            "description": f"**{tier_badge(r['tier'])} {r['pick']}**",
            "fields": [
                {"name": "Odds", "value": str(r.get("odds", "N/A")), "inline": True},
                {"name": "Edge", "value": f"{r['edge']:+.1%}", "inline": True},
                {"name": "Confidence", "value": f"{r['confidence']:.1%}", "inline": True},
            ],
            "color": 0xFF4500 if r["tier"] == "Elite" else 0x00C853,
        })

    payload = {"content": "🔥 **Today's Top Picks**", "embeds": embeds}
    requests.post(webhook, json=payload, timeout=10)
```

### Feature 17 — RSS Feed for Picks

Generate an RSS/Atom feed of today's Elite and Strong picks.
Subscribe with any RSS reader for automated delivery.

```python
# scripts/generate_picks_rss.py
import pandas as pd
from datetime import datetime
from pathlib import Path

def generate_rss(df: pd.DataFrame, output: Path = Path("picks_feed.xml")) -> None:
    today = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = ""
    for _, r in df[df["tier"].isin(["Elite", "Strong"])].head(20).iterrows():
        items += f"""
    <item>
      <title>{r['sport']}: {r['pick']} — {r['game']}</title>
      <description>Tier: {r['tier']} | Edge: {r['edge']:+.1%} | Conf: {r['confidence']:.1%} | {r.get('notes', '')}</description>
      <pubDate>{today}</pubDate>
      <guid>{r['sport']}_{r['game']}_{r['pick']}</guid>
    </item>"""
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sports Picks Grid — Daily Picks</title>
    <link>https://sports-picks-grid.streamlit.app</link>
    <description>Cross-sport ML betting picks</description>
    <lastBuildDate>{today}</lastBuildDate>
    {items}
  </channel>
</rss>"""
    output.write_text(rss)
```

### Feature 18 — Sharpe Ratio & Drawdown Analytics

Calculate risk-adjusted performance (Sharpe ratio) and maximum drawdown
for the portfolio of all picks over the trailing 30/60/90 days.

```python
# utils/portfolio_analytics.py
import numpy as np, pandas as pd

def portfolio_sharpe(picks: pd.DataFrame, window_days: int = 30) -> dict:
    """Portfolio analytics for flat-bet picks history."""
    recent = picks[picks["date"] >= (pd.Timestamp.now() - pd.Timedelta(days=window_days)).date().isoformat()]
    if len(recent) < 10:
        return {}
    returns = recent["pnl"].values
    sharpe = (returns.mean() / returns.std(ddof=1)) if returns.std() > 0 else 0
    cum = np.cumsum(returns)
    peak = np.maximum.accumulate(cum + 1000)
    drawdown = (cum + 1000 - peak) / peak
    return {
        "sharpe": round(sharpe, 3),
        "max_drawdown": round(drawdown.min(), 4),
        "avg_daily_return": round(returns.mean(), 4),
        "win_rate": round((returns > 0).mean(), 3),
        "n_bets": len(recent),
    }
```

### Feature 19 — GitHub Actions Performance — Audit Log

Log every data fetch attempt with status, timing, and error. Display
aggregated uptime and success rate per sport source.

```python
# utils/audit_log.py
import json, os
from datetime import datetime
from pathlib import Path

AUDIT_LOG = Path("data_cache/audit_log.jsonl")

def log_fetch_result(sport: str, source: str, success: bool,
                      n_bets: int, duration_ms: float, error: str | None = None) -> None:
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "sport": sport, "source": source,
        "success": success, "n_bets": n_bets,
        "duration_ms": round(duration_ms, 1),
        "error": error,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def load_audit_log() -> pd.DataFrame:
    if not AUDIT_LOG.exists():
        return pd.DataFrame()
    rows = [json.loads(l) for l in AUDIT_LOG.read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows)
```

### Feature 20 — Picks Export to PDF

Export today's top picks as a formatted PDF "daily card" for offline
use or printing.

```python
# scripts/export_daily_card.py
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from io import BytesIO
import pandas as pd

def export_daily_picks_pdf(df: pd.DataFrame, date_str: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    story = [Paragraph(f"🎯 Sports Picks Grid — {date_str}", styles["Title"]), Spacer(1, 12)]

    elite = df[df["tier"] == "Elite"].head(10)
    data = [["Sport", "Game", "Pick", "Odds", "Edge", "Tier"]]
    for _, r in elite.iterrows():
        data.append([r["sport"], r["game"][:30], r["pick"],
                     str(r.get("odds", "N/A")), f"{r['edge']:+.1%}", r["tier"]])

    table = Table(data, colWidths=[60, 140, 80, 55, 55, 55])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF4500")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF8F0")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(table)
    doc.build(story)
    return buffer.getvalue()
```

### Feature 21 — Data Source Fallback Chain

Implement a 3-tier fallback: cache JSON → GitHub raw URL → API direct.
Log which source was used and show in the health monitor.

```python
# utils/fetcher.py (update _load_sport)
import json, requests
from pathlib import Path
from datetime import datetime

def _load_sport_with_fallback(sport: str, cache_key: str, repo_name: str) -> pd.DataFrame:
    """Try cache → GitHub raw → return empty. Log each attempt."""
    from utils.audit_log import log_fetch_result
    start = datetime.utcnow()

    # Tier 1: local cache
    cache_file = Path(f"data_cache/{cache_key}.json")
    if cache_file.exists():
        age_hours = (datetime.utcnow() - datetime.fromtimestamp(cache_file.stat().st_mtime)).total_seconds() / 3600
        if age_hours < 26:
            try:
                data = json.loads(cache_file.read_text())
                ms = (datetime.utcnow() - start).total_seconds() * 1000
                log_fetch_result(sport, "local_cache", True, len(data.get("bets", [])), ms)
                return pd.DataFrame(data.get("bets", []))
            except Exception as e:
                pass

    # Tier 2: GitHub raw URL
    url = f"https://raw.githubusercontent.com/gmalbert/{repo_name}/main/data_files/best_bets_today.json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            ms = (datetime.utcnow() - start).total_seconds() * 1000
            log_fetch_result(sport, "github_raw", True, len(data.get("bets", [])), ms)
            return pd.DataFrame(data.get("bets", []))
    except Exception as e:
        ms = (datetime.utcnow() - start).total_seconds() * 1000
        log_fetch_result(sport, "github_raw", False, 0, ms, str(e))

    return pd.DataFrame()
```

### Feature 22 — Bankroll Simulator (Season-Level)

Simulate a full season of flat bets vs Kelly bets using historical picks data.
Show confidence intervals, drawdown periods, and breakeven point.

```python
# pages/bankroll_simulator.py
import streamlit as st, numpy as np, plotly.go as go

def render_bankroll_simulator(picks_history: pd.DataFrame) -> None:
    st.title("💰 Bankroll Season Simulator")
    bankroll = st.number_input("Starting Bankroll ($)", 500, 100_000, 1000)
    strategy = st.radio("Staking Strategy", ["Flat $25", "1% Bank", "Half-Kelly"])
    n_sim = 500

    if st.button("Run Simulation"):
        final_bankrolls = []
        for _ in range(n_sim):
            br = float(bankroll)
            for _, row in picks_history.sample(frac=1).iterrows():
                if strategy == "Flat $25":
                    stake = 25.0
                elif strategy == "1% Bank":
                    stake = br * 0.01
                else:
                    kelly = max(0, row.get("kelly_pct", 0.02)) * 0.5
                    stake = br * kelly
                stake = min(stake, br * 0.10)
                dec = row.get("decimal_odds", 1.91)
                if np.random.random() < row.get("confidence", 0.52):
                    br += stake * (dec - 1)
                else:
                    br -= stake
            final_bankrolls.append(br)

        fig = go.Figure(go.Histogram(x=final_bankrolls, nbinsx=40,
                                      marker_color="#FF4500"))
        fig.add_vline(x=bankroll, line_dash="dash", annotation_text="Start")
        fig.update_layout(title=f"Season-End Bankroll Distribution ({strategy})",
                           template="plotly_dark")
        st.plotly_chart(fig, width="stretch")
        col1, col2, col3 = st.columns(3)
        col1.metric("Median End Bankroll", f"${np.median(final_bankrolls):,.0f}")
        col2.metric("10th Percentile", f"${np.percentile(final_bankrolls, 10):,.0f}")
        col3.metric("90th Percentile", f"${np.percentile(final_bankrolls, 90):,.0f}")
```

---

## Timeline Summary

| Quarter | Focus | Key Deliverables |
|---------|-------|-----------------|
| Q1 Aug–Oct 2026 | DQ & UX | Health monitor, correlation warnings, user preferences, parlay builder, model leaderboard |
| Q2 Nov 2026–Jan 2027 | Intelligence | AI briefing, weather badges, weekly email, value calendar, unit tracker |
| Q3 Feb–Apr 2027 | Visual analytics | Edge heatmap, pick volume, confidence distribution, top pick card, season calendar |
| Q4 May–Jul 2027 | Automation & platform | Discord bot, RSS feed, Sharpe ratio, audit log, PDF export, fallback chain, bankroll simulator |
