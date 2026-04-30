# Unified Best Bets JSON Schema

## File Location

Every sport repo writes this file at the end of its nightly pipeline:

```
data_files/best_bets_today.json
```

The dashboard reads it from:
```
https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json
```

---

## Top-Level Structure

The file is a JSON object with two keys: `meta` (file-level metadata) and `bets` (array
of individual bet recommendations).

```json
{
  "meta": {
    "sport":        "MLB",
    "generated_at": "2026-04-29T12:00:00Z",
    "model_version": "v2.1",
    "season":       "2026",
    "total_bets":   7,
    "notes":        ""
  },
  "bets": [
    { ... },
    { ... }
  ]
}
```

### `meta` Object

| Field | Type | Required | Description |
|---|---|---|---|
| `sport` | string | ✅ | Sport identifier. See **Sport Identifiers** below. |
| `generated_at` | ISO 8601 string | ✅ | UTC timestamp when this file was written. |
| `model_version` | string | optional | Semver or label for the model that produced this output. |
| `season` | string | optional | Current season label, e.g. "2025-26" or "2026". |
| `total_bets` | integer | ✅ | Count of bets in the `bets` array. |
| `notes` | string | optional | Human-readable note, e.g. "off-season — no picks today". |

### Sport Identifiers

Use these exact strings for the `sport` field throughout:

| Repo | `sport` value |
|---|---|
| baseball-predictions | `"MLB"` |
| hockey-predictions | `"NHL"` |
| nba-predictions | `"NBA"` |
| nfl-predictions | `"NFL"` |
| mls-predictions | `"MLS"` |
| premier-league | `"EPL"` |
| la-liga | `"LaLiga"` |
| bundesliga | `"Bundesliga"` |
| ligue-1 | `"Ligue1"` |
| rugby | `"Rugby"` |
| college-football-predictions | `"NCAAF"` |
| tennis-predictions | `"Tennis"` |
| march-madness | `"NCAAB"` |

---

## `bets` Array — Individual Bet Object

Each element of `bets` represents **one specific wagering recommendation**.

```json
{
  "sport":          "MLB",
  "league":         "MLB",
  "game":           "Yankees @ Red Sox",
  "home_team":      "Red Sox",
  "away_team":      "Yankees",
  "game_date":      "2026-04-29",
  "game_time":      "19:10 ET",
  "bet_type":       "Moneyline",
  "pick":           "Yankees ML (+145)",
  "confidence":     0.64,
  "edge":           0.09,
  "tier":           "Strong",
  "model":          "XGBoost",
  "generated_at":   "2026-04-29T12:00:00Z"
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `sport` | string | ✅ | Same as `meta.sport`. Duplicated here so individual bets are self-describing. |
| `league` | string | optional | Sub-league or competition name (used mainly for Rugby multi-league). |
| `game` | string | ✅ | Human-readable matchup. Format: `"{away} @ {home}"` for US sports; `"{home} vs {away}"` for soccer/rugby. |
| `home_team` | string | ✅ | Home team name (normalized). |
| `away_team` | string | ✅ | Away team name (normalized). |
| `game_date` | string (YYYY-MM-DD) | ✅ | Date the game is played (local time of venue). |
| `game_time` | string | optional | Game start time, e.g. `"19:10 ET"` or `"14:30 GMT"`. Omit if unknown. |
| `bet_type` | string | ✅ | One of the standardized bet types below. |
| `pick` | string | ✅ | The recommended bet in human-readable form, e.g. `"Yankees ML (+145)"` or `"OVER 8.5"`. Include the line/odds if known. |
| `confidence` | float (0–1) | ✅ | Model's probability for the picked outcome. Always 0–1, never a percentage. |
| `edge` | float (0–1) | ✅ if known | Model prob minus implied odds prob. Positive = value. Use `null` if odds unavailable. |
| `tier` | string | ✅ | One of: `"Elite"`, `"Strong"`, `"Good"`, `"Standard"`. See tier mapping below. |
| `model` | string | optional | Model name, e.g. `"XGBoost"`, `"VotingClassifier"`, `"Elo+Dixon-Coles"`. |
| `generated_at` | ISO 8601 string | ✅ | UTC timestamp when this specific bet was generated. |
| `odds` | float | optional | American moneyline odds for the pick (e.g. `+145`, `-180`). Include when available. |
| `line` | float | optional | The spread or total line (e.g. `-3.5` for spread, `8.5` for total). |
| `notes` | string | optional | Short note, e.g. `"bullpen advantage"`, `"goalie confirmed"`. |

---

## Bet Type Values

Use these exact strings for `bet_type`:

| `bet_type` value | Used in |
|---|---|
| `"Moneyline"` | All sports — straight win/loss bet |
| `"Spread"` | NFL, NBA, NCAAF, NCAAB, NHL Puck Line, MLB Run Line |
| `"Over/Under"` | All sports — totals bet |
| `"Home Win"` | Soccer repos — home team wins (H/D/A format) |
| `"Away Win"` | Soccer repos — away team wins |
| `"Draw"` | Soccer repos — draw |
| `"Match Winner"` | Rugby, Tennis — outright winner (no spread) |
| `"Try Scorer"` | Rugby — player prop |
| `"Player Prop"` | NFL, NBA — player stat over/under |
| `"Outright"` | Golf/tournament — winner or top-N finish |

---

## Tier Mapping — All Repos

The export script in each repo must translate its internal tier/confidence system to the
unified 4-tier scale:

| Unified Tier | Badge | Criteria Summary |
|---|---|---|
| `"Elite"` | 🔥 | Highest confidence + strongest edge. Reserve for clear value plays. |
| `"Strong"` | ✅ | Good model confidence + positive edge. Core recommended bets. |
| `"Good"` | ➡ | Moderate signal. Worth a smaller position. |
| `"Standard"` | ⚪ | Tracked but minimal sizing recommended. |

### Per-Repo Translation

| Repo | Internal | → Unified |
|---|---|---|
| **NFL** | `Elite` (≥65%) | → `Elite` |
| **NFL** | `Strong` (≥60%) | → `Strong` |
| **NFL** | `Good` (≥55%) | → `Good` |
| **NFL** | `Standard` | → `Standard` |
| **NHL** | `High` (edge ≥ 8%) | → `Elite` |
| **NHL** | `Medium` (edge 3–8%) | → `Strong` |
| **NHL** | `Low` (edge < 3%) | → `Good` |
| **NBA** | `High` (prob ≥ 65% AND edge ≥ 5%) | → `Elite` |
| **NBA** | `Medium` (prob ≥ 57% OR edge ≥ 2%) | → `Strong` |
| **NBA** | `Low` | → `Good` |
| **MLB** | `BET` (edge > 3%) and conf ≥ 60% | → `Elite` |
| **MLB** | `BET` (edge > 3%) and conf < 60% | → `Strong` |
| **MLB** | `LEAN` (edge 0–3%) | → `Good` |
| **MLB** | `PASS` | → excluded from export |
| **Soccer (EPL/La Liga/Bundesliga/Ligue-1/MLS)** | edge ≥ 8% | → `Elite` |
| **Soccer** | edge 4–8% | → `Strong` |
| **Soccer** | edge 2–4% | → `Good` |
| **Soccer** | edge < 2% or `PASS` | → excluded |
| **NCAAF** | `Strong` (edge ≥ 5 pts spread or ≥ 2.5 pts total) | → `Elite` |
| **NCAAF** | `Moderate` (edge ≥ 2 pts spread or ≥ 1.5 pts total) | → `Strong` |
| **NCAAF** | `Lean` (edge ≥ 0.5 pts) | → `Good` |
| **NCAAB** | model_prob ≥ 65% | → `Elite` |
| **NCAAB** | model_prob 55–65% | → `Strong` |
| **NCAAB** | model_prob 50–55% | → `Good` |
| **Tennis** | `HIGH` (conf ≥ 75%) | → `Elite` |
| **Tennis** | `MEDIUM` (conf ≥ 65%) | → `Strong` |
| **Tennis** | `LOW` | → `Good` |
| **Rugby** | edge ≥ 10% | → `Elite` |
| **Rugby** | edge 5–10% | → `Strong` |
| **Rugby** | edge 2–5% | → `Good` |

---

## Minimum Export Thresholds

To keep the dashboard's signal-to-noise ratio high, each repo's export script should
**only include bets that meet or exceed the `Good` tier**. Bets below the minimum
threshold are computed internally but **not written to `best_bets_today.json`**.

| Repo | Minimum to include |
|---|---|
| NFL | `Good` tier or higher (≥ 55% confidence) |
| NHL | `Good` (edge ≥ 3%) |
| NBA | `Good` (Medium tier or higher) |
| MLB | `Good` (LEAN or better — edge ≥ 0%) |
| Soccer repos | `Good` (edge ≥ 2%) |
| NCAAF | `Good` (Lean or higher) |
| NCAAB | `Good` (≥ 50% model prob) |
| Tennis | `Good` (all levels included) |
| Rugby | `Good` (edge ≥ 2%) |

**Maximum bets per sport per day:** 15. If more pass the threshold, take the top 15
sorted by tier (Elite first) then confidence descending.

---

## Off-Season / No Games Response

When there are no qualifying bets (off-season, no games today, pipeline not run):

```json
{
  "meta": {
    "sport":        "NFL",
    "generated_at": "2026-04-29T03:00:00Z",
    "season":       "off-season",
    "total_bets":   0,
    "notes":        "NFL off-season. Next season begins September 2026."
  },
  "bets": []
}
```

An empty `bets` array is valid. The dashboard renders a "No picks today" card for that
sport. Never write an invalid JSON file or omit the file entirely — an absent file is
treated as an error, an empty `bets` array is treated as "no picks."

---

## Full Example — Multi-Sport Day

```json
{
  "meta": {
    "sport": "NHL",
    "generated_at": "2026-04-29T07:15:00Z",
    "model_version": "analytics-blend-v1",
    "season": "2025-26",
    "total_bets": 3,
    "notes": ""
  },
  "bets": [
    {
      "sport": "NHL",
      "game": "Maple Leafs @ Bruins",
      "home_team": "Bruins",
      "away_team": "Maple Leafs",
      "game_date": "2026-04-29",
      "game_time": "19:00 ET",
      "bet_type": "Moneyline",
      "pick": "Maple Leafs ML (+120)",
      "confidence": 0.62,
      "edge": 0.11,
      "tier": "Elite",
      "model": "Elo+Dixon-Coles",
      "odds": 120,
      "generated_at": "2026-04-29T07:15:00Z"
    },
    {
      "sport": "NHL",
      "game": "Oilers @ Canucks",
      "home_team": "Canucks",
      "away_team": "Oilers",
      "game_date": "2026-04-29",
      "game_time": "22:00 ET",
      "bet_type": "Over/Under",
      "pick": "OVER 5.5 (-110)",
      "confidence": 0.59,
      "edge": 0.06,
      "tier": "Strong",
      "model": "Elo+Dixon-Coles",
      "odds": -110,
      "line": 5.5,
      "generated_at": "2026-04-29T07:15:00Z"
    },
    {
      "sport": "NHL",
      "game": "Panthers @ Lightning",
      "home_team": "Lightning",
      "away_team": "Panthers",
      "game_date": "2026-04-29",
      "game_time": "19:30 ET",
      "bet_type": "Spread",
      "pick": "Panthers -1.5 (+165)",
      "confidence": 0.57,
      "edge": 0.04,
      "tier": "Good",
      "model": "Elo+Dixon-Coles",
      "odds": 165,
      "line": -1.5,
      "generated_at": "2026-04-29T07:15:00Z"
    }
  ]
}
```
