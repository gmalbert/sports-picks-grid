# Sports Picks Grid — Next 5 Features to Implement

> **Based on:** Codebase gap analysis as of July 2025

---

## Feature 1: Picks Archive with Historical Accuracy Tracker

**Why:** The daily GitHub Action commits `best_bets_today.json` from each sport repo but does not preserve prior days' snapshots. Without a historical archive, the app cannot show which sport models have been most profitable over time — the most trust-building feature for users.

**How:**
1. Modify `.github/workflows/aggregate.yml` to rename each day's snapshots before overwriting: `data_cache/{key}_{YYYY-MM-DD}.json`
2. Add `scripts/archive_picks.py` that copies today's `data_cache/{key}.json` to `data_cache/archive/{key}_{date}.json` during the daily Action run
3. Build a loader in `utils/fetcher.py`: `load_historical_picks(days=90) → pd.DataFrame`
4. Read from `st.session_state` in `pages/4_Performance.py` to display rolling accuracy per sport

**Complexity:** Medium

---

## Feature 2: 7-Day Calendar View Page

**Why:** Tabs organized by tier (Elite/Strong/Good) are useful for picking the best bets but unhelpful for planning across a week. A calendar-grid view showing all picks organized by game date would be the most practical navigation improvement.

**How:**
1. Add `pages/6_Calendar.py`
2. Use `upcoming_bets(df, days=7)` to get the 7-day window
3. Render a Plotly table or `st.columns()` layout with one column per day (Mon–Sun)
4. Within each day, list picks by tier (Elite first) with sport emoji and odds
5. Wire into `predictions.py` navigation and add to the sidebar

**Complexity:** Medium

---

## Feature 3: Sport-Level Performance Leaderboard

**Why:** Users want to know: "Which sport model makes money?" A sortable leaderboard showing ROI, win rate, and total picks per sport over 30/60/90 days would directly answer this and drive users toward the most profitable sport apps.

**How:**
1. Requires Feature 1 (archive) as a prerequisite
2. Add a "Performance" section to `pages/4_Performance.py` (or a new page) with a sortable `st.dataframe`
3. Columns: Sport | Model | 30d Win Rate | 30d ROI | Total Picks | Avg Edge
4. Color-code ROI: green > 5%, yellow 0–5%, red < 0%
5. Source data from the archive loaded by `load_historical_picks()`

**Complexity:** Low (once archive is built)

---

## Feature 4: Email Newsletter Export

**Why:** A daily email digest of Elite + Strong picks sent at 12 PM UTC (aligned with the existing GitHub Action) would give users actionable picks without needing to visit the app. `scripts/fetch_all_picks.py` already structures all the data.

**How:**
1. Add `scripts/send_daily_email.py` using SMTP (Gmail App Password pattern from the NFL repo)
2. Email content: today's Elite picks → Strong picks → summary stats; use existing `display_columns()` and `tier_badge()` formatters
3. Add email recipients list to GitHub Actions secrets (`EMAIL_RECIPIENTS`)
4. Trigger from `.github/workflows/aggregate.yml` as a step after the fetch-and-commit step
5. Use a simple HTML template (inline CSS, no frameworks) to render the email body

**Complexity:** Medium

---

## Feature 5: Discord / Slack Webhook Alert for New Elite Picks

**Why:** Lines move quickly after Elite picks are published. A push notification to a Discord or Slack channel when any sport repo generates a new Elite-tier bet would let users act before the line tightens.

**How:**
1. Add `scripts/send_webhook_alert.py` that compares yesterday's Elite picks vs today's Elite picks
2. For any new picks (not present yesterday), POST to a Discord webhook URL or Slack incoming webhook
3. Message format: "🔥 NEW ELITE PICK: [Sport] — [Game] — [Pick] @ [Odds] (Edge: [Edge]%)"
4. Store the webhook URL in GitHub Secrets (`DISCORD_WEBHOOK_URL`)
5. Run from the daily `.github/workflows/aggregate.yml` after the fetch step

**Complexity:** Medium
