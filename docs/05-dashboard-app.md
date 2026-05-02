# Sports Picks Grid — Streamlit App Design

## Entry Point

`streamlit run predictions.py`

`predictions.py` is the single entry point. It calls `st.set_page_config()` once,
renders the shared sidebar, and uses `st.navigation()` to wire up the pages.

**No model code lives in `predictions.py`** — it is purely a shell and router.

---

## Page Structure

```
predictions.py                    ← Entry point, sidebar, navigation
pages/
├── 1_Today.py                    ← Daily picks grid (all sports, today only)
├── 2_By_Sport.py                 ← Pick a sport, see all current picks
├── 3_Best_Bets.py                ← Elite + Strong picks across all sports
├── 4_Performance.py              ← Model report cards per sport
└── 5_About.py                    ← How the models work, disclaimers
utils/
├── fetcher.py                    ← Load + cache JSONs from GitHub raw or data_cache/
├── formatter.py                  ← Normalize bets into a flat DataFrame
└── tier_styles.py                ← Badge colors and emoji per tier
footer.py                         ← Betting Oracle footer (call on every page)
```

---

## `predictions.py` — Entry Point

```python
import streamlit as st
from utils.fetcher import load_all_bets
from footer import add_betting_oracle_footer

st.set_page_config(
    page_title="Sports Picks Grid",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
with st.sidebar:
    st.image("data_files/logo.png", width=220)
    st.caption("Daily picks from all Betting Oracle models")
    st.divider()

    if st.button("🔄 Refresh picks", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    # Last updated timestamp
    from utils.fetcher import get_cache_age
    age = get_cache_age()
    if age:
        st.caption(f"Last updated: {age}")

# --- Pre-warm data (load once, all pages reference this) ---
if "all_bets_df" not in st.session_state:
    with st.spinner("Loading picks from all sport models..."):
        st.session_state["all_bets_df"] = load_all_bets()

# --- Navigation ---
pg = st.navigation([
    st.Page("pages/1_Today.py",       title="Today's Picks",   icon="📅"),
    st.Page("pages/2_By_Sport.py",    title="By Sport",        icon="🏆"),
    st.Page("pages/3_Best_Bets.py",   title="Best Bets",       icon="🔥"),
    st.Page("pages/4_Performance.py", title="Performance",     icon="📊"),
    st.Page("pages/5_About.py",       title="About",           icon="ℹ️"),
])

pg.run()
add_betting_oracle_footer()
```

---

## `utils/fetcher.py`

```python
"""
Load best_bets_today.json from each sport repo.

Priority order:
  1. data_cache/{sport}.json  — pre-fetched by the aggregator Action (no HTTP needed)
  2. GitHub raw URL           — live fetch with 1-hour cache
  3. Empty bets response      — if both fail
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

REPOS = {
    "MLB":        ("baseball", "baseball-predictions"),
    "NHL":        ("hockey",   "hockey-predictions"),
    "NBA":        ("nba",      "nba-predictions"),
    "NFL":        ("nfl",      "nfl-predictions"),
    "MLS":        ("mls",      "mls-predictions"),
    "EPL":        ("epl",      "premier-league"),
    "LaLiga":     ("laliga",   "la-liga"),
    "Bundesliga": ("bundesliga", "bundesliga"),
    "Ligue1":     ("ligue1",   "ligue-1"),
    "Rugby":      ("rugby",    "rugby"),
    "NCAAF":      ("ncaaf",    "college-football-predictions"),
    "Tennis":     ("tennis",   "tennis-predictions"),
    "NCAAB":      ("ncaab",    "march-madness"),
}

RAW_URL = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json"
CACHE_DIR = Path("data_cache")

@st.cache_data(ttl=3600)
def load_all_bets() -> pd.DataFrame:
    """Load bets from all sport repos and return a flat DataFrame."""
    all_bets = []
    for sport, (cache_key, repo) in REPOS.items():
        bets = _load_sport(cache_key, repo)
        all_bets.extend(bets)

    if not all_bets:
        return pd.DataFrame()

    df = pd.DataFrame(all_bets)
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce").dt.date
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df["edge"] = pd.to_numeric(df["edge"], errors="coerce")
    return df


def _load_sport(cache_key: str, repo: str) -> list[dict]:
    """Try local cache first, then GitHub raw URL."""
    # 1. Local cache
    local = CACHE_DIR / f"{cache_key}.json"
    if local.exists():
        try:
            data = json.loads(local.read_text(encoding="utf-8"))
            return data.get("bets", [])
        except Exception:
            pass

    # 2. GitHub raw URL
    try:
        url = RAW_URL.format(repo=repo)
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("bets", [])
    except Exception:
        return []


def get_cache_age() -> str | None:
    """Return a human-readable string describing cache age."""
    # Check the most recently modified data_cache file
    if not CACHE_DIR.exists():
        return None
    files = list(CACHE_DIR.glob("*.json"))
    if not files:
        return None
    newest = max(files, key=lambda f: f.stat().st_mtime)
    mtime = datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc)
    delta = datetime.now(timezone.utc) - mtime
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m ago"
    return f"{minutes}m ago"
```

---

## `utils/formatter.py`

```python
"""Formatting helpers for the picks DataFrame."""
import pandas as pd
from datetime import date

TIER_EMOJI = {
    "Elite":    "🔥",
    "Strong":   "✅",
    "Good":     "➡",
    "Standard": "⚪",
}

TIER_ORDER = ["Elite", "Strong", "Good", "Standard"]


def today_bets(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to today's bets only."""
    if df.empty or "game_date" not in df.columns:
        return df
    today = date.today()
    return df[df["game_date"] == today].copy()


def sort_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by tier (Elite first) then confidence descending."""
    tier_rank = {t: i for i, t in enumerate(TIER_ORDER)}
    df = df.copy()
    df["_tier_rank"] = df["tier"].map(tier_rank).fillna(99)
    df = df.sort_values(["_tier_rank", "confidence"], ascending=[True, False])
    return df.drop(columns=["_tier_rank"])


def format_confidence(c) -> str:
    if c is None or pd.isna(c):
        return "—"
    return f"{c * 100:.1f}%"


def format_edge(e) -> str:
    if e is None or pd.isna(e):
        return "—"
    sign = "+" if e >= 0 else ""
    return f"{sign}{e * 100:.1f}%"


def tier_badge(tier: str) -> str:
    emoji = TIER_EMOJI.get(tier, "⚪")
    return f"{emoji} {tier}"


def display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display-ready DataFrame with renamed and formatted columns."""
    cols = {
        "sport":      "Sport",
        "tier":       "Tier",
        "game":       "Game",
        "game_time":  "Time",
        "bet_type":   "Bet Type",
        "pick":       "Pick",
        "confidence": "Confidence",
        "edge":       "Edge",
        "odds":       "Odds",
        "league":     "League",
    }
    present = [c for c in cols if c in df.columns]
    out = df[present].copy()
    out = out.rename(columns={c: cols[c] for c in present})

    if "Confidence" in out.columns:
        out["Confidence"] = out["Confidence"].apply(format_confidence)
    if "Edge" in out.columns:
        out["Edge"] = out["Edge"].apply(format_edge)
    if "Tier" in out.columns:
        out["Tier"] = out["Tier"].apply(tier_badge)

    return out
```

---

## Page: `pages/1_Today.py` — Today's Picks

Primary landing page. Shows all qualifying bets for today across all sports.

```
┌─────────────────────────────────────────────────────────┐
│  📅 Today's Picks — Wednesday, April 29, 2026           │
│                                                         │
│  🔥 Elite   ✅ Strong   ➡ Good                          │
│                                                         │
│  ┌────────┬──────────────────┬──────────┬──────────┐    │
│  │ Sport  │ Game             │ Pick     │ Conf     │    │
│  ├────────┼──────────────────┼──────────┼──────────┤    │
│  │ 🔥 NHL │ Leafs @ Bruins   │ Leafs ML │ 62.0%    │    │
│  │ ✅ MLB │ Yankees @ Sox    │ OVER 8.5 │ 58.5%    │    │
│  │ ➡ NBA  │ Lakers @ Celtics │ Celtics -4 │ 55.2% │    │
│  └────────┴──────────────────┴──────────┴──────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Layout

```python
import streamlit as st
import pandas as pd
from datetime import date
from utils.formatter import today_bets, sort_by_tier, display_columns, TIER_ORDER

df = st.session_state.get("all_bets_df", pd.DataFrame())
today_df = today_bets(df)

st.header(f"📅 Today's Picks — {date.today().strftime('%A, %B %d, %Y')}")

if today_df.empty:
    st.info("No picks available for today. Models may not have run yet, or all sports are in off-season.")
    st.stop()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Picks", len(today_df))
col2.metric("🔥 Elite", len(today_df[today_df["tier"] == "Elite"]))
col3.metric("✅ Strong", len(today_df[today_df["tier"] == "Strong"]))
col4.metric("Sports Active", today_df["sport"].nunique())

st.divider()

# Picks by tier tabs
tab_elite, tab_strong, tab_good, tab_all = st.tabs(
    ["🔥 Elite", "✅ Strong", "➡ Good", "All Picks"]
)

sorted_df = sort_by_tier(today_df)
display_df = display_columns(sorted_df)

with tab_elite:
    elite = display_df[display_df["Tier"].str.contains("Elite")]
    if elite.empty:
        st.info("No Elite picks today.")
    else:
        st.dataframe(elite, width='stretch', hide_index=True)

with tab_strong:
    strong = display_df[display_df["Tier"].str.contains("Strong")]
    if strong.empty:
        st.info("No Strong picks today.")
    else:
        st.dataframe(strong, width='stretch', hide_index=True)

with tab_good:
    good = display_df[display_df["Tier"].str.contains("Good")]
    st.dataframe(good, width='stretch', hide_index=True)

with tab_all:
    st.dataframe(display_df, width='stretch', hide_index=True)
```

---

## Page: `pages/2_By_Sport.py` — By Sport

Lets users filter to a single sport and see all current picks.

```python
import streamlit as st
import pandas as pd
from utils.formatter import today_bets, sort_by_tier, display_columns

df = st.session_state.get("all_bets_df", pd.DataFrame())

st.header("🏆 Picks by Sport")

if df.empty:
    st.info("No data loaded.")
    st.stop()

sports = sorted(df["sport"].unique())
selected = st.selectbox("Select Sport", options=sports)

sport_df = df[df["sport"] == selected]
today_df = today_bets(sport_df)

# Show "last updated" for this sport
if "generated_at" in df.columns:
    sport_gen = df[df["sport"] == selected]["generated_at"].max()
    st.caption(f"Last model run: {sport_gen}")

if today_df.empty:
    st.info(f"No picks for {selected} today. The sport may be in off-season.")
else:
    st.dataframe(
        display_columns(sort_by_tier(today_df)),
        width='stretch',
        hide_index=True,
    )
```

---

## Page: `pages/3_Best_Bets.py` — Best Bets

Shows only Elite and Strong picks across all sports. This is the "what should I bet
today" page for users who want a curated, short list.

### Card Layout

Each bet gets a card (use `st.container` with `border=True`):

```
┌──────────────────────────────────────────────────┐
│  🔥 ELITE  |  🏒 NHL  |  Apr 29, 19:00 ET       │
│  Maple Leafs @ Bruins                            │
│  Pick: Maple Leafs ML (+120)                    │
│  Confidence: 62.0%   Edge: +11.0%               │
└──────────────────────────────────────────────────┘
```

```python
import streamlit as st
import pandas as pd
from datetime import date
from utils.formatter import today_bets, sort_by_tier, TIER_EMOJI

df = st.session_state.get("all_bets_df", pd.DataFrame())
today_df = today_bets(df)

st.header("🔥 Best Bets Today")
st.caption("Elite and Strong picks across all sports")

best = today_df[today_df["tier"].isin(["Elite", "Strong"])]
best = sort_by_tier(best)

if best.empty:
    st.info("No Elite or Strong bets today.")
    st.stop()

for _, row in best.iterrows():
    with st.container(border=True):
        badge = TIER_EMOJI.get(row.get("tier"), "")
        sport_icon = {
            "NFL": "🏈", "NHL": "🏒", "NBA": "🏀", "MLB": "⚾",
            "MLS": "⚽", "EPL": "⚽", "LaLiga": "⚽", "Bundesliga": "⚽",
            "Ligue1": "⚽", "Rugby": "🏉", "NCAAF": "🏈", "Tennis": "🎾",
            "NCAAB": "🏀",
        }.get(row.get("sport", ""), "🎯")

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.markdown(f"**{badge} {row.get('tier', '')}**")
            st.markdown(f"{sport_icon} {row.get('sport', '')}")
        with c2:
            st.markdown(f"**{row.get('game', '')}**")
            st.markdown(f"Pick: `{row.get('pick', '')}`")
        with c3:
            conf = row.get("confidence")
            edge = row.get("edge")
            if conf:
                st.metric("Confidence", f"{conf*100:.1f}%")
            if edge is not None and not pd.isna(edge):
                st.metric("Edge", f"+{edge*100:.1f}%" if edge >= 0 else f"{edge*100:.1f}%")
```

---

## Page: `pages/4_Performance.py` — Model Performance

Shows a model report card per sport. Reads from `performance_summary.json` in each
sport repo (see Additional Artifacts below).

```
┌──────────────────────────────────────────────────┐
│  Sport  │ Win Rate │ ROI    │ Bets  │ Season     │
│─────────┼──────────┼────────┼───────┼────────────│
│  🏈 NFL  │  91.9%   │ +76.7% │ 685   │ 2024-25   │
│  🏒 NHL  │  62.0%   │ +18.4% │ 233   │ 2024-25   │
│  🏀 NBA  │  58.5%   │ +12.1% │ 512   │ 2024-25   │
└──────────────────────────────────────────────────┘
```

This page also links to each individual sport app (via `st.link_button`).

---

## Page: `pages/5_About.py` — About

- Brief description of what Sports Picks Grid is
- How the models work (each sport is a machine learning model, not human picks)
- Links to each individual sport app
- Responsible gambling disclaimer
- Link to the GitHub org

---

## Additional Artifacts to Add to Each Sport Repo

### `data_files/model_performance.json`

Each sport repo should also commit a performance summary file:

```json
{
  "sport": "NHL",
  "season": "2024-25",
  "last_updated": "2026-04-29",
  "bet_types": {
    "Moneyline": {
      "total_bets": 112,
      "wins": 69,
      "win_rate": 0.616,
      "roi": 0.184,
      "avg_edge": 0.063
    },
    "Spread": {
      "total_bets": 87,
      "wins": 51,
      "win_rate": 0.586,
      "roi": 0.092,
      "avg_edge": 0.048
    }
  }
}
```

The Performance page in Sports Picks Grid reads these files via the same GitHub raw
URL pattern:
```
https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/model_performance.json
```

---

## Responsive Layout Notes

- Use `st.columns()` with narrow ratios for the best bet cards on wide screens
- The `st.dataframe()` with `use_container_width=True` handles mobile well
- Avoid fixed pixel heights — let Streamlit size tables based on row count
- `st.container(border=True)` for bet cards is available in Streamlit ≥ 1.31

---

## Deployment

Deploy to Streamlit Cloud:

1. Push this repo to GitHub (public or private)
2. Visit https://share.streamlit.io
3. Connect the `gmalbert/sports-picks-grid` repo
4. Set main file to `predictions.py`
5. No secrets required (all data is from public GitHub raw URLs)

### Environment

```
# requirements.txt
streamlit>=1.36
pandas>=2.0
requests>=2.31
```

No ML libraries are needed in this repo — all predictions come pre-computed from the
sport repos.

---

## Build Order / Implementation Priority

Work through these in order to get a working end-to-end pipeline as quickly as possible:

1. **NFL export script** — easiest, `betting_recommendations_log.csv` already has all fields
2. **NHL export script** — `recommendations.json` is already close to the schema
3. **NBA export script** — reads today's prediction parquet file
4. **Sports Picks Grid app** — build with NFL + NHL + NBA data working first
5. **Tennis export script** — simple parquet read
6. **March Madness export** — reads existing JSON, mostly schema translation
7. **Soccer repos (EPL/La Liga/Bundesliga/Ligue-1/MLS)** — all require a `generate_picks.py`
   step since predictions are computed at runtime; do these together
8. **MLB export script** — requires adding `picks_today.parquet` to the ingestion pipeline
9. **Rugby export script** — requires running the value finder model in the export script
10. **College Football export** — weekly, lower urgency

This order maximizes the number of sports visible in the dashboard as early as possible.
