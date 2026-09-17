# Sports Picks Grid — 6-Month Feature Roadmap

## Month 1: Dashboard Polish

- **Sports freshness indicator** — Each sport card shows time since last update; stale data shown in amber.
- **Elite picks hero section** — Prominent top-of-page card highlighting today's highest-edge pick.
- **Sport filter buttons** — Quick-filter buttons (MLB, NFL, NBA, etc.) above the main grid.
- **Upcoming games only toggle** — Filter out past game dates from the grid.

## Month 2: Performance Tab

- **Historical picks browser** — Browse past `best_bets_today.json` snapshots by date and sport.
- **Accuracy by sport** — Win rate and ROI for each of the 17 sports, with sample size and grading rules.
- **Tier accuracy chart** — Does "Elite" actually win at a higher rate than "Strong"?
- **Best sports by ROI** — Ranked list of sports by model accuracy since launch.

## Month 3: Alerts & Notifications

- **Daily email digest** — 12:30 PM UTC email with today's Elite + Strong picks (formatted HTML).
- **Breaking pick alert** — When an Elite pick is added after the initial 12 PM run, send a flash alert.
- **Discord integration** — Daily post to a Discord webhook with today's picks summary.

## Month 4: Analytics

- **CLV tracker** — Opening vs. closing odds for this week's picks across all sports.
- **Model agreement indicator** — When 3+ sport models agree on a theme (e.g., "overs are hitting"), surface a trend badge.
- **Calendar view** — Monthly calendar view of all upcoming picks by date.

## Month 5: User Experience

- **Odds format toggle** — Switch between American, decimal, and fractional odds display.
- **Bankroll simulator** — Enter bankroll; see Kelly-sized stakes for today's Elite + Strong picks combined.
- **Favourite sports** — Persist user's preferred sports filter in `st.session_state` / URL param.

## Month 6: Reliability & Automation

- **Retry + stale cache** — Serve last successful data with warning on transient fetch failures.
- **Schema validation log** — Surface schema errors in a developer-only sidebar tab.
- **Aggregator Action health check** — GitHub Action posts a status check to a status page after each run.
