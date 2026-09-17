# MLB Pick-File Contract Issue

## Summary

The MLB repository’s daily pipeline and Sports Picks Grid exporter disagree about the file used to hand off daily picks.

The exporter expects:

```text
data_files/processed/picks_today.parquet
```

But the daily pipeline currently writes dated CSV files:

```text
data_files/processed/picks_YYYY-MM-DD.csv
```

When no picks qualify, the pipeline writes no pick file at all. The exporter then incorrectly reports `pipeline_pending`, even though the workflow may have completed successfully.

## Evidence

- The daily pipeline stores output in `picks_YYYY-MM-DD.csv` and does not create `picks_today.parquet`: [daily_pipeline.py](https://github.com/gmalbert/baseball-predictions/blob/main/src/picks/daily_pipeline.py#L222-L235)
- The exporter looks specifically for `picks_today.parquet`: [export_best_bets.py](https://github.com/gmalbert/baseball-predictions/blob/main/scripts/export_best_bets.py#L1-L20)
- If there are no picks, `_store_picks()` returns before writing any file: [daily_pipeline.py](https://github.com/gmalbert/baseball-predictions/blob/main/src/picks/daily_pipeline.py#L222-L228)
- The exporter maps a missing parquet file to `pipeline_pending`: [export_best_bets.py](https://github.com/gmalbert/baseball-predictions/blob/main/scripts/export_best_bets.py#L62-L70)
- The July 22, 2026 GitHub Actions run completed successfully: [Daily Ingestion run](https://github.com/gmalbert/baseball-predictions/actions/runs/29919985175)

## What this means

The current `pipeline_pending` status is ambiguous. A missing `picks_today.parquet` can mean:

1. The daily pipeline failed.
2. There were no games on the target date.
3. Games were processed, but no predictions passed the model thresholds.
4. The pipeline produced output in the wrong format or location.

The dashboard cannot currently distinguish these cases.

## Desired contract

The pipeline and exporter need one explicit, stable handoff contract:

```text
MLB pipeline
    ↓
dated pick artifact + explicit pipeline status
    ↓
Sports Picks Grid exporter
    ↓
data_files/best_bets_today.json
    ↓
Hermes briefing
```

Recommended statuses:

```text
pipeline_pending
pipeline_failed
no_games
no_qualifying_picks
ok
```

An empty pick list must still produce a valid artifact containing the status, target date, generation timestamp, source commit, and diagnostic notes.

## Recommended fix

Choose one canonical internal format and use it consistently. The simplest approach is:

1. Keep the dated internal file, such as `picks_2026-07-22.csv`, for historical traceability.
2. Have the daily pipeline also write a canonical `picks_today.csv` or `picks_today.parquet` snapshot.
3. Always write that snapshot, including when there are zero picks.
4. Add an explicit status field to the snapshot or a companion metadata file.
5. Update `scripts/export_best_bets.py` to read the canonical snapshot and preserve the status.
6. Remove the inference that “missing parquet” automatically means `pipeline_pending`.
7. Make workflow failures visible; avoid allowing the daily picks step to fail silently through `continue-on-error` unless the exporter receives the failure status.

## Suggested behavior

### Successful picks

```json
{
  "status": "ok",
  "target_date": "2026-07-22",
  "picks_count": 3
}
```

### No qualifying picks

```json
{
  "status": "no_qualifying_picks",
  "target_date": "2026-07-22",
  "picks_count": 0,
  "notes": "Games and odds were processed; no pick cleared the configured edge threshold."
}
```

### Pipeline failure

```json
{
  "status": "pipeline_failed",
  "target_date": "2026-07-22",
  "picks_count": 0,
  "notes": "Odds fetch failed: ..."
}
```

## Acceptance criteria

- A successful run with picks creates the canonical snapshot and exports valid bets.
- A successful run with zero qualifying picks creates an empty canonical snapshot with `no_qualifying_picks`.
- A day with no games creates a snapshot with `no_games`.
- A failed pipeline creates a snapshot or export with `pipeline_failed` and diagnostic details.
- The exporter never labels a valid no-picks result as `pipeline_pending`.
- Hermes displays the explicit status instead of inferring state from file absence.
- A regression test covers the CSV/parquet path mismatch and the zero-picks path.

## Scope note

This issue belongs primarily in `gmalbert/baseball-predictions`. The Sports Picks Grid repository should only need a follow-up adjustment if the final MLB status vocabulary or artifact schema changes.
