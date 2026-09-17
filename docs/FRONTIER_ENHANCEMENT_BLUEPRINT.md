# Frontier Enhancement Blueprint

The current architecture already defines cross-repo schemas, fetch/grade workflows, data-quality checks, portfolio concepts, Kelly staking, and a dashboard. The next step is to turn the grid into a decision ledger with verifiable identity, price history, and correlated exposure controls.

## Canonical bet identity

Text labels are not durable keys. Define an event/market/selection identity that survives team aliases and price changes.

```python
class BetKey(BaseModel):
    sport: str
    league: str
    event_id: str
    market: str
    period: str = "full_game"
    selection: str
    line: Decimal | None = None

class OfferedBet(BaseModel):
    key: BetKey
    book: str
    odds_decimal: Decimal
    observed_at: datetime
    source_sha: str
```

The aggregator should deduplicate by `BetKey`, retain every offer, and choose the best executable price only after freshness/availability checks.

## Correlated portfolio optimizer

Estimate shared exposure through team, game, sport, market, and latent-factor tags. Optimize expected log growth under maximum sport/game/day loss and uncertainty-adjusted edge constraints.

```python
def portfolio_objective(stakes, edge, covariance, risk_aversion=2.0):
    return stakes @ edge - risk_aversion * (stakes @ covariance @ stakes)
```

Use conservative covariance shrinkage and scenario stress tests; provide a simple capped fractional-Kelly fallback.

## Performance attribution

Separate model selection, price shopping, timing, grading, and luck. Persist prediction probability, available price, taken price, closing price, result, source versions, and timestamps. Report CLV and calibration before ROI.

## Product workflow

- “Action queue” showing only fresh, executable, policy-compliant bets.
- Exposure heatmap by game/team/sport and worst-case correlated scenario.
- Price-shopping and movement view with stale-book warnings.
- Reconciliation inbox for duplicate events, grading conflicts, and void rules.
- Daily decision journal: what was recommended, what changed, and why.
- Responsible-wagering limits that cannot be bypassed by UI filters.

## Contract and release gates

Add contract fixtures from every producer repo and consumer-driven CI. Fail closed on unknown schema major versions, naive timestamps, duplicate bet keys, probabilities outside `[0,1]`, or prices older than policy. Canary each new producer and preserve the last healthy artifact. Track source freshness SLO, unresolved-grade count, calibration, CLV, and exposure-limit breaches.
