# Sports Picks Grid — Enhancement Suggestions

## Priority 1: Aggregation Quality

### Stale Data Detection
- Add a `data_freshness_check()` function that compares each sport's `generated_at` to the current timestamp.
- Flag sports where the JSON is >24 hours old with a warning badge in the dashboard.

### Schema Validation
- Add a `pydantic` model for the canonical bet schema. Validate every loaded JSON against it.
- Log schema violations to a `data_cache/schema_errors.log` file without crashing the app.

### Historical Performance Tracking
- Store each day's `best_bets_today.json` snapshots in `data_cache/history/YYYY-MM-DD/{sport}.json`.
- Enable a "Performance" tab to look back at prior picks and compute accuracy.

## Priority 2: Dashboard Improvements

### Smart Tier Summary
- Top of dashboard: Elite picks count, Strong picks count, total sports with data today.
- Progress bar showing "X of 17 sports have fresh data", sourced from `status_manifest.json`.

### Same-Game Correlation Warning
- If two picks are from the same game (moneyline + total), add a "correlated picks" note.

## Priority 3: Notifications

### Email Digest
- GitHub Action at 12:30 PM UTC (after aggregation) sends a formatted HTML email with today's Elite + Strong picks.

### CLV Tracking
- Compare opening odds (from `generated_at` time) to closing odds (from sport repos' nightly refresh).
- Surface sports with the highest CLV on the Performance tab.

## Priority 4: Reliability

- Add retry logic in `_load_sport()` for transient HTTP failures on the GitHub raw URL fallback.
- Cache the last successful load per sport; serve stale cache with a warning rather than empty DataFrame.
