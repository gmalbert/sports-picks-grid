# Hermes Briefing Data-Quality Implementation Plan

## Objective

Make the daily Hermes briefing distinguish reliable current data from stale data, failed pipelines, missing exports, and legitimate no-pick/off-season states. Make cross-sport pick tiers and later performance measurements comparable.

## Findings to Correct

1. The aggregator runs at `12:00 UTC`, the same time as the MLB pipeline. It can read MLB's intermediate "pipeline pending" export before MLB finishes.
2. The documented `data_cache/` fallback is absent from the current checkout and remote `main`, so the dashboard commonly depends on live GitHub requests.
3. Darts has a public, active repository, but the standardized `data_files/best_bets_today.json` export is missing. This is an export-contract failure, not necessarily a repository outage.
4. The repository documentation says 13 sports while the implementation and Hermes briefing cover 17.
5. The seven-day dashboard lookahead does not match Boxing's July 24-August 2 output window.
6. Tier semantics are inconsistent: the shared documentation describes edge-based tiers in places, while the generic exporter uses confidence thresholds. Boxing labels low-confidence picks as Elite, which makes cross-sport comparisons unsafe.
7. There is no durable daily snapshot archive or consistent result-grading feed, so model accuracy and ROI cannot yet be independently calculated.

## Phase 1 — Establish a canonical data contract

- Define one schema for every sport export:
  - `meta.sport`, `meta.generated_at`, `meta.status`, `meta.source_commit`, `meta.lookahead_days`, and `meta.tier_definition`.
  - `status` values: `ok`, `no_picks`, `off_season`, `pipeline_pending`, `pipeline_failed`, `export_missing`, and `stale`.
  - `bets` containing explicit `game_date`, `pick`, `confidence`, `edge`, `odds`, and `tier` fields.
- Require every export to include a current timestamp, even when `bets` is empty.
- Add a schema validator in `sports-picks-grid` and run it against all configured repositories during aggregation.
- Fail the health check on malformed JSON, missing required metadata, invalid dates, or unrecognized statuses.

## Phase 2 — Fix freshness and orchestration

- Move the scheduled aggregator to a time after the slowest source workflow, or have each successful source workflow dispatch an aggregation event.
- Keep the scheduled run as a backup, but make it report which sources were not yet fresh at aggregation time.
- Add a freshness threshold by sport rather than treating every empty response as equivalent.
- Make the aggregator retain the previous valid snapshot when a fetch fails; never overwrite good data with an empty/error response without recording the reason.
- Commit `data_cache/` snapshots and verify that the workflow has write permissions and actually produces files.
- Add a workflow summary showing per-repo HTTP status, source timestamp, cache timestamp, status, and bet count.

## Phase 3 — Repair repository exports

- MLB: ensure the daily pipeline writes or explicitly reports `pipeline_pending`/`pipeline_failed`; do not silently convert a missing parquet into ordinary no-picks.
- Darts: add `data_files/best_bets_today.json` and commit it from the Darts workflow. Until then, classify the source as `export_missing`, not `repo_down`.
- Review every source workflow for `continue-on-error`; preserve the failed step in the exported status so a successful workflow shell cannot hide a failed model run.
- Add a small contract test to each source repo that validates its generated JSON before commit.

## Phase 4 — Standardize tiers and date windows

- Choose one tier definition. Recommended: calculate tiers from calibrated expected value/edge, while displaying confidence separately.
- Define the exact thresholds centrally and include the tier version in `meta.tier_definition`.
- Validate that a pick's tier agrees with its numeric fields before accepting it.
- Set one canonical lookahead policy. Recommended: seven days for the dashboard, with sport-specific exceptions explicitly declared in metadata.
- Have Hermes label future picks as `upcoming`, not implicitly as today's picks.
- Update all documentation, settings, and UI copy from 13 sports to the actual 17-source configuration.

## Phase 5 — Add historical grading

- Archive each successful daily source export under `data_cache/history/YYYY-MM-DD/{sport}.json`.
- Store the odds and timestamp available when the pick was published.
- Add a results-ingestion job that records final outcome, push/void state, closing odds when available, profit/loss, and settlement timestamp.
- Calculate accuracy, ROI, yield, calibration, and sample size by sport, tier, bet type, and odds band.
- Do not publish a model accuracy percentage until the sample size, grading rules, and time window are visible.
- Treat third-party or Reddit performance claims as context only, never as validation of the current Boxing card.

## Phase 6 — Make Hermes reporting deterministic

- Generate the briefing from the aggregator's validated status manifest rather than interpreting empty JSON files ad hoc.
- For each sport, show: status, source generated time, cache time, age, bet count, and action required.
- Use precise messages:
  - `No qualifying picks today`
  - `Off-season`
  - `Pipeline has not produced today's data`
  - `Export file missing`
  - `Source is stale`
  - `Fetch failed; last valid snapshot retained`
- Add a briefing-level warning when any source is stale, missing, or pending.
- Include the aggregation timestamp and source commit IDs so the email can be reproduced.

## Verification Plan

1. Run the schema validator against all 17 configured repositories.
2. Simulate each failure mode: HTTP 404, timeout, invalid JSON, missing parquet, stale timestamp, and legitimate empty bets.
3. Confirm the aggregator never replaces a valid cached snapshot with an empty failure response.
4. Run the workflow twice around the MLB/source schedule boundary and verify that the final cache contains the completed MLB export.
5. Confirm Darts changes from `export_missing` to a valid current export.
6. Compare Hermes output with the validated manifest for a full daily run.
7. Backtest the result grader on a known historical date before publishing performance metrics.

## Suggested Delivery Order

1. Canonical status schema and validator.
2. Aggregator freshness manifest and safe cache behavior.
3. Workflow scheduling/dispatch correction.
4. MLB and Darts export repairs.
5. Tier and lookahead standardization.
6. Historical archive and result grading.
7. Hermes briefing rewrite and end-to-end tests.

## Success Criteria

- Every configured sport produces a machine-readable status every day.
- No source is described as merely "no picks" when its pipeline or export failed.
- Aggregation never races the source workflows without reporting the race.
- The dashboard and Hermes use the same source count, tier rules, and date-window policy.
- Model accuracy and ROI are based on archived, settled picks with transparent sample sizes and grading rules.
