# Sports Picks Grid

**One dashboard. 13 sports. Every day's best bets — ranked by confidence.**

Sports Picks Grid pulls together daily betting recommendations from 13 separate machine-learning prediction apps and shows them all in one clean, easy-to-read place. No spreadsheets, no bouncing between tabs — just today's picks, sorted by how confident the models are.

Part of the **Betting Oracle** suite.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Sports Covered](#sports-covered)
- [How Confidence Tiers Work](#how-confidence-tiers-work)
- [The Pages](#the-pages)
- [How It Stays Up to Date](#how-it-stays-up-to-date)
- [Running It Yourself](#running-it-yourself)
- [Deploying to the Web](#deploying-to-the-web)
- [Project Structure](#project-structure)
- [Recent Changes](#recent-changes)
- [Roadmaps & Planning Docs](#roadmaps--planning-docs)

---

## What It Does

Every night, each of the 13 sport-specific prediction apps runs its machine-learning model, crunches the latest data, and saves a file called `best_bets_today.json` to its GitHub repository. Sports Picks Grid reads all 13 of those files and displays everything in a single dashboard.

**This app contains no models of its own.** It is purely a reader and display layer — think of it as a scoreboard that shows results from the individual sport apps.

Key behaviors:
- Picks for **today's games** are shown front and center
- Picks for **upcoming games** (up to 7 days out) are also included — so tournament brackets, future match weeks, and scheduled events don't disappear just because they're not today
- When a sport is in its off-season and has no upcoming games, the most recently available picks are shown instead so the page is never blank
- Each pick shows the **game**, **bet type**, **recommended side**, **betting odds** (formatted as +135 or -140), **model confidence**, and **edge vs. the market**
- The timestamp of when each sport's model last ran is shown so you know how fresh the data is

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Sports Covered

| Sport | League | Prediction App |
|---|---|---|
| ⚾ MLB | Major League Baseball | [baseball-predictions](https://github.com/gmalbert/baseball-predictions) |
| 🏒 NHL | National Hockey League | [hockey-predictions](https://github.com/gmalbert/hockey-predictions) |
| 🏀 NBA | National Basketball Association | [nba-predictions](https://github.com/gmalbert/nba-predictions) |
| 🏈 NFL | National Football League | [nfl-predictions](https://github.com/gmalbert/nfl-predictions) |
| ⚽ MLS | Major League Soccer | [mls-predictions](https://github.com/gmalbert/mls-predictions) |
| ⚽ EPL | English Premier League | [premier-league](https://github.com/gmalbert/premier-league) |
| ⚽ La Liga | Spanish La Liga | [la-liga](https://github.com/gmalbert/la-liga) |
| ⚽ Bundesliga | German Bundesliga | [bundesliga](https://github.com/gmalbert/bundesliga) |
| ⚽ Ligue 1 | French Ligue 1 | [ligue-1](https://github.com/gmalbert/ligue-1) |
| 🏉 Rugby | Multi-league | [rugby](https://github.com/gmalbert/rugby) |
| 🏈 NCAAF | College Football | [college-football-predictions](https://github.com/gmalbert/college-football-predictions) |
| 🎾 Tennis | ATP Tour | [tennis-predictions](https://github.com/gmalbert/tennis-predictions) |
| 🏀 NCAAB | College Basketball / March Madness | [march-madness](https://github.com/gmalbert/march-madness) |

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## How Confidence Tiers Work

Each pick is assigned a tier based on two things: how confident the model is in its prediction, and how much of an "edge" it has over the bookmaker's implied odds. Edge means the model thinks the true probability of winning is higher than what the betting line implies.

| Tier | Badge | What It Means |
|---|---|---|
| Elite | 🔥 | Highest confidence + strongest edge. The model is very sure and the market hasn't caught up. |
| Strong | ✅ | Good confidence + positive expected value. A solid bet worth considering. |
| Good | ➡ | Moderate signal. Worth tracking, but size down or treat as secondary. |
| Standard | ⚪ | Tracked internally. Not shown in the dashboard by default. |

> **What is "edge"?** If a team has a 60% real chance of winning but the bookmaker's line implies only a 50% chance, the edge is +10%. That gap is where value lives.

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## The Pages

### 📅 Today's Picks
The home page. Shows every pick for today and the next 7 days, grouped into tabs by confidence tier (Elite / Strong / Good / All). A summary bar at the top tells you how many picks are available and across how many sports. Includes a "Date" column so you can see at a glance which games are today vs. coming up later in the week.

### 🏆 By Sport
Pick a single sport from the dropdown and see all its current picks in one table. Shows the timestamp of when that sport's model last ran. If there are no games in the next 7 days (off-season), the most recent historical picks are shown with a note.

### 🔥 Best Bets
A card-style view of only the Elite and Strong picks. Each card shows the matchup, the recommended bet, the odds in standard American format (+135 / -140), confidence, edge, and any model notes. If the game is not today, the date is shown prominently on the card.

### 📈 Performance
Model accuracy and record-keeping for each sport app. Shows win rate, ROI, and links back to the individual sport dashboards. (Populated once each sport repo starts writing `model_performance.json`.)

### ℹ️ About
Explains how the app works, what the tiers mean, and which sports are covered.

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## How It Stays Up to Date

A GitHub Action called `aggregate.yml` runs automatically every day at **12:00 PM UTC**:

1. It runs `scripts/fetch_all_picks.py`, which visits each of the 13 sport repos
2. It downloads the latest `best_bets_today.json` from each one
3. It saves those files to the `data_cache/` folder in this repo and commits them

This means the dashboard always has a local copy of the picks even if GitHub's raw file servers are slow. Individual sport repos can also trigger an early refresh via a `repository_dispatch` event after their own nightly pipeline finishes.

If you run the app locally without a populated `data_cache/`, it falls back to fetching each sport's JSON live from GitHub.

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Running It Yourself

```bash
pip install -r requirements.txt
streamlit run predictions.py
```

That's it. No API keys, no database, no environment variables needed.

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Deploying to the Web

1. Connect this repo to [Streamlit Cloud](https://streamlit.io/cloud)
2. Set the entry point to `predictions.py`
3. No secrets needed — all data comes from public GitHub URLs

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Project Structure

```
sports-picks-grid/
├── predictions.py              # App entry point — page config, sidebar, navigation
├── footer.py                   # Shared Betting Oracle footer
├── utils/
│   ├── fetcher.py              # Loads all 13 JSONs → flat DataFrame (with generated_at)
│   └── formatter.py            # Tier badges, odds formatting, display columns, sorting
├── pages/
│   ├── 1_Today.py              # Today + upcoming picks by tier (7-day window)
│   ├── 2_By_Sport.py           # Filter picks by sport; shows last model run time
│   ├── 3_Best_Bets.py          # Card layout — Elite + Strong only, with odds display
│   ├── 4_Performance.py        # Model report cards + links to sport apps
│   └── 5_About.py              # Description, tiers, sport list
├── scripts/
│   └── fetch_all_picks.py      # Pre-fetches all JSONs into data_cache/
├── data_cache/                  # Local copies committed by the nightly GitHub Action
├── .github/
│   └── workflows/
│       └── aggregate.yml       # Daily 12:00 PM UTC fetch + commit
└── docs/
    ├── 01-master-architecture.md
    ├── 02-unified-schema.md
    ├── 03-repo-export-specs.md
    ├── 04-github-actions.md
    └── 05-dashboard-app.md
```

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Recent Changes

### April 2026 — Upcoming Games, Odds Formatting, and Data Freshness

**Upcoming games window (7 days)**
Previously the dashboard only showed picks where the game was scheduled for *today*. Sports like NCAAB (March Madness brackets) and NCAAF export picks for games that are still days away. Those picks were invisible. All pages now show today's games plus any games in the next 7 days. A "Date" column makes it easy to see which games are today vs. later in the week.

**American odds formatting**
Betting odds are now displayed in standard sportsbook format: `+135` means you win $135 on a $100 bet; `-140` means you need to bet $140 to win $100. Previously the raw number was shown without the sign, which could be confusing.

**Sport emoji in tables**
Each row in the picks tables now shows a sport icon (⚾ 🏒 🏀 etc.) alongside the sport name, making it faster to scan a mixed-sport table.

**Model freshness timestamp**
The "By Sport" page now shows when each sport's model last ran, pulled from the `generated_at` field in each sport repo's JSON. Previously this field was read from the file's metadata but never made it into the display.

**Off-season fallback improved**
When a sport has no upcoming games (NFL in April, for example), the "By Sport" page now clearly states "no picks for today or upcoming" before falling back to the most recent historical picks.

**Best Bets cards — date on future games**
Cards on the Best Bets page now display the game date prominently when the game is not today, so it's clear you're looking at a future pick, not today's action.

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## Roadmaps & Planning Docs

Detailed planning and design documents live in the [`docs/`](docs/) folder:

| Doc | What's in it |
|---|---|
| [01 — Master Architecture](docs/01-master-architecture.md) | How this app fits into the broader Betting Oracle suite |
| [02 — Unified Schema](docs/02-unified-schema.md) | The standard JSON format every sport repo must produce |
| [03 — Repo Export Specs](docs/03-repo-export-specs.md) | How each sport repo's export script works |
| [04 — GitHub Actions](docs/04-github-actions.md) | Nightly automation setup and `repository_dispatch` triggers |
| [05 — Dashboard App](docs/05-dashboard-app.md) | Page-by-page design notes for this Streamlit app |

<p align="right"><a href="#table-of-contents">▲ Back to Top</a></p>

---

## License

MIT — see individual sport repos for their own licenses.
