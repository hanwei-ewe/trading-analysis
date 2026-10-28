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
- **DCA ladder research** — spot-only capital ladder with fixed/Fibonacci/
  trend-Fibonacci/geometric/ATR drop levels, allocation presets,
  anchor/rolling/ATH references, adaptive targets, EMA200 filter, profit
  reserve/reinvestment, and a downloadable report.

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

Dependencies live in `.vendor`; `dev.sh` adds `.vendor` and `src` to
`PYTHONPATH`:

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
./dev.sh python -m trading_analysis.strategies.backtest --timeframe 1h --days 365
./dev.sh python -m trading_analysis.strategies.backtest --timeframe 4h --days 365 --target rr
./dev.sh python -m trading_analysis.strategies.backtest --timeframe 1h --days 365 --entry limit --limit-bars 5
./dev.sh python -m trading_analysis.strategies.walkforward --timeframe 4h --days 1095
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

### DCA ladder

The separate `/dca` page backtests a spot-only capital ladder and can download a
Markdown/JSON report. The default is Fibonacci levels, deep allocation, anchor
reference, EMA200 filter, 15% target, and 50% profit reinvestment.

Canonical 5-year ETH results (pre-window anchor, 0.10% fee + 0.05% slippage):

| Strategy | Return | Max DD | Calmar |
| --- | ---: | ---: | ---: |
| Trend `rsi21` | +49.99% | -8.44% | 1.00 |
| DCA `fib_deep_percent15` | +61.72% | -18.56% | 0.54 |
| DCA `fib_deep_retrace50` | +90.93% | -29.29% | 0.47 |
| 50/50 blend `fib_deep_percent15` + trend | +89.35% | -11.36% | 1.20 |

DCA wins raw return on ETH but loses risk-adjusted to the trend strategy. A 50%
blend improves ETH Calmar (1.20 vs 1.00) and the 2024-2026 test (+25.58% vs
+22.67%), but hurts BTC, where DCA made 0% in the test. With a realistic
pre-window anchor, DCA is an accumulation/regime tool, not a standalone
replacement. See `/dca` for the interactive report.

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
| GET | `/dca` | DCA ladder page |
| GET | `/dca/run` | DCA result partial (HTML) |
| GET | `/dca/report` | Downloadable DCA report (Markdown) |
| GET | `/api/dca` | DCA result (JSON) |

## Project layout

The importable library lives under `src/trading_analysis/`; the web app is a
separate presentation package under `web/`.

```
src/trading_analysis/
  config.py              configuration + project paths
  core/                  generic plugin registry + protocol
  indicators/            one module per indicator/oscillator plugin
  data/                  exchange adapter, OHLCV cache, timeframe helpers
  analysis/              level detection + confluence engine
    checks/              one module per confluence-check plugin
  strategies/
    base.py              Strategy interface + registry
    builtin.py           registered trend + DCA strategies
    backtest/            checks, features, engine, metrics, runner, report, CLI
    dca/                 DCA levels, engine, report
      modes/             registered level/target/reference/allocation/trend plugins
    walkforward.py       walk-forward validation
    sweep.py             parallel parameter sweeps
  analytics/             shared performance metrics + curve blending
  reporting/             analysis/DCA Markdown, explanations, params, journal
  app/                   UI-facing application service (pipeline)
web/
  api.py                 FastAPI composition root
  routes/                analysis, chart, and DCA routes
  query.py               query-string parsing
  templates/             Jinja templates
  static/                frontend assets (incl. vendored libs)
scripts/                 reproducible research scripts
tests/                   indicator / engine / strategy / DCA / metrics tests
```

## Extension points

Indicators, oscillators, confluence checks, strategies, and DCA modes are
plugins. Each declares a stable `id`, lives in its own module, and registers
itself at import time through `trading_analysis.core.Registry`. Adding an
indicator does not require editing `add_indicators`, warmup calculation, or the
oscillator chart builder. DCA level/target/reference/allocation/trend modes are
registered under `strategies/dca/modes/`.

See `DESIGN.md` §6.1 for the contracts and registration pattern.

## Docs

- `RULES.md` — strict operating constraints (Level 0).
- `DESIGN.md` — architecture and method.
- `PLAN.md` — roadmap.
- `DCA_REPORT.md` — DCA ladder study results and caveats.

## Tests

```bash
./dev.sh python tests/run.py
```

## Disclaimer

Educational tooling only. This is **not** financial advice and comes with no
guarantee of profit. Always do your own research.
