# GitHub Actions Integration Guide

This document provides the exact YAML additions to make in each sport repo's nightly
GitHub Action so that `best_bets_today.json` is generated and committed automatically.

---

## General Pattern

Add two steps at the **end** of each sport repo's existing nightly workflow:

1. **Run the export script** — generates `data_files/best_bets_today.json`
2. **Commit and push** — makes the JSON available via GitHub raw URL

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update best_bets_today [skip ci]"
          git push
```

The `[skip ci]` tag in the commit message prevents triggering another workflow run
from the push.

---

## 1. NFL — `.github/workflows/nightly-update.yml`

**Current schedule:** `cron: '0 3 * * *'` (3 AM UTC, Sept–Feb only)

Add at the end of the existing job steps, after the email step:

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update best_bets_today [skip ci]"
          git push
```

**Off-season:** The export script writes an empty bets response year-round. No change
to the `if: github.ref == 'refs/heads/main'` or month-range conditions needed.

---

## 2. NHL — `.github/workflows/daily-game-fetch.yml`

**Current schedule:** `cron: '0 7 * * *'` (7 AM UTC)

Current steps: runs `auto_fetch_games.py --days 10` then commits. Add after that:

```yaml
      - name: Generate value finder predictions
        run: python scripts/generate_recommendations.py
        # This script runs the Value Finder pipeline and refreshes recommendations.json

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit updated files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/recommendations.json data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: daily NHL update [skip ci]"
          git push
```

**Note:** A `scripts/generate_recommendations.py` script may need to be created to
materialize the Value Finder output to `recommendations.json`. Currently the Value Finder
runs only in-app. See `docs/03-repo-export-specs.md` for the NHL section.

---

## 3. NBA — `.github/workflows/nightly-pipeline.yml`

**Current schedule:** `cron: '0 10 * * *'` (10 AM UTC)

Add after the prediction parquet write step:

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update NBA best_bets_today [skip ci]"
          git push
```

---

## 4. MLB — `.github/workflows/ingestion.yml`

**Current schedule:** `cron: '0 12 * * *'` (12 PM UTC)

The ingestion workflow already commits parquets. Add a new step after the ingestion
pipeline completes to run the daily picks generation + export:

```yaml
      - name: Generate today's picks
        run: python src/picks/daily_pipeline.py
        # This writes data_files/processed/picks_today.parquet
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit picks and best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/processed/picks_today.parquet data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update MLB picks [skip ci]"
          git push
```

---

## 5. MLS — `.github/workflows/nightly.yml`

**Current schedule:** runs nightly (check existing cron)

MLS predictions are computed at runtime. Add a generate_picks step before export:

```yaml
      - name: Generate today's picks
        run: python scripts/generate_picks.py
        # Writes data_files/picks_today.csv
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit picks and best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/picks_today.csv data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update MLS picks [skip ci]"
          git push
```

---

## 6. EPL — `.github/workflows/nightly-pipeline.yml`

**Current schedule:** nightly

EPL has the most complex pipeline. Predictions need the model to run. Add after
`precompute-app-data.yml` steps or at the end of `nightly-pipeline.yml`:

```yaml
      - name: Generate today's picks
        run: python scripts/generate_picks.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/picks_today.csv data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update EPL picks [skip ci]"
          git push
```

---

## 7–9. La Liga, Bundesliga, Ligue-1

All three are identical. Replace `{SPORT}` and `{WORKFLOW_FILE}` as appropriate.

La Liga: `la-liga`, `nightly.yml`
Bundesliga: `bundesliga`, `nightly.yml`
Ligue-1: `ligue-1`, `nightly.yml`

```yaml
      - name: Generate today's picks
        run: python scripts/generate_picks.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/picks_today.csv data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update {SPORT} picks [skip ci]"
          git push
```

---

## 10. Rugby — `.github/workflows/scrape.yml`

**Current schedule:** `cron: '0 3 * * *'` (3 AM UTC)

The pipeline already commits CSV/Parquet. Add after the existing commit step:

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update Rugby picks [skip ci]"
          git push
```

---

## 11. College Football — `.github/workflows/weekly_pipeline.yml`

**Current schedule:** `cron: '0 6 * * 2'` (Tuesdays 6 AM UTC, Aug–Jan)

NCAAF is weekly, not daily. The export runs once per week after the pipeline:

```yaml
      - name: Generate this week's picks
        run: python scripts/generate_picks.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        # Note: LOOKAHEAD_DAYS = 6 in this script (cover the full week)
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/picks_today.json data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update NCAAF picks [skip ci]"
          git push
```

**Note:** Set `LOOKAHEAD_DAYS = 6` in the NCAAF export script since college football
games span an entire Saturday and the pipeline only runs Tuesdays.

---

## 12. Tennis — `.github/workflows/update_data.yml`

**Current schedule:** `cron: '0 5 * * *'` (5 AM UTC)

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update Tennis picks [skip ci]"
          git push
```

---

## 13. March Madness — `.github/workflows/precompute_predictions.yml`

**Current schedule:** `cron: '0 6 * * *'` (6 AM UTC)

The precompute pipeline already writes `upcoming_game_predictions.json`. The export
script reads it directly:

```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py
        env:
          PYTHONPATH: ${{ github.workspace }}

      - name: Commit best_bets_today.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_files/best_bets_today.json
          git diff --staged --quiet || git commit -m "chore: update NCAAB picks [skip ci]"
          git push
```

---

## Sports Picks Grid Aggregator Action

This repo (sports-picks-grid) has its own Action that runs after all sport repos
have updated. It pre-fetches all JSONs into `data_cache/` so the Streamlit app
never makes outbound HTTP calls at page-load time.

Create `.github/workflows/aggregate.yml`:

```yaml
name: Aggregate picks from all sport repos

on:
  schedule:
    - cron: '0 12 * * *'    # 12:00 PM UTC — after all sport repos have run
  workflow_dispatch:          # Allow manual trigger

jobs:
  aggregate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Fetch all sport repo JSONs
        run: python scripts/fetch_all_picks.py
        # Writes to data_cache/{sport}.json for each repo

      - name: Commit updated cache
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data_cache/
          git diff --staged --quiet || git commit -m "chore: refresh picks cache [skip ci]"
          git push
```

### `scripts/fetch_all_picks.py`

```python
"""Fetch best_bets_today.json from all sport repos and cache locally."""
import json
from pathlib import Path
import requests

REPOS = {
    "baseball": "baseball-predictions",
    "hockey":   "hockey-predictions",
    "nba":      "nba-predictions",
    "nfl":      "nfl-predictions",
    "mls":      "mls-predictions",
    "epl":      "premier-league",
    "laliga":   "la-liga",
    "bundesliga": "bundesliga",
    "ligue1":   "ligue-1",
    "rugby":    "rugby",
    "ncaaf":    "college-football-predictions",
    "tennis":   "tennis-predictions",
    "ncaab":    "march-madness",
}

BASE = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json"
CACHE_DIR = Path("data_cache")
CACHE_DIR.mkdir(exist_ok=True)

for key, repo in REPOS.items():
    url = BASE.format(repo=repo)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = CACHE_DIR / f"{key}.json"
        out.write_text(json.dumps(data, indent=2))
        count = len(data.get("bets", []))
        print(f"[OK] {key}: {count} bets cached")
    except Exception as e:
        print(f"[WARN] {key}: {e} — skipping")
```

---

## Triggering the Aggregator from Sport Repos (Optional)

For real-time freshness, each sport repo can trigger the aggregator when it finishes.
This requires a Personal Access Token (PAT) with `repo` scope stored as a secret.

Add to each sport repo's workflow at the very end:

```yaml
      - name: Trigger Sports Picks Grid refresh
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.SPORTS_PICKS_GRID_PAT }}
          repository: gmalbert/sports-picks-grid
          event-type: sport-data-updated
          client-payload: '{"sport": "NFL"}'
        continue-on-error: true    # Don't fail the sport repo's workflow if this step fails
```

In `sports-picks-grid/.github/workflows/aggregate.yml`, add a trigger:

```yaml
on:
  schedule:
    - cron: '0 12 * * *'
  workflow_dispatch:
  repository_dispatch:
    types: [sport-data-updated]
```

The PAT needs to be stored as `SPORTS_PICKS_GRID_PAT` in each sport repo's settings
(Settings → Secrets and variables → Actions → New repository secret).

---

## Troubleshooting Common Issues

### "Permission denied" on git push
The Actions token needs write permission. Add to the job:
```yaml
    permissions:
      contents: write
```

### "nothing to commit" — export script didn't change the file
This is normal when there are no new picks. The `git diff --staged --quiet || git commit`
pattern handles this silently.

### Export script fails but pipeline should still succeed
Wrap the export step:
```yaml
      - name: Export best bets for Sports Picks Grid
        run: python scripts/export_best_bets.py || echo "Export failed — continuing"
        continue-on-error: true
```

This ensures a failing export never breaks the core sport repo pipeline.

### JSON file is stale
If the sport repo's Action fails mid-run before the export step, the previous day's
`best_bets_today.json` remains. The `meta.generated_at` timestamp tells the dashboard
how old the data is. The dashboard shows "last updated X hours ago" for staleness.
