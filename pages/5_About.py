"""
pages/5_About.py — About Sports Picks Grid.
"""
import streamlit as st

st.header("ℹ️ About Sports Picks Grid")

st.markdown(
    """
    **Sports Picks Grid** is a unified daily dashboard that aggregates
    betting recommendations from machine learning models across 26 sport-specific
    prediction repositories.

    ---

    ### How It Works

    Each sport repo runs a nightly GitHub Action that:

    1. Fetches the latest data (schedules, odds, stats)
    2. Re-runs the prediction model
    3. Writes a standardized `best_bets_today.json` to its `data_files/` folder

    WNBA uses its web JSON feed; paper-only, no-bet, and unreleased predictions are withheld.
    Sports Picks Grid reads source JSON files and displays today's top picks in one place.
    **No models run here** — this app is a reader and aggregator only.

    ---

    ### Confidence Tiers

    | Tier | Badge | Description |
    |---|---|---|
    | Elite | 🔥 | Edge ≥ 6% under the canonical edge-v1 definition |
    | Strong | ✅ | Edge ≥ 3% and < 6% |
    | Good | ➡ | Edge ≥ 1% and < 3% |
    | Standard | ⚪ | Tracked internally but not displayed by default |

    Edge is defined as **model probability minus the market's implied probability** (derived
    from the bookmaker's odds). A positive edge means the model believes the bet is
    underpriced.

    ---

    ### Sports Covered

    | Sport | League | Model Type |
    |---|---|---|
    | ⚾ MLB | Major League Baseball | XGBoost — Moneyline, Run Line, Over/Under |
    | 🏒 NHL | National Hockey League | Elo + Dixon-Coles — ML, Puck Line, Totals |
    | 🏀 NBA | National Basketball Association | XGBoost Ensemble — ML, Spread, Totals |
    | 🏈 NFL | National Football League | XGBoost — Spread, Moneyline, Totals, Props |
    | ⚽ MLS | Major League Soccer | VotingClassifier — H/D/A |
    | ⚽ EPL | English Premier League | VotingClassifier — H/D/A |
    | ⚽ LaLiga | Spanish La Liga | VotingClassifier — H/D/A |
    | ⚽ Bundesliga | German Bundesliga | VotingClassifier — H/D/A |
    | ⚽ Ligue 1 | French Ligue 1 | VotingClassifier — H/D/A |
    | 🏉 Rugby | Multi-league | Elo + Dixon-Coles — ML, Spread, Totals |
    | 🏈 NCAAF | College Football | XGBoost — Spread, Totals, Moneyline |
    | 🎾 Tennis | ATP Tour | XGBoost — Match Winner |
    | 🏀 NCAAB | College Basketball / March Madness | Ensemble — Spread, Moneyline |
    | 🏏 Cricket | Cricket | Match and market predictions |
    | 🏓 Table Tennis | Table Tennis | Match predictions |
    | 🥊 Boxing | Boxing | Fight moneyline predictions |
    | 🎯 Darts | PDC Darts | Match and props modeling |
    | ⚽ Portugal | Portuguese Primeira Liga | Poisson goal and match-result models |
    | ⚽ Netherlands | Dutch Eredivisie | Poisson goal and match-result models |
    | ⚽ Belgium | Belgian Pro League | Poisson goal and match-result models |
    | ⚽ Scotland | Scottish Premiership | Poisson goal and match-result models |
    | ⚽ Turkey | Turkish Süper Lig | Poisson goal and match-result models |
    | 🏇 HorseRacing | Horse Racing | Race win predictions |
    | ⛳ Golf | Golf | Tournament predictions |
    | 🏀 WNBA | Women's National Basketball Association | Calibrated ensemble — release-gated moneyline predictions |
    | 🎮 Esports | LoL, CS2, Dota 2, VALORANT, R6, Overwatch | Historical Elo — match winner vs saved Kalshi asks |

    ---

    ### Source Repositories

    All models are open-source and hosted on GitHub:

    - [baseball-predictions](https://github.com/gmalbert/baseball-predictions)
    - [hockey-predictions](https://github.com/gmalbert/hockey-predictions)
    - [nba-predictions](https://github.com/gmalbert/nba-predictions)
    - [nfl-predictions](https://github.com/gmalbert/nfl-predictions)
    - [mls-predictions](https://github.com/gmalbert/mls-predictions)
    - [premier-league](https://github.com/gmalbert/premier-league)
    - [la-liga](https://github.com/gmalbert/la-liga)
    - [bundesliga](https://github.com/gmalbert/bundesliga)
    - [ligue-1](https://github.com/gmalbert/ligue-1)
    - [rugby](https://github.com/gmalbert/rugby)
    - [college-football-predictions](https://github.com/gmalbert/college-football-predictions)
    - [tennis-predictions](https://github.com/gmalbert/tennis-predictions)
    - [march-madness](https://github.com/gmalbert/march-madness)
    - [cricket](https://github.com/gmalbert/cricket)
    - [table-tennis](https://github.com/gmalbert/table-tennis)
    - [boxing](https://github.com/gmalbert/boxing)
    - [esports](https://github.com/gmalbert/esports)
    - [darts](https://github.com/gmalbert/darts)
    - [portugal-soccer](https://github.com/gmalbert/portugal-soccer)
    - [netherlands-soccer](https://github.com/gmalbert/netherlands-soccer)
    - [belgium-soccer](https://github.com/gmalbert/belgium-soccer)
    - [scotland-premiership](https://github.com/gmalbert/scotland-premiership)
    - [turkey-soccer](https://github.com/gmalbert/turkey-soccer)
    - [horse-racing-predictions](https://github.com/gmalbert/horse-racing-predictions)
    - [golf-predictions](https://github.com/gmalbert/golf-predictions)
    - [wnba-predictions](https://github.com/gmalbert/wnba-predictions)

    ---

    ### ⚠️ Responsible Gambling Disclaimer

    > These picks are generated by statistical models for **entertainment and research
    > purposes only**. They are not financial advice. Models can and do lose. Never bet
    > more than you can afford to lose. If gambling is causing you harm, visit
    > [ncpgambling.org](https://www.ncpgambling.org) or call 1-800-GAMBLER.
    """
)
