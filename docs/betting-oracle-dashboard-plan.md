# Betting Oracle — Unified Dashboard Architecture Plan

## Overview

You have at least 3 public GitHub repos following a consistent Streamlit + XGBoost pattern, each writing daily predictions to a `data_files/` directory. The goal is a unified daily dashboard that aggregates the best bets across all sports without significantly changing how any individual repo works.

---

## Confirmed Repos

| Repo | Sport | Key Output Files | Nightly Action |
|---|---|---|---|
| `gmalbert/nfl-predictions` | NFL | `betting_recommendations_log.csv`, predictions CSV | ✅ 3AM UTC (Sept–Feb) |
| `gmalbert/hockey-predictions` | NHL | `data_files/` CSVs | ✅ Yes |
| `gmalbert/golf-predictions` | PGA Tour | `data_files/` parquet + CSV | Likely |

All three use the same general pattern: Streamlit app → model pipeline → output written to `data_files/` → GitHub Actions runs nightly.

---

## Recommended Architecture

### The Core Idea

Don't change how the individual repos work — just standardize their *output* and build a lightweight aggregator on top.

```
nfl-predictions/data_files/best_bets_today.json  ─┐
hockey-predictions/data_files/best_bets_today.json ─┼──► betting-oracle-dashboard
golf-predictions/data_files/best_bets_today.json  ─┘         (new repo)
```

The dashboard repo reads from each sport repo at load time via GitHub raw content URLs — no API keys, no server, no database needed.

---

## Step-by-Step Implementation

### Step 1: Standardize Output Across All Repos

Add a small export script to each sport repo that runs at the **end of the existing nightly pipeline** and writes a `data_files/best_bets_today.json` file with a consistent schema.

**Recommended JSON schema:**

```json
[
  {
    "sport": "NFL",
    "game": "Chiefs @ Raiders",
    "game_date": "2025-09-14",
    "game_time": "20:20 ET",
    "bet_type": "Spread",
    "pick": "Raiders +3.5",
    "confidence": 0.69,
    "edge": 0.08,
    "tier": "Elite",
    "model": "XGBoost",
    "generated_at": "2025-09-14T03:45:00Z"
  }
]
```

**Fields to include:**

- `sport` — string identifier (NFL, NHL, PGA, etc.)
- `game` — human-readable matchup
- `game_date` / `game_time` — when the game is
- `bet_type` — Spread, Moneyline, Over/Under, Outright Winner
- `pick` — the actual recommended bet
- `confidence` — model probability (0–1)
- `edge` — model prob minus implied odds prob (value indicator)
- `tier` — Elite / Strong / Good / Standard (already used in NFL repo)
- `model` — which model generated this (useful once you add more)
- `generated_at` — ISO timestamp so the dashboard can show data freshness

> **Note:** The NFL repo already has `tier` and `edge` logic. Extract that pattern and replicate it in hockey and golf.

---

### Step 2: Update Each Repo's GitHub Action

At the end of each sport's nightly workflow, add a step that runs the export script and commits the output:

```yaml
# .github/workflows/nightly-update.yml (addition to existing file)
- name: Export best bets for dashboard
  run: python scripts/export_best_bets.py

- name: Commit best_bets_today.json
  run: |
    git config user.name "github-actions"
    git config user.email "actions@github.com"
    git add data_files/best_bets_today.json
    git diff --staged --quiet || git commit -m "chore: update best_bets_today [skip ci]"
    git push
```

The `[skip ci]` tag prevents an infinite loop of triggering new Actions on the commit.

---

### Step 3: Create `betting-oracle-dashboard` Repo

A new repo with a single Streamlit app that reads from all sport repos via raw GitHub URLs.

**Raw URL pattern:**
```
https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json
```

**Basic aggregator app (`app.py`):**

```python
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

SPORT_REPOS = {
    "🏈 NFL":   "nfl-predictions",
    "🏒 NHL":   "hockey-predictions",
    "⛳ PGA":   "golf-predictions",
}

BASE_URL = "https://raw.githubusercontent.com/gmalbert/{repo}/main/data_files/best_bets_today.json"

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_all_bets():
    all_bets = []
    for label, repo in SPORT_REPOS.items():
        url = BASE_URL.format(repo=repo)
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            bets = r.json()
            for bet in bets:
                bet["_label"] = label
            all_bets.extend(bets)
        except Exception as e:
            st.warning(f"Could not load {label}: {e}")
    return pd.DataFrame(all_bets)

st.set_page_config(page_title="Betting Oracle", layout="wide")
st.title("🔮 Betting Oracle — Daily Best Bets")

df = load_all_bets()

# Filter to today's bets
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
today_df = df[df["game_date"] == today] if "game_date" in df.columns else df

# Sport tabs
sports = today_df["_label"].unique()
tabs = st.tabs(list(sports))

for tab, sport in zip(tabs, sports):
    with tab:
        sport_df = today_df[today_df["_label"] == sport]
        st.dataframe(sport_df, width='stretch')
```

---

### Step 4: Deploy

**Option A — Streamlit Cloud (Recommended for now)**
- Free tier, deploys from GitHub in ~5 minutes
- Connects directly to the dashboard repo
- Visit [share.streamlit.io](https://share.streamlit.io) → connect repo → done
- Custom domain supported (point `betting-oracle.com` at it)

**Option B — GitHub Pages (Static)**
- The aggregator Action generates a static `index.html` instead of a Streamlit app
- Zero runtime cost, blazing fast, scales to any traffic
- Best long-term if you go public-facing
- Requires building a static HTML/JS frontend instead of Streamlit

**Option C — Vercel or Render**
- Easy deploys, free tiers available
- Better for a more polished public site down the road
- Works with a FastAPI backend if you ever want to add user features (saved picks, bet tracking, etc.)

---

## Additional Considerations

### 🔄 Action Timing & Dependencies

Your NFL repo runs at 3AM UTC. If you want the dashboard to always show fresh data, stagger the sport repo schedules slightly and run the aggregator dashboard Action **last** (e.g., 4AM UTC). You can also trigger the dashboard Action using `workflow_dispatch` or `repository_dispatch` from the sport repos when they finish.

```yaml
# At end of nfl-predictions nightly action:
- name: Trigger dashboard refresh
  uses: peter-evans/repository-dispatch@v2
  with:
    token: ${{ secrets.DASHBOARD_PAT }}
    repository: gmalbert/betting-oracle-dashboard
    event-type: sport-update
    client-payload: '{"sport": "NFL"}'
```

This requires a Personal Access Token (PAT) with `repo` scope stored as a secret.

### 📅 Seasonality — Handle Off-Season Gracefully

The NFL repo already skips off-season runs (March–August). The dashboard should handle missing or empty `best_bets_today.json` gracefully:
- Show a "No games today" card per sport
- Show the last available date the model ran
- Don't crash if a file doesn't exist yet (especially golf, which is tournament-based not daily)

### 🏌️ Golf Is Different

PGA predictions are tournament-based, not daily matchups. Consider a separate schema for golf — "best outright winner picks for this week's tournament" rather than a game-by-game format. The `bet_type` field can accommodate this (`Outright Win`, `Top 5`, `Top 10`, `Make Cut`), but the dashboard UI should render golf cards differently.

### 📊 Historical Performance Tracking

Each sport repo tracks ROI and win rate separately. Consider adding a `performance` block to the JSON or a separate `model_performance.json`:

```json
{
  "sport": "NFL",
  "season": "2024",
  "spread_win_rate": 0.919,
  "spread_roi": 0.755,
  "moneyline_win_rate": 0.595,
  "moneyline_roi": 0.654,
  "last_updated": "2025-01-10"
}
```

The dashboard can then show a "Model Report Card" section alongside daily picks, which builds credibility if you go public.

### 🔔 Notification Layer (RSS is still valuable here)

The NFL repo already has `scripts/generate_rss.py`. Once you have a unified JSON, generate a **single cross-sport RSS feed** from the dashboard repo:

- All Elite/Strong bets across all sports in one feed
- Tools like [follow.it](https://follow.it) or [Feedly](https://feedly.com) can turn it into email digests
- Also useful for future Discord/Slack bot integration

### 🔐 Public vs. Private Considerations

If you eventually make this public:
- Don't expose raw model files or training data — just the output JSONs
- Consider rate-limiting or caching the dashboard's GitHub raw requests (the `ttl=3600` cache in the Streamlit example helps here)
- GitHub raw content is served via CDN and is very fast, but has soft rate limits for unauthenticated requests — if traffic grows, mirror the JSON to a cheap CDN or S3 bucket
- Add a clear disclaimer about responsible gambling (the NFL repo already has one — replicate it on the dashboard)

### 🧩 Future Features Worth Planning For

| Feature | Complexity | Value |
|---|---|---|
| Email digest of daily picks | Low | High |
| Discord bot posting daily picks | Low | Medium |
| Odds API integration (live line movement) | Medium | High |
| More sports (NBA, MLB, NCAAF) | Low (if repos exist) | High |
| Mobile-optimized UI | Low (Streamlit handles it) | High if public |

### 📁 Suggested Repo Structure

```
betting-oracle-dashboard/
├── .github/
│   └── workflows/
│       └── aggregate.yml       # Runs after sport repos, refreshes dashboard
├── predictions.py                      # Main Streamlit dashboard
├── pages/
│   ├── performance.py          # Model report cards
│   ├── history.py              # Historical picks archive
│   └── about.py                # How the models work
├── utils/
│   ├── fetcher.py              # GitHub raw URL fetching logic
│   ├── formatter.py            # Standardize data across sports
│   └── rss_generator.py        # Unified RSS feed generator
├── data_cache/                 # Optional: locally cached JSONs for fallback
├── requirements.txt
└── README.md
```

---

## Quick-Start Checklist

- [ ] Add `scripts/export_best_bets.py` to each sport repo
- [ ] Update each nightly Action to run the export and commit `best_bets_today.json`
- [ ] Create `gmalbert/betting-oracle-dashboard` repo
- [ ] Build the basic aggregator Streamlit app
- [ ] Deploy to Streamlit Cloud (free)
- [ ] Point `betting-oracle.com` at the Streamlit app
- [ ] Add unified RSS generation from the dashboard repo
- [ ] Handle off-season / empty data gracefully per sport
- [ ] Add model performance JSON to each repo

---

## Why Not RSS as the Primary Mechanism?

RSS works well for *pushing notifications* but not for *displaying a dashboard*. The two complement each other:

- **JSON → Dashboard**: what you see when you open the site
- **RSS → Subscriptions**: how you get notified without opening the site

The NFL repo already scaffolded an RSS generator (`scripts/generate_rss.py`). Once the unified JSON exists, extending that to a cross-sport feed is a small addition.

---

*Last updated: April 2026*
