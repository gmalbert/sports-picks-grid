# Per-Repo Export Script Specifications

Each sport repo needs a `scripts/export_best_bets.py` added to it. This document
specifies exactly what each script must read, how to map columns, and what special
handling is needed. All scripts follow the template in `export_best_bets.py` (repo root).

---

## General Template Behavior

Every export script must:

1. **Read** the primary prediction output (see per-repo specs below)
2. **Filter** to today's games only (`LOOKAHEAD_DAYS = 0`) — or 0–6 days for tournament sports
3. **Apply** the minimum tier threshold (exclude bets below `Good`)
4. **Map** internal column names to the unified schema fields
5. **Write** `data_files/best_bets_today.json` with `meta` + `bets` structure
6. **Exit 0** even if there are zero bets (writes the empty-bets response)
7. **Never crash** if a source file is missing — write the off-season/no-data response

---

## 1. NFL (`gmalbert/nfl-predictions`)

### Primary Input
```
data_files/betting_recommendations_log.csv
```

This file is already committed nightly by the pipeline and has all needed fields.

### Column Map

| Unified field | CSV column | Notes |
|---|---|---|
| `game_date` | `gameday` | Format: YYYY-MM-DD |
| `game_time` | `gametime` | May be missing — use `null` |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `bet_type` | `bet_type` | Values: "Spread", "Moneyline", "Over/Under" |
| `pick` | `recommended_team` + `spread_line` / `total_line` | Build: `"{team} +{spread}"` or `"OVER {line}"` |
| `confidence` | `model_probability` | Already 0–1 |
| `edge` | `edge` | Already 0–1 |
| `tier` | `confidence_tier` | Already uses Elite/Strong/Good/Standard |
| `odds` | `moneyline_odds` | American format |
| `line` | `spread_line` or `total_line` | Depends on bet_type |

### Tier Mapping
Pass-through — NFL already uses the unified tier labels.

### Filter
`gameday == today` and `confidence_tier in ["Elite", "Strong", "Good"]`

### Notes
- The log file contains historical + future games. Filter strictly to `gameday == today`.
- One row per game+bet_type already in this CSV — no need to expand.
- If `betting_recommendations_log.csv` is absent, try `nfl_games_historical_with_predictions.csv`
  (tab-delimited) and build bets from the raw probability columns.

---

## 2. NHL (`gmalbert/hockey-predictions`)

### Primary Input
```
data_files/recommendations.json
```

This file already exists and is structurally close to the unified schema.

### JSON Field Map

| Unified field | JSON field | Notes |
|---|---|---|
| `game_date` | `date` | Format: YYYY-MM-DD |
| `game_time` | — | Not in current JSON; omit |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `game` | `matchup` | Already formatted |
| `bet_type` | `bet_type` | Values vary — map to unified set |
| `pick` | `recommendation` | Already human-readable |
| `confidence` | `model_prob` | Already 0–1 |
| `edge` | `edge_percent` | Divide by 100 to get 0–1 |
| `tier` | derived | See tier mapping below |
| `odds` | `odds` | American format |

### Tier Derivation (from `edge_percent`)
```python
edge = row["edge_percent"] / 100
if edge >= 0.08:    tier = "Elite"
elif edge >= 0.03:  tier = "Strong"
else:               tier = "Good"
```

### Bet Type Normalization
```python
BET_TYPE_MAP = {
    "ML": "Moneyline",
    "Moneyline": "Moneyline",
    "Puck Line": "Spread",
    "PL": "Spread",
    "Over": "Over/Under",
    "Under": "Over/Under",
    "Total": "Over/Under",
}
```

### Filter
`date == today` and `edge_percent >= 3`

### Notes
- Some `recommendations.json` entries have `won` field — ignore it for export (it's
  historical tracking, not a prediction for today).
- The Value Finder page is partially scaffolded. If `recommendations.json` is empty or
  stale, the export writes the no-picks response.

---

## 3. NBA (`gmalbert/nba-predictions`)

### Primary Input
```
data_files/historical/predictions_{YYYY-MM-DD}.parquet
```
Where `{YYYY-MM-DD}` is today's date.

### Parquet Column Map

| Unified field | Parquet column | Notes |
|---|---|---|
| `game_date` | `game_date` | |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `confidence` | `home_win_prob` or `away_win_prob` | Take the higher one; that team is the pick |
| `edge` | `edge` | 0–1 |
| `bet_type` | `bet_type` | "Moneyline", "Spread", "Over/Under" |
| `pick` | Derived | `"{team} ML"` or `"OVER/UNDER {line}"` |
| `tier` | `confidence` | Values: "High", "Medium", "Low" — map below |
| `odds` | From `data_files/odds_snapshots.parquet` | Join on game_date + teams |

### Tier Mapping
```python
TIER_MAP = {
    "High":   "Elite",
    "Medium": "Strong",
    "Low":    "Good",
}
```

### File Discovery (handle missing today file)
```python
from datetime import date
today = date.today().isoformat()
path = Path(f"data_files/historical/predictions_{today}.parquet")
if not path.exists():
    # Try yesterday as fallback
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    path = Path(f"data_files/historical/predictions_{yesterday}.parquet")
    if not path.exists():
        write_no_picks("NBA", "No predictions file found for today.")
        sys.exit(0)
```

### Notes
- Join `odds_snapshots.parquet` on `game_date + home_team + away_team` to get `odds` field.
  If no odds are available, set `odds = null` and compute `edge = null`.
- The `predicted_spread` column can populate `line` for Spread bets.

---

## 4. MLB (`gmalbert/baseball-predictions`)

### Primary Input
MLB predictions are computed at runtime by the home page of the Streamlit app — they are
**not persisted to a file** in the current pipeline. The export script must replicate
the edge computation from `predictions.py`.

### Available Parquet Files
```
data_files/processed/moneyline_test_df.parquet     ← ML model results
data_files/processed/spread_test_df.parquet        ← Run line results
data_files/processed/totals_test_df.parquet        ← Over/Under results
```
These are backtest/test DataFrames, not today's predictions. The export script needs to
also read the odds CSV to get today's lines.

### Recommended Approach: Two-Stage

**Stage 1 — Add to the ingestion pipeline (`src/picks/daily_pipeline.py`)**

At the end of the daily pipeline, compute today's predictions and write them to:
```
data_files/processed/picks_today.parquet
```

Columns: `home_team`, `away_team`, `game_date`, `game_time`, `bet_type`, `prob_home_win`,
`implied_prob`, `edge`, `badge` (BET/LEAN/PASS), `odds`, `line`

**Stage 2 — Export script reads `picks_today.parquet`**

| Unified field | Parquet column | Notes |
|---|---|---|
| `game_date` | `game_date` | |
| `game_time` | `game_time` | |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `confidence` | `prob_home_win` | 0–1 |
| `edge` | `edge` | 0–1 |
| `bet_type` | `bet_type` | "Moneyline", "Spread", "Over/Under" |
| `pick` | Derived from badge + team + odds | |
| `tier` | Derived from badge + confidence | |
| `odds` | `odds` | American |
| `line` | `line` | Spread or total |

### Tier Derivation
```python
if badge == "BET" and confidence >= 0.60:   tier = "Elite"
elif badge == "BET":                         tier = "Strong"
elif badge == "LEAN":                        tier = "Good"
else:                                        # PASS — excluded
```

### Notes
- If `picks_today.parquet` doesn't exist (pipeline hasn't run yet), export writes no-picks.
- This is the most complex repo to wire up. Prioritize the daily pipeline parquet write
  in `src/picks/daily_pipeline.py` first, then the export script is simple.

---

## 5. MLS (`gmalbert/mls-predictions`)

### Primary Input
MLS predictions are computed at runtime and **not persisted to a file**. The export
script needs to replicate the prediction logic from `predictions.py`.

### Recommended Approach

Add a `scripts/generate_picks.py` that runs the same model + fixture loading logic as
`predictions.py` but writes output to `data_files/picks_today.csv`.

| Unified field | CSV column | Notes |
|---|---|---|
| `game_date` | `Date` | From `upcoming_fixtures.csv` |
| `home_team` | `HomeTeam` | Normalize via `team_name_mapping.py` |
| `away_team` | `AwayTeam` | |
| `bet_type` | `"Home Win"` / `"Draw"` / `"Away Win"` | |
| `pick` | `Betting Tip` stripped of emoji | `"Home Win"`, etc. |
| `confidence` | `home_prob` / `draw_prob` / `away_prob` | Take max_prob team |
| `edge` | `max_prob - implied_prob` | Compute from `OddsHome/OddsDraw/OddsAway` if available |
| `tier` | Derived from edge | See soccer tier mapping |

### Tier Derivation (Soccer)
```python
if edge >= 0.08:   tier = "Elite"
elif edge >= 0.04: tier = "Strong"
elif edge >= 0.02: tier = "Good"
else:              # excluded
```

### Notes
- Only include bets where the MLS model returns `"💰 Bet [outcome]"` (not `"❌ Avoid"`).
- `risk_score > 60` → cap at `"Good"` tier even if edge is higher.

---

## 6. EPL (`gmalbert/premier-league`)

### Primary Input
```
data_files/upcoming_fixtures.csv
data_files/combined_historical_data_with_calculations.csv
```

The EPL app computes predictions at runtime. The export script must:
1. Load `upcoming_fixtures.csv` to get today's matches
2. Load the processed historical data + run the VotingClassifier
3. Join with odds from `data_files/api_*.csv` if available

### Recommended Approach

Add `scripts/generate_picks.py` that mirrors the model inference block from
`premier-league-predictions.py` and writes `data_files/picks_today.csv`.

| Unified field | Source | Notes |
|---|---|---|
| `game_date` | `upcoming_fixtures.csv` → `date` | |
| `home_team` | `upcoming_fixtures.csv` → `HomeTeam` | |
| `away_team` | `upcoming_fixtures.csv` → `AwayTeam` | |
| `bet_type` | `"Home Win"` / `"Draw"` / `"Away Win"` | |
| `pick` | `PredictedResult` (H/D/A) → mapped | H→"Home Win", D→"Draw", A→"Away Win" |
| `confidence` | `PredHomeWin` / `PredDraw` / `PredAwayWin` | Take the predicted outcome's probability |
| `edge` | `confidence - implied_prob` | From Bet365 odds columns if available |
| `tier` | Derived from edge | Soccer tier mapping |

### Notes
- If referee data is available for today's fixtures, include a `notes` field with
  the referee name and their home/away card average.
- EPL has the richest feature set of all soccer repos — the edge calculation here
  is more reliable than in la-liga/bundesliga/ligue-1.

---

## 7. La Liga (`gmalbert/la-liga`)

### Primary Input
```
data_files/picks_today.csv     ← Write this from generate_picks.py (new)
data_files/predictions_log.csv ← Historical reference only
data_files/upcoming_fixtures.csv
```

La Liga, Bundesliga, and Ligue-1 all use identical code structure (same `utils.py`,
same `pages/best_bets.py` logic). One export template serves all three.

### Column Map (same for Bundesliga and Ligue-1)

| Unified field | Source column | Notes |
|---|---|---|
| `game_date` | `Date` | From `best_bets.py` output |
| `home_team` | `Match` → split on ` vs ` | Take right side |
| `away_team` | `Match` → split on ` vs ` | Take left side |
| `bet_type` | `Bet` | Values: "Home Win", "Draw", "Away Win" |
| `pick` | `Bet` + team name | e.g. "Home Win — Real Madrid" |
| `confidence` | `Model` / 100 | Convert percent string to float |
| `edge` | `Edge` / 100 | Convert "+N.N%" to float |
| `tier` | Derived from edge | Soccer tier mapping |
| `odds` | `Odds` | Decimal odds — convert to American |

### Decimal → American Odds Conversion
```python
def decimal_to_american(decimal_odds: float) -> float:
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1) * 100)
    else:
        return round(-100 / (decimal_odds - 1))
```

### Notes
- `pages/best_bets.py` already does the edge calculation — just read its output.
- In La Liga and Bundesliga repos, the Copa del Rey / DFB-Pokal congestion flag may
  cause some picks to be suppressed — this is expected.

---

## 8. Bundesliga (`gmalbert/bundesliga`)

Identical to La Liga spec above. Change `SPORT = "Bundesliga"` in the script.

The `EV_THRESHOLD = 0.04` in `pages/best_bets.py` already filters to ≥ 4% edge.

---

## 9. Ligue 1 (`gmalbert/ligue-1`)

Identical to La Liga spec above. Change `SPORT = "Ligue1"` in the script.

---

## 10. Rugby (`gmalbert/rugby`)

### Primary Input
```
data_files/csv/odds_snapshots.csv      ← Latest odds per match
data_files/csv/matches.csv             ← Schedule + scores
data_files/csv/teams.csv               ← Team ID → name
data_files/csv/leagues.csv             ← League ID → name
```

Rugby predictions come from `models/value_finder.py` which runs in-memory. The export
script must run the value finder and serialize its output.

### Steps

1. Load `matches.csv`, filter to `status == "scheduled"` and `kickoff_utc` within today
2. Load latest `odds_snapshots.csv` (latest row per `match_id`)
3. Load ELO ratings from `models/elo.py` (in-memory — call `build_elo_history(matches_df)`)
4. Call `find_match_edges(upcoming, odds_df, elo_df, min_edge=0.02)`
5. Map output to unified schema

### Column Map

| Unified field | Value Finder output | Notes |
|---|---|---|
| `game_date` | `kickoff_utc` → date part | |
| `game_time` | `kickoff_utc` → time part | |
| `home_team` | `home_team_id` → `tname()` lookup | |
| `away_team` | `away_team_id` → `tname()` lookup | |
| `league` | `league_id` → league name | |
| `bet_type` | `market` | Map "ML" → "Match Winner" |
| `pick` | `direction + team/side` | `"Back {team}"` or `"Fade {team}"` |
| `confidence` | `model_pct` | 0–1 |
| `edge` | `edge_pct` | 0–1 |
| `tier` | Derived from `edge_pct` | Rugby tier mapping |
| `odds` | `dk_odds` | American format |

### Rugby Tier Derivation
```python
if edge >= 0.10:   tier = "Elite"
elif edge >= 0.05: tier = "Strong"
elif edge >= 0.02: tier = "Good"
else:              # excluded
```

### Notes
- Rugby covers multiple leagues — always populate the `league` field.
- Try scorer props (from `models/try_scorer.py`) are optional to include. Use
  `bet_type = "Try Scorer"` and format pick as `"{player_name} — Try Scorer"`.
- The Dixon-Coles model requires ≥ 15 completed matches — if insufficient data is
  available, fall back to Elo-only model.

---

## 11. College Football (`gmalbert/college-football-predictions`)

### Primary Input
```
data_files/processed/lines.parquet    ← Betting lines per game
data_files/processed/games.parquet   ← Schedule
```

Bet recommendations are computed by `utils/betting.py → BetRecommendation` dataclass.

### Recommended Approach

Add `scripts/generate_picks.py` that:
1. Loads `lines.parquet` and `games.parquet`
2. Joins and filters to today's/this week's games
3. Calls `utils/betting.py` recommendation logic
4. Writes `data_files/picks_today.json`

### Column Map

| Unified field | BetRecommendation field | Notes |
|---|---|---|
| `game_date` | From `games.parquet → start_date` | |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `bet_type` | `bet_type` | "spread" → "Spread", "total" → "Over/Under", "moneyline" → "Moneyline" |
| `pick` | `pick` | Team or OVER/UNDER |
| `confidence` | `win_prob` | 0–1 |
| `edge` | `edge` | In points — normalize: divide by line for relative edge |
| `tier` | `confidence` (enum) | Strong→Elite, Moderate→Strong, Lean→Good |
| `line` | From `lines.parquet` | Spread or total value |

### Seasonality
College football runs August–January. Export script should detect off-season and write
empty bets with `notes = "NCAAF off-season"`.

---

## 12. Tennis (`gmalbert/tennis-predictions`)

### Primary Input
```
data_files/prediction_backlog.parquet    ← Today's pending predictions
data_files/features_{year}_present.parquet
```

Tennis predictions are per-match. The `prediction_backlog.parquet` is refreshed by the
nightly Action.

### Column Map

| Unified field | Parquet column | Notes |
|---|---|---|
| `game_date` | `match_date` | YYYY-MM-DD |
| `home_team` | `player1_name` | Tennis has no home team — use Player 1 |
| `away_team` | `player2_name` | |
| `game` | `"{player1} vs {player2}"` | Use `vs` not `@` for tennis |
| `bet_type` | `"Match Winner"` | Only bet type exported |
| `pick` | `pick` (winner name) | |
| `confidence` | `p1_win_prob` or `1-p1_win_prob` | Take the prob of the `pick` |
| `edge` | `confidence - implied_prob` | Need odds from `flashscore_odds_history.csv` |
| `tier` | From tennis tier system | HIGH→Elite, MEDIUM→Strong, LOW→Good |
| `odds` | From `flashscore_odds_history.csv` | Join on match_date + player names |
| `notes` | `surface` | e.g. "Clay", "Hard" |

### Notes
- Tennis uses `"{player1} vs {player2}"` format (not `@`) in the `game` field.
- `player1_name` / `player2_name` should be set to the two players, and `home_team` /
  `away_team` map to player1 / player2 for schema consistency.
- Only export HIGH and MEDIUM confidence picks by default (confidence ≥ 0.65).
- `surface` is a valuable signal — include it in `notes`.

---

## 13. March Madness / NCAAB (`gmalbert/march-madness`)

### Primary Input
```
data_files/upcoming_game_predictions.json
```

This file is already precomputed nightly by the pipeline.

### JSON Field Map

| Unified field | JSON field | Notes |
|---|---|---|
| `game_date` | `date` | |
| `home_team` | `home_team` | |
| `away_team` | `away_team` | |
| `game` | `"{away_team} @ {home_team}"` | Derived |
| `bet_type` | `"Spread"` | Primary output |
| `pick` | Derived from `spread_prediction` | If negative → home team favored: `"{home_team} -{abs(spread)}"` |
| `confidence` | Derived from confidence interval width | `1 / (ci_high - ci_low)` normalized |
| `edge` | `null` | No market odds stored in JSON |
| `tier` | Derived | Based on confidence interval width |
| `line` | `spread_prediction` | |
| `notes` | `model_source` + advanced diff fields | |

### Confidence Interval → Tier
```python
ci_width = ci_high - ci_low
if ci_width <= 4:   tier = "Elite"
elif ci_width <= 8: tier = "Strong"
elif ci_width <= 14: tier = "Good"
else:               # excluded — too uncertain
```

### Seasonality
March Madness runs March–April. Regular NCAAB season runs November–March. The
precompute pipeline only runs during active season; the export script writes empty
bets outside these windows.

### Notes
- The `upcoming_game_predictions.json` file is already the right format — the export
  script is mostly a schema translation layer.
- `home_moneyline` / `away_moneyline` fields exist in the JSON and can populate `odds`.

---

## Shared Utilities

Create `scripts/export_utils.py` in each repo (or add to existing utils) with:

```python
from datetime import datetime, timezone

def write_best_bets(sport: str, bets: list[dict], notes: str = "") -> None:
    """Write the standardized best_bets_today.json file."""
    import json
    from pathlib import Path

    output = {
        "meta": {
            "sport": sport,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_bets": len(bets),
            "notes": notes,
        },
        "bets": bets,
    }

    path = Path("data_files/best_bets_today.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[OK] Wrote {len(bets)} bets to {path}")
```

This function is identical across all repos — copy-paste is fine since each repo is
independent.
