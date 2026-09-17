# Sports Picks Grid — Architecture

## Overview
Read-only Streamlit aggregator dashboard that displays daily betting picks from 17 sport-specific ML prediction repositories. Contains no ML models — all data is pre-computed by each sport repo's nightly pipeline and consumed here.

## Data Flow
```
17 sport repos (each writes data_files/best_bets_today.json)
        ↓
GitHub Actions (aggregate.yml — 3 PM UTC daily)
scripts/fetch_all_picks.py
        ↓
data_cache/{sport_key}.json (committed to repo)
        ↓
utils/fetcher.py → load_all_bets()
    Priority: 1) data_cache/ 2) raw.githubusercontent.com 3) empty DataFrame
        ↓
st.session_state["all_bets_df"] (pre-warmed at startup in predictions.py)
        ↓
pages/ (read ONLY from session state, never call load_all_bets() directly)
```

## Data Priority per Sport
1. `data_cache/{key}.json` — committed by GitHub Action
2. Live GitHub raw URL — fallback
3. Empty DataFrame — graceful degradation

## REPOS Mapping (`utils/fetcher.py`)
| Sport | Cache Key | GitHub Repo |
|-------|-----------|-------------|
| MLB | `baseball` | baseball-predictions |
| NHL | `hockey` | hockey-predictions |
| NBA | `nba` | nba-predictions |
| NFL | `nfl` | nfl-predictions |
| MLS | `mls` | mls-predictions |
| EPL | `epl` | premier-league |
| LaLiga | `laliga` | la-liga |
| Bundesliga | `bundesliga` | bundesliga |
| Ligue 1 | `ligue1` | ligue-1 |
| Rugby | `rugby` | rugby |
| NCAAF | `ncaaf` | college-football-predictions |
| Tennis | `tennis` | tennis-predictions |
| NCAAB | `ncaab` | march-madness |

## Tier System
| Tier | Emoji | Edge Threshold |
|------|-------|----------------|
| Elite | 🔥 | > 6% |
| Strong | ✅ | 3–6% |
| Good | ➡ | 1–3% |
| Standard | ⚪ | < 1% (not displayed) |

## Key Components
- `predictions.py` — entry, `st.set_page_config`, pre-warms `all_bets_df`, wires `st.navigation`
- `utils/fetcher.py` — `load_all_bets()`, `load_performance()`, `get_cache_age()`
- `utils/formatter.py` — `today_bets()`, `upcoming_bets()`, `sort_by_tier()`, `display_columns()`, `format_odds()`, `tier_badge()`
- `scripts/fetch_all_picks.py` — run by GitHub Action to populate `data_cache/`
- `footer.py` — `add_betting_oracle_footer()`

## Pages
| Page | Purpose |
|------|---------|
| `1_Today.py` | Today + 7-day upcoming picks, tabs by edge tier |
| `2_By_Sport.py` | Filter by sport + `generated_at` timestamp |
| `3_Best_Bets.py` | Card layout — Elite + Strong only |
| `4_Performance.py` | Model report cards + links to sport apps |
| `5_About.py` | App description, tier system, sport list |

## Critical Rules
- ALL pages read from `st.session_state["all_bets_df"]` — never call `load_all_bets()` in a page
- Use `upcoming_bets(df, days=7)` as default filter (covers NCAAB/NCAAF multi-day picks)
- Use `today_bets(df)` only for "today only" metrics
- `st.set_page_config()` only in `predictions.py`
- No ML models in this repo

## JSON Schema (canonical)
```json
{"meta": {"sport": "...", "generated_at": "ISO8601", "model_version": "1.0.0", "season": "YYYY"},
 "bets": [{"game_date": "YYYY-MM-DD", "game": "...", "bet_type": "...", "pick": "...",
           "confidence": 0.0, "edge": 0.0, "odds": -110, "tier": "Elite", "notes": "..."}]}
```
`generated_at` lives in `meta`; `_load_sport()` stamps each bet dict for DataFrame flow.
