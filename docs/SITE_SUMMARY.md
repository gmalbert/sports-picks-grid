> **AI Onboarding Guide** — See also `.github/copilot-instructions.md` for full coding conventions.

# Sports Picks Grid — Site Summary

## What This App Does

Read-only Streamlit aggregator dashboard that collects daily betting picks from 17 sport-specific ML repositories and displays them in a unified interface. This repo contains **no ML models** — it fetches pre-computed `best_bets_today.json` files from each sport repo. A GitHub Action validates, archives, and commits fresh snapshots at 3 PM UTC daily.

## Quick Start

```bash
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate           # macOS/Linux

# 2. Run the app
streamlit run predictions.py
```

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit (multi-page, `st.navigation`) |
| Data | `utils/fetcher.py` — reads `data_cache/*.json` or live GitHub raw URLs |
| Formatting | `utils/formatter.py` — display helpers, tier badges, odds formatting |
| Scheduling | GitHub Actions (12 PM UTC daily) |

## Key Files

| File | Purpose |
|---|---|
| `predictions.py` | Entry point — pre-warms `st.session_state["all_bets_df"]` at startup |
| `utils/fetcher.py` | `REPOS` mapping + `load_all_bets()` — reads all 17 sport JSON files |
| `utils/formatter.py` | `upcoming_bets()`, `sort_by_tier()`, `tier_badge()`, `format_odds()`, `display_columns()` |
| `pages/1_Today.py` | Today + upcoming picks (7-day window), tabbed by tier |
| `pages/2_By_Sport.py` | Filter view by sport with `generated_at` timestamp |
| `pages/3_Best_Bets.py` | Card layout — Elite + Strong only |
| `pages/4_Performance.py` | Model report cards + links to sport apps |
| `scripts/fetch_all_picks.py` | Validates, archives, and fetches all 17 JSONs → `data_cache/` (run by GitHub Action) |
| `footer.py` | `add_betting_oracle_footer()` |

## Data Flow

1. **GitHub Action** (12 PM UTC) runs `scripts/fetch_all_picks.py` → reads each sport repo's `best_bets_today.json` → commits to `data_cache/`
2. **Startup**: `predictions.py` calls `load_all_bets()` once → `st.session_state["all_bets_df"]`
3. **Pages** read from `st.session_state["all_bets_df"]` — never call `load_all_bets()` directly

## REPOS Mapping

```python
REPOS = {
    "MLB": ("baseball", "baseball-predictions"),
    "NHL": ("hockey", "hockey-predictions"),
    "NBA": ("nba", "nba-predictions"),
    "NFL": ("nfl", "nfl-predictions"),
    "MLS": ("mls", "mls-predictions"),
    "EPL": ("epl", "premier-league"),
    "LaLiga": ("laliga", "la-liga"),
    "Bundesliga": ("bundesliga", "bundesliga"),
    "Ligue1": ("ligue1", "ligue-1"),
    "Rugby": ("rugby", "rugby"),
    "NCAAF": ("ncaaf", "college-football-predictions"),
    "Tennis": ("tennis", "tennis-predictions"),
    "NCAAB": ("ncaab", "march-madness"),
}
```

## JSON Schema

Each sport repo writes `data_files/best_bets_today.json`:
```json
{
  "meta": { "sport": "NFL", "generated_at": "2025-01-15T08:00:00Z", "season": "2025" },
  "bets": [
    { "game_date": "2025-01-15", "game": "NYY vs BOS", "game_time": "7:05 PM ET",
      "bet_type": "moneyline", "pick": "NYY", "confidence": 0.67,
      "edge": 0.11, "odds": -110, "tier": "Elite", "notes": "..." }
  ]
}
```

## Tier System

| Tier | Emoji | Threshold |
|---|---|---|
| Elite | 🔥 | Edge > 6% |
| Strong | ✅ | Edge 3–6% |
| Good | ➡ | Edge 1–3% |
| Standard | ⚪ | <1% (not displayed) |

## Critical Conventions

- **NEVER** call `load_all_bets()` in page files — always read from `st.session_state["all_bets_df"]`
- **NEVER** call `st.set_page_config()` outside `predictions.py`
- Use `upcoming_bets(df, days=7)` as the default filter — NCAAB/NCAAF export picks for multiple days ahead; `today_bets()` would hide them
- This repo is **display-only** — do not add ML models here

## Common Gotchas

- `generated_at` is in `meta`, not in individual bet dicts; `_load_sport()` in `fetcher.py` stamps each bet dict after loading
- If a sport repo's GitHub raw URL fails, `load_all_bets()` falls back to `data_cache/{key}.json` committed by the Action
- Do not store credentials or private data in `data_cache/` — all fetched files are from public repos
