# Sports Picks Grid — Master Architecture

## What This Repo Does

Sports Picks Grid is a centralized Streamlit dashboard that aggregates daily betting picks
from all of the following sport prediction repositories. It does **not** run any models
itself — it reads standardized JSON output files that each sport repo publishes nightly.

---

## All Connected Repos

| # | Repo | Sport | Season | GH Actions Schedule | Tier System | Output Exists? |
|---|---|---|---|---|---|---|
| 1 | `gmalbert/baseball-predictions` | MLB | Apr–Oct | 12:00 UTC daily | BET/LEAN/PASS (>3% edge) | ❌ needs export |
| 2 | `gmalbert/hockey-predictions` | NHL | Oct–Jun | 7:00 AM UTC daily | High/Med/Low (edge slider) | ✅ `recommendations.json` (needs schema align) |
| 3 | `gmalbert/nba-predictions` | NBA | Oct–Jun | 10:00 AM UTC daily | High/Medium/Low | ❌ needs export |
| 4 | `gmalbert/nfl-predictions` | NFL | Sep–Feb | 3:00 AM UTC (season only) | Elite/Strong/Good/Standard | ❌ needs export |
| 5 | `gmalbert/mls-predictions` | MLS | Mar–Nov | nightly | Bet/Avoid | ❌ needs export |
| 6 | `gmalbert/premier-league` | EPL | Aug–May | nightly | None (prob % only) | ❌ needs export |
| 7 | `gmalbert/la-liga` | La Liga | Aug–May | 7:00 AM UTC daily | Surfaced/Not (EV ≥ 4%) | ❌ needs export |
| 8 | `gmalbert/bundesliga` | Bundesliga | Aug–May | nightly | Surfaced/Not (EV ≥ 4%) | ❌ needs export |
| 9 | `gmalbert/ligue-1` | Ligue 1 | Aug–May | nightly | Surfaced/Not (EV ≥ 4%) | ❌ needs export |
| 10 | `gmalbert/rugby` | Rugby (multi-league) | Year-round | 3:00 AM UTC daily | back/fade (5% edge) | ❌ needs export |
| 11 | `gmalbert/college-football-predictions` | NCAAF | Aug–Jan | Tue 6:00 AM UTC (season only) | Strong/Moderate/Lean/None | ❌ needs export |
| 12 | `gmalbert/tennis-predictions` | ATP Tennis | Year-round | 5:00 AM UTC daily | HIGH/MEDIUM/LOW | ❌ needs export |
| 13 | `gmalbert/march-madness` | NCAAB | Mar–Apr | 6:00 AM UTC daily | None (interval only) | ❌ needs export |

---

## Architecture Overview

```
baseball-predictions/  ──► best_bets_today.json ─┐
hockey-predictions/    ──► best_bets_today.json ──┤
nba-predictions/       ──► best_bets_today.json ──┤
nfl-predictions/       ──► best_bets_today.json ──┤
mls-predictions/       ──► best_bets_today.json ──┤
premier-league/        ──► best_bets_today.json ──┼──► sports-picks-grid (this repo)
la-liga/               ──► best_bets_today.json ──┤        └── reads via GitHub raw URLs
bundesliga/            ──► best_bets_today.json ──┤            cached for 1 hour
ligue-1/               ──► best_bets_today.json ──┤
rugby/                 ──► best_bets_today.json ──┤
college-football/      ──► best_bets_today.json ──┤
tennis-predictions/    ──► best_bets_today.json ──┤
march-madness/         ──► best_bets_today.json ──┘
```

Each repo writes `data_files/best_bets_today.json` at the end of its nightly GitHub Action.
Sports Picks Grid fetches these files via GitHub raw content URLs — no API keys, no server,
no database required.

**Raw URL pattern:**
```
https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json
```

---

## Nightly Timing Plan

To ensure picks are ready when users check in the morning (US Eastern), stagger the
Actions runs and schedule sports-picks-grid to run last as an aggregator sweep.

| Time (UTC) | Repos Running |
|---|---|
| 3:00 AM | NFL (season), Rugby |
| 5:00 AM | Tennis |
| 7:00 AM | NHL, La Liga |
| 8:00 AM | NBA, Baseball (ingestion) |
| 9:00 AM | MLS, Premier League, Bundesliga, Ligue-1 |
| 10:00 AM | NBA predictions write |
| 11:00 AM | College Football (Tuesdays), March Madness |
| **12:00 PM UTC** | **Sports Picks Grid aggregator sweep** |

The aggregator Action (in this repo) at 12:00 PM UTC runs after all sport repos have
updated. It optionally pre-fetches and caches the JSON files locally so the Streamlit app
serves instantly without making GitHub API calls at page-load time.

---

## Seasonality Handling

Each export script must handle off-season gracefully by writing a valid but empty array:

```json
[]
```

The dashboard detects this and shows a "No picks available — {sport} is in its off-season"
card instead of an error. The last-updated timestamp in the file header helps users
understand data freshness.

### Season Windows

| Sport | Active Months |
|---|---|
| NFL | September – February |
| MLB | April – October |
| NHL | October – June |
| NBA | October – June |
| MLS | March – November |
| EPL / La Liga / Bundesliga / Ligue-1 | August – May |
| NCAAF | August – January |
| NCAAB | November – April (March Madness: March–April) |
| Tennis ATP | Year-round (except Dec) |
| Rugby | Year-round (overlapping leagues) |

---

## Data Flow in Detail

```
1. Sport repo's nightly GH Action runs
   └── Existing pipeline (data fetch + model run)
   └── NEW: scripts/export_best_bets.py
       ├── Reads primary prediction output (CSV, Parquet, or JSON)
       ├── Filters to today's/upcoming games
       ├── Applies tier + edge thresholds
       ├── Writes data_files/best_bets_today.json
       └── GH Action commits and pushes the JSON

2. Sports Picks Grid (this repo) at 12:00 PM UTC
   └── Optional: pre-fetch Action downloads all JSONs → data_cache/
   └── Commits data_cache/*.json for offline fallback

3. Streamlit app (on page load)
   └── load_all_bets() fetches from GitHub raw URLs (ttl=3600 cache)
   └── Falls back to data_cache/ if remote fetch fails
   └── Renders daily picks grid grouped by sport + date
```

---

## File Structure for This Repo

```
sports-picks-grid/
├── .github/
│   └── workflows/
│       └── aggregate.yml         # Runs at 12:00 PM UTC, fetches all JSONs
├── predictions.py                # Streamlit entry point (st.set_page_config here only)
├── pages/
│   ├── 1_Today.py                # Today's picks grid (all sports)
│   ├── 2_By_Sport.py             # Filter by sport
│   ├── 3_By_Tier.py              # Elite/Strong/Good across all sports
│   ├── 4_Performance.py          # Model report cards per sport
│   └── 5_About.py                # How the models work
├── utils/
│   ├── fetcher.py                # GitHub raw URL fetch + fallback logic
│   ├── formatter.py              # Normalize schema across sports
│   └── tier_styles.py            # Color coding for tiers
├── footer.py                     # Betting Oracle footer
├── data_cache/                   # Pre-fetched JSON snapshots (committed by Action)
│   ├── baseball.json
│   ├── hockey.json
│   ├── nba.json
│   └── ...
├── data_files/
│   └── logo.png
├── requirements.txt
└── README.md
```

---

## Key Design Decisions

### 1. No Runtime API Calls to GitHub
The aggregator Action pre-fetches and commits all JSONs to `data_cache/`. The Streamlit
app reads local files first, only falling back to raw GitHub URLs if the cache is stale.
This avoids GitHub's unauthenticated rate limit (60 req/hr) and makes the app snappy.

### 2. Schema Normalization at Export Time (Not Dashboard Time)
Each sport repo is responsible for mapping its own columns to the unified schema. The
dashboard assumes the schema is already normalized — it does not do any column remapping.
This keeps `formatter.py` trivial.

### 3. One File Per Sport, Not One File Per Game
Each repo writes a single `best_bets_today.json` containing all qualifying bets for the
day. The dashboard reads 13 files max per load cycle. This is fast and simple.

### 4. Tier Normalization Across Sports
Different repos use different tier labels. The export script in each repo maps to the
unified 4-tier scale:

| Unified Tier | Badge | Description |
|---|---|---|
| `Elite` | 🔥 | Highest confidence + strong edge |
| `Strong` | ✅ | Good confidence + positive edge |
| `Good` | ➡ | Moderate confidence or edge |
| `Standard` | ⚪ | Worth tracking but minimal sizing |

Mapping rules per repo are documented in `docs/03-repo-export-specs.md`.

### 5. No Model Logic in This Repo
Sports Picks Grid is a reader, not a predictor. All model logic stays in the individual
sport repos. If a model changes, the export script in that repo handles the translation.
