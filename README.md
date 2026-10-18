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
         explanations, params, pipeline, report, journal
web/     FastAPI app, Jinja templates, static assets (incl. vendored libs)
tests/   indicator tests
```

## Docs

- `RULES.md` — strict operating constraints (Level 0).
- `DESIGN.md` — architecture and method.
- `PLAN.md` — roadmap.

## Tests

```bash
./dev.sh python tests/test_indicators.py
```

## Disclaimer

Educational tooling only. This is **not** financial advice and comes with no
guarantee of profit. Always do your own research.
