# Cross-Repo Standards & Best Practices

> Generated: 2026-07-31 | Applies to all Betting Oracle suite repos

---

## Overview

This document consolidates best practices that should be applied across ALL
Betting Oracle prediction apps to ensure consistency, quality, and maintainability.

---

## 1. Universal Coding Standards

### 1.1 Type Hints (Required)

All function signatures must include type hints:

```python
# CORRECT
def compute_edge(model_prob: float, market_odds: int) -> float:
    ...

# WRONG — no type hints
def compute_edge(model_prob, market_odds):
    ...
```

### 1.2 File Path Convention (Required)

```python
# CORRECT — use pathlib.Path
from pathlib import Path
DATA_DIR = Path("data_files")
model_path = DATA_DIR / "models" / "xgb_model.joblib"

# WRONG — string concatenation
model_path = "data_files/models/xgb_model.joblib"
```

### 1.3 DataFrame Schema Validation

Before writing Parquet files, validate schema:

```python
import pyarrow as pa
import pyarrow.parquet as pq

PICKS_SCHEMA = pa.schema([
    pa.field("game_date", pa.string()),
    pa.field("game", pa.string()),
    pa.field("pick", pa.string()),
    pa.field("bet_type", pa.string()),
    pa.field("confidence", pa.float32()),
    pa.field("edge", pa.float32()),
    pa.field("odds", pa.int16()),
    pa.field("tier", pa.string()),
    pa.field("notes", pa.string()),
])

def save_picks_parquet(df: pd.DataFrame, path: Path) -> None:
    table = pa.Table.from_pandas(df, schema=PICKS_SCHEMA, preserve_index=False)
    pq.write_table(table, path)
```

---

## 2. Universal best_bets_today.json Schema

ALL repos must export `data_files/best_bets_today.json` in this format:

```json
{
  "meta": {
    "sport": "SPORT_NAME",
    "generated_at": "2026-07-31T10:00:00Z",
    "model_version": "1.0.0",
    "season": "2026"
  },
  "bets": [
    {
      "game_date": "2026-07-31",
      "game": "Team A vs Team B",
      "game_time": "7:05 PM ET",
      "bet_type": "moneyline",
      "pick": "Team A",
      "confidence": 0.67,
      "edge": 0.11,
      "odds": -110,
      "tier": "Elite",
      "notes": "Optional context"
    }
  ]
}
```

### Tier Classification Standard

| Tier | Edge | Confidence | Behavior |
|------|------|------------|----------|
| Elite | > 6% | > 60% | Always display, high priority |
| Strong | 3-6% | > 55% | Display prominently |
| Good | 1-3% | > 52% | Display with caveat |
| Standard | < 1% | Any | Do not display or display last |

---

## 3. Streamlit Anti-Patterns to Avoid

### 3.1 Never call st.set_page_config() in sub-pages

```python
# WRONG — in any pages/*.py file
st.set_page_config(page_title="My Page")  # Will crash on navigation

# CORRECT — only in predictions.py or app.py entry point
```

### 3.2 Never use use_container_width

```python
# WRONG — deprecated parameter
st.dataframe(df, use_container_width=True)
st.plotly_chart(fig, use_container_width=True)

# CORRECT
st.dataframe(df, width="stretch")
st.plotly_chart(fig, width="stretch")
```

### 3.3 Always use @st.cache_data for heavy data loads

```python
# CORRECT — wrap all data loading
@st.cache_data(ttl=3600)
def load_historical_data() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "historical.parquet")

# WRONG — uncached data load called on every render
def render_page():
    df = pd.read_parquet(DATA_DIR / "historical.parquet")  # Loads every time!
```

---

## 4. Universal Temporal Leakage Prevention

### The Golden Rule: Always Use shift(1)

```python
# CORRECT — no leakage
df["win_rate_l5"] = (
    df.groupby("team")["won"]
    .transform(lambda x: x.shift(1).rolling(5, min_periods=1).mean())
)

# WRONG — current game included in rolling window
df["win_rate_l5"] = (
    df.groupby("team")["won"]
    .transform(lambda x: x.rolling(5, min_periods=1).mean())  # BUG
)
```

### Walk-Forward Validation (Required for All Models)

```python
from sklearn.model_selection import TimeSeriesSplit

def validate_model_temporal(X: pd.DataFrame, y: pd.Series,
                              model, date_col: str = "date") -> dict:
    """Standard temporal validation used across all Betting Oracle models."""
    X = X.sort_values(date_col) if date_col in X.columns else X
    tscv = TimeSeriesSplit(n_splits=5, gap=7)
    from sklearn.metrics import roc_auc_score, brier_score_loss
    results = []
    for tr, val in tscv.split(X):
        model.fit(X.iloc[tr], y.iloc[tr])
        preds = model.predict_proba(X.iloc[val])[:, 1]
        results.append({
            "auc": roc_auc_score(y.iloc[val], preds),
            "brier": brier_score_loss(y.iloc[val], preds),
        })
    return {k: np.mean([r[k] for r in results]) for k in ["auc", "brier"]}
```

---

## 5. Security Standards

### 5.1 Never Hardcode API Keys

```python
# WRONG
ODDS_API_KEY = "abc123secretkey"

# CORRECT
import os
ODDS_API_KEY = os.environ.get("ODDS_API_KEY") or st.secrets.get("ODDS_API_KEY")
if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY not set in environment or secrets")
```

### 5.2 Never Use Raw String SQL

```python
# WRONG — SQL injection risk
query = f"SELECT * FROM fights WHERE fighter = '{user_input}'"

# CORRECT — parameterized query
query = "SELECT * FROM fights WHERE fighter = :fighter"
session.execute(text(query), {"fighter": user_input})
```

### 5.3 Validate All External Data

```python
from pydantic import BaseModel, validator

class BetRecord(BaseModel):
    game: str
    pick: str
    odds: int
    confidence: float
    edge: float

    @validator("confidence")
    def confidence_must_be_valid_probability(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return v

    @validator("odds")
    def odds_must_be_valid(cls, v):
        if not (-10000 <= v <= 10000):
            raise ValueError("odds out of reasonable range")
        return v
```

---

## 6. GitHub Actions Templates

### 6.1 Standard Daily Pipeline

```yaml
# .github/workflows/daily_pipeline.yml
name: Daily Picks Pipeline
on:
  schedule:
    - cron: '0 14 * * *'  # 10 AM ET
  workflow_dispatch:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Run pipeline
        env:
          ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
        run: python scripts/run_daily_pipeline.py
      - name: Export picks
        run: python scripts/export_best_bets.py
      - uses: EndBug/add-and-commit@v9
        with:
          message: "Auto: daily picks $(date +%Y-%m-%d)"
          add: "data_files/best_bets_today.json"
```

---

## 7. Model Monitoring Standards

All ML repos should implement these monitoring checks:

```python
# scripts/monitor_model_health.py
import pandas as pd, numpy as np

def run_model_health_checks(predictions: pd.DataFrame, actuals: pd.DataFrame) -> dict:
    """Standard health checks for all Betting Oracle ML models."""
    merged = predictions.merge(actuals, on="game_id", how="inner")

    if len(merged) < 10:
        return {"status": "INSUFFICIENT_DATA", "n_settled": len(merged)}

    # 1. Accuracy check
    accuracy = (merged["predicted_winner"] == merged["actual_winner"]).mean()

    # 2. Calibration check
    if "model_prob" in merged.columns:
        calibration_error = abs(merged["model_prob"].mean() - accuracy)
    else:
        calibration_error = None

    # 3. Edge vs CLV check (are we beating closing lines?)
    if "closing_odds" in merged.columns and "model_prob" in merged.columns:
        merged["closing_implied"] = merged["closing_odds"].apply(
            lambda o: 100 / (abs(o) + 100) if o < 0 else o / (o + 100)
        )
        clv_beat_rate = (merged["model_prob"] > merged["closing_implied"]).mean()
    else:
        clv_beat_rate = None

    # 4. Tier accuracy check
    tier_accuracy = merged.groupby("tier").apply(
        lambda g: (g["predicted_winner"] == g["actual_winner"]).mean()
    ).to_dict()

    status = "HEALTHY"
    if accuracy < 0.45:
        status = "DEGRADED"
    elif calibration_error and calibration_error > 0.10:
        status = "MISCALIBRATED"

    return {
        "status": status,
        "accuracy": round(accuracy, 3),
        "n_settled": len(merged),
        "calibration_error": round(calibration_error, 4) if calibration_error else None,
        "clv_beat_rate": round(clv_beat_rate, 3) if clv_beat_rate else None,
        "tier_accuracy": tier_accuracy,
    }
```

---

## 8. Documentation Standards

Every repo should maintain these docs in `/docs/`:

| File | Contents |
|------|----------|
| `SITE_SUMMARY.md` | App purpose, tech stack, entry point |
| `architecture.md` | Data flow diagram, component overview |
| `MODEL_SUGGESTED_ENHANCEMENTS.md` | ML improvement ideas |
| `12_MONTH_ROADMAP.md` | This document's companion |
| `NEXT_FEATURES.md` | Short-term (current quarter) feature list |
| `6_MONTH_FEATURES.md` | Mid-term roadmap |

---

## 9. Responsible Gambling Compliance

All prediction apps **must** include:

```python
# Streamlit: include on every page footer
def add_responsible_gambling_notice() -> None:
    st.markdown(
        """<div style='text-align:center;color:gray;font-size:11px;padding:16px'>
        ⚠️ This tool is for educational and entertainment purposes only.
        Never bet more than you can afford to lose.
        If you have a gambling problem, call 1-800-522-4700 (NCPG Helpline).
        </div>""",
        unsafe_allow_html=True,
    )
```
