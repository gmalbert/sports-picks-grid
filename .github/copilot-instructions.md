# Sports Picks Grid — GitHub Copilot Instructions

## Project Overview

**App name:** Sports Picks Grid  
**Purpose:** Streamlit multi-page aggregator dashboard that displays daily betting picks from 13 sport-specific ML prediction repositories.  
**Entry point:** `streamlit run predictions.py`  
**Part of:** Betting Oracle suite

---

## Architecture (Read-Only Aggregator)

**This repo contains no ML models.** It reads pre-computed `best_bets_today.json` files written by each sport repo's nightly pipeline.

Data priority per sport:
1. `data_cache/{key}.json` — committed by the aggregator GitHub Action (12 PM UTC)
2. `https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json` — live fallback
3. Empty DataFrame — graceful degradation when both sources fail

---

## File Structure

```
sports-picks-grid/
├── predictions.py              # Streamlit entry point — st.set_page_config HERE ONLY
├── footer.py                   # add_betting_oracle_footer()
├── utils/
│   ├── __init__.py
│   ├── fetcher.py              # load_all_bets(), load_performance(), get_cache_age()
│   └── formatter.py            # display_columns(), sort_by_tier(), tier_badge(), format_odds(), etc.
├── pages/
│   ├── 1_Today.py              # Today + upcoming picks (7-day window) — tabs by tier
│   ├── 2_By_Sport.py           # Filter by sport; shows generated_at timestamp
│   ├── 3_Best_Bets.py          # Card layout — Elite + Strong only, with odds + game date
│   ├── 4_Performance.py        # Model report cards + links to sport apps
│   └── 5_About.py              # App description, tiers, sport list
├── scripts/
│   └── fetch_all_picks.py      # Fetches all JSONs into data_cache/ — run by Action
├── data_cache/                  # Pre-fetched JSONs committed by GitHub Action
├── .github/
│   └── workflows/
│       └── aggregate.yml       # Daily 12 PM UTC fetch + commit
└── docs/
    ├── 01-master-architecture.md
    ├── 02-unified-schema.md
    ├── 03-repo-export-specs.md
    ├── 04-github-actions.md
    └── 05-dashboard-app.md
```

---

## Key Conventions

### Streamlit patterns
- `st.set_page_config()` is called **only once** in `predictions.py`. Never in page files.
- **All pages read from `st.session_state["all_bets_df"]`** — pre-warmed at startup. Never call `load_all_bets()` directly in a page file.
- Navigation is wired in `predictions.py` via `st.navigation()` / `st.Page()`.
- `add_betting_oracle_footer()` is called in `predictions.py` after `pg.run()`.

### Data access
```python
# In predictions.py (startup pre-warm)
if "all_bets_df" not in st.session_state:
    st.session_state["all_bets_df"] = load_all_bets()

# In any page
df = st.session_state.get("all_bets_df", pd.DataFrame())
```

Never call `load_all_bets()` in a page file. This would re-fetch on every navigation.

### Date filtering
- Use `upcoming_bets(df, days=7)` (not `today_bets`) as the default filter on all pages.
  This covers sports like NCAAB and NCAAF that export picks for games multiple days out.
- Use `today_bets(df)` only when explicitly showing "today only" data (e.g. a metric label).
- Both helpers are in `utils/formatter.py`.

### JSON schema
The canonical schema is in `docs/02-unified-schema.md`. Key fields:

```json
{
  "meta": {
    "sport": "MLB",
    "generated_at": "2025-01-15T08:00:00Z",
    "model_version": "1.0.0",
    "season": "2025"
  },
  "bets": [
    {
      "game_date": "2025-01-15",
      "game": "NYY vs BOS",
      "game_time": "7:05 PM ET",
      "bet_type": "moneyline",
      "pick": "NYY",
      "confidence": 0.67,
      "edge": 0.11,
      "odds": -110,
      "tier": "Elite",
      "notes": "Strong SP matchup advantage"
    }
  ]
}
```

`generated_at` lives in `meta`, not in individual bet dicts. `_load_sport()` in `fetcher.py`
stamps each bet dict with `generated_at` so it flows through to the DataFrame and pages can
display it as `df["generated_at"]`.

### Tier system
| Tier | Emoji | Threshold |
|---|---|---|
| Elite | 🔥 | Edge > 6%, high confidence |
| Strong | ✅ | Edge 3–6% |
| Good | ➡ | Edge 1–3% |
| Standard | ⚪ | Below 1% edge (not displayed) |

Tier constants live in `utils/formatter.py` (`TIER_EMOJI`, `TIER_ORDER`).

### Formatting helpers (`utils/formatter.py`)
| Helper | Purpose |
|---|---|
| `today_bets(df)` | Filter to `game_date == today` |
| `upcoming_bets(df, days=7)` | Filter to `today ≤ game_date ≤ today + days` |
| `sort_by_tier(df)` | Elite first, then confidence descending |
| `display_columns(df)` | Rename + format all display columns (adds Date, Sport emoji, Odds formatting) |
| `format_confidence(c)` | `0.67` → `"67.0%"` |
| `format_edge(e)` | `0.11` → `"+11.0%"` |
| `format_odds(o)` | `135` → `"+135"`, `-140` → `"-140"`, None → `"—"` |
| `tier_badge(tier)` | `"Elite"` → `"🔥 Elite"` |

`display_columns()` applies `format_odds`, sport emoji, and `tier_badge` automatically.
The col_map includes `game_date` → `"Date"` so multi-day tables are readable.

### REPOS mapping (`utils/fetcher.py`)
```python
REPOS = {
    "MLB":        ("baseball",   "baseball-predictions"),
    "NHL":        ("hockey",     "hockey-predictions"),
    "NBA":        ("nba",        "nba-predictions"),
    "NFL":        ("nfl",        "nfl-predictions"),
    "MLS":        ("mls",        "mls-predictions"),
    "EPL":        ("epl",        "premier-league"),
    "LaLiga":     ("laliga",     "la-liga"),
    "Bundesliga": ("bundesliga", "bundesliga"),
    "Ligue1":     ("ligue1",     "ligue-1"),
    "Rugby":      ("rugby",      "rugby"),
    "NCAAF":      ("ncaaf",      "college-football-predictions"),
    "Tennis":     ("tennis",     "tennis-predictions"),
    "NCAAB":      ("ncaab",      "march-madness"),
}
```

---

## Adding a New Sport

1. Add to `REPOS` in `utils/fetcher.py` (and `scripts/fetch_all_picks.py`)
2. Add `SPORT_EMOJI` entry in `utils/formatter.py`
3. Confirm the sport repo writes `data_files/best_bets_today.json` per the schema in `docs/02-unified-schema.md`

## Adding a New Page

1. Create `pages/N_Name.py`
2. Add `st.Page(...)` entry in `predictions.py`
3. Never call `st.set_page_config()` in the page
4. Read data from `st.session_state["all_bets_df"]`
5. Use `upcoming_bets()` not `today_bets()` as the default filter

---

## Security

- No API keys in this repo — data is read from public GitHub raw URLs
- The aggregator Action uses no secrets; it only reads public repos
- `.env` and `st.secrets` are not used here

## What NOT to Do

- Do not add ML models to this repo — it is a display layer only
- Do not call `load_all_bets()` inside page files — always read from session state
- Do not call `st.set_page_config()` outside `predictions.py`
- Do not store real credentials or private data in `data_cache/`
- Do not use `today_bets()` as the primary filter — use `upcoming_bets()` so future-dated picks from NCAAB/NCAAF are not hidden
