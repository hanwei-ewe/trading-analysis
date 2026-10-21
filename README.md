# Trading Analysis Agent

An **analysis-only** assistant for a single crypto pair (ETH/USDT spot on Binance).
It fetches public market data, computes indicators, applies a deterministic rule
engine, and explains the reasoning in plain language through a web dashboard.

> **Level 0 — analysis only.** No orders are ever placed and no API keys are used.
> Not financial advice.

## Features

- Multi-timeframe chart (`1m`…`1w`) with synced oscillator panes.
- Overlays: EMA, Bollinger Bands, VWAP, support/resistance levels.
- Oscillators: RSI, MACD, Stochastic, ADX, OBV — each toggleable with tunable params.
- Deterministic rule engine: `LONG` / `SHORT` / `NEUTRAL-FLAT` bias, confidence,
  a scored confluence checklist, and a trade *proposal* (entry zone, stop, targets,
  R:R, invalidation).
- **Selection-driven scoring** — only the indicators you enable contribute to the score.
- Plain-language explanations ("Why this read?"), an indicator glossary, and
  market-context coaching.
- **Parameter review** — errors/warnings/tips for inconsistent or redundant settings,
  plus a "how to choose parameters" guide.

## Tech stack

Python 3.12 · FastAPI + Jinja2 + HTMX · pandas / NumPy · ccxt (Binance public) ·
lightweight-charts (vendored) · Docker.

## Quick start

### Docker (recommended)

```bash
APP_PORT=8000 docker compose up -d --build
```

Open <http://localhost:8000>. If port 8000 is taken, pick another:
`APP_PORT=8124 docker compose up -d`.

### Local (no Docker)

Dependencies live in `.vendor`; `dev.sh` puts it on `PYTHONPATH`:

```bash
./dev.sh python -m uvicorn web.api:app --host 127.0.0.1 --port 8000
```

## Configuration — `config.yaml`

- `universe.pair` (ETH/USDT) and `exchange` (Binance spot).
- `timeframes.available` plus primary / context / regime.
- `indicators`: `ema`, `rsi`, `macd`, `atr`, `bollinger`, `vwap`, `stoch`, `adx`,
  `obv`, `volume_ma`.
- `risk`: `max_risk_pct`, `min_rr`.

## How it decides

The engine scores a checklist of directional checks derived from the **enabled**
indicators (`regime`, `price vs EMA`, `price vs VWAP`, `Bollinger %B`, `RSI`,
`MACD`, `Stochastic`, `ADX/DI`, `OBV`). A signal requires a clear majority (≥60%)
of the enabled checks to agree **and** `|score| ≥ 2`; ≥80% agreement with
`|score| ≥ 3` is High confidence. A proposal is only emitted when it also clears
the minimum reward-to-risk. See `DESIGN.md` §10.

## Backtesting

Validate the signal on history with modeled costs and no look-ahead (signals on
closed bars, market fills at the next bar's open):

```bash
./dev.sh python -m src.backtest --timeframe 1h --days 365
./dev.sh python -m src.backtest --timeframe 4h --days 365 --target rr
./dev.sh python -m src.backtest --timeframe 1h --days 365 --entry limit --limit-bars 5
./dev.sh python -m src.walkforward --timeframe 4h --days 1095
```

Options: `--checks default|all|rsi,macd,...`, `--entry market|limit`,
`--limit-bars`, `--target proposal|rr`, `--regime-filter none|aligned|loose`,
`--stop-mult`, `--target-r`, `--no-mtf`, `--days`, `--equity`, `--fee`,
`--slippage`, `--no-cache`. Walk-forward adds `--train-days`, `--test-days`,
`--step-days`, `--min-train-trades`, and `--json`.

Each run writes JSON + Markdown + equity/trade CSVs to `results/` (gitignored)
and prints the summary. The first 365-day validation is recorded in `PLAN.md`
(Phase 2): MTF helped materially, but market entries after a pullback proposal
produced sub-2R fills; limit entries into the zone **hurt** via adverse
selection, and a hard 1d filter mostly reduced activity rather than improving
the edge. Widening the stop (1.5-2x) and targeting 3R removed most of the cost
drag and moved 4h positive in-sample, but the result is trade-concentrated.

Walk-forward over 3 years (4h, 180d train / 90d test) showed **unstable**
parameter selection (+4.5R OOS, PF 1.03): train-window R is a noisy selector,
and the fixed 1x/2R baseline was marginal (+0.045R/trade, PF 1.07). A 5-year
holdout changed the picture for the fixed **4h 2x/3R** config: +7.7R before the
tuning period and +10.5R during it (PF 1.13/1.21); over 5 years it made +17.3%
(CAGR 3.25%, Sharpe 0.38, max DD -12.1%) and survived doubled costs. The
original 1x/2R lost -17.3% over 5 years. The 2x/3R edge is fat-tailed and
concentrated, so it is a paper-trading candidate, not a real-capital strategy.

Cross-asset BTC over the same 5 years: 2x/3R +25.3% (Sharpe 0.56, DD -10.6%,
PF 1.22), with a strong pre-2024 holdout (+29.3R) but a negative recent period
(-4.7R); ETH was +10.5R in the same recent period. The edge is
regime-dependent, but 2x/3R is the only config positive on both assets.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard |
| GET | `/api/chart`, `/api/overlays` | Chart / overlay data |
| GET | `/api/analysis`, `/api/explain` | Analysis / explanations (JSON) |
| GET | `/analysis/view`, POST `/analysis/run` | Analysis panel (HTML) |
| GET | `/params/review` | Parameter check (HTML) |

## Project layout

```
src/     engine: config, exchange, data, indicators, analysis,
         explanations, params, pipeline, report, journal, backtest
web/     FastAPI app, Jinja templates, static assets (incl. vendored libs)
tests/   indicator / engine / parameter / backtest tests
```

## Docs

- `RULES.md` — strict operating constraints (Level 0).
- `DESIGN.md` — architecture and method.
- `PLAN.md` — roadmap.

## Tests

```bash
./dev.sh python tests/run.py
```

## Disclaimer

Educational tooling only. This is **not** financial advice and comes with no
guarantee of profit. Always do your own research.
