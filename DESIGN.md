# DESIGN.md — Trading Analysis Agent

_Architecture, method, and conventions. Version 2.9 — 2026-10-24._
_Companion to RULES.md (constraints) and PLAN.md (roadmap)._

## 1. Broker & Data Source

- **Primary exchange:** Binance.
- **Region:** Singapore — spot market data only; some derivatives are geo-restricted.
- **Market data:** Binance **public** REST + WebSocket. No API key required for analysis.
- **Private endpoints:** not used while at Level 0 (see RULES.md §2).
- **Abstraction:** all exchange access goes through one adapter module (CCXT-based)
  so the broker can be swapped without touching strategy/indicator code.
- **Local data cache:** OHLCV is persisted to `data/cache/{SYMBOL}_{tf}.csv` and
  refreshed **incrementally** (`since` = last cached candle + one step, with a
  bounded catch-up loop for long downtime). On restart the service re-reads the
  CSV and fetches only new candles — the full window is never re-downloaded. An
  in-memory TTL cache (~20s) sits on top for rapid UI actions. Cache files are
  host-mounted (`./data`), so they survive container restarts/rebuilds.

## 2. Tech Stack

- **Language:** Python 3.
- **Market data / exchange access:** CCXT (unified API).
- **Data handling:** pandas + numpy.
- **Indicators:** computed in-house or via `pandas-ta` (decide during setup).
- **Backtesting:** event-driven engine (in-house core) for parity with live; a
  vectorized lib (e.g. `vectorbt`) may be used for fast parameter screening.
- **Web UI:** FastAPI backend + HTMX (server-rendered, no build step). React can
  be layered in later for the live dashboard. Frontend libraries (htmx,
  lightweight-charts) are **vendored under `web/static/vendor/`** and served
  locally — no runtime CDN dependency — with a plain `fetch` fallback for the
  analysis panel if htmx ever fails to load.
- **Packaging/runtime:** Docker + Docker Compose (container is the canonical
  runtime); `python:3.12-slim` base image.
- **Config:** a single `config.yaml` holding pair, timeframes, indicator params,
  strategy params, and cost assumptions.
- **Output:** Markdown signal reports + JSON; backtest metric reports.

## 3. Architecture — One Pipeline, Three Modes

The same strategy code runs unchanged across backtest, paper, and live. Only the
**data feed** and **execution backend** differ.

```
        ┌────────────┐   ┌────────────┐   ┌────────────┐
Data ──▶│  Strategy  │──▶│    Risk    │──▶│ Execution  │
        │  (signal)  │   │ (size/lim) │   │ (backend)  │
        └────────────┘   └────────────┘   └────────────┘
              ▲                 ▲                ▲
        shared across all three modes ───────────┘
                                    ▲
                              Web UI (read-only review + control plane)

  Mode        Data feed            Execution backend
  ---------   ------------------   ---------------------
  Backtest    historical OHLCV     simulated fills
  Paper       live public feed     simulated fills
  Live        live public feed     real orders (Level ≥ 1)
```

Layering rules:
- Strategies emit **signals only**; they never place orders.
- **Risk** converts a signal + equity into an order intent (size, stops).
- **Execution** is the only component that talks to the broker/account.
- Analysis/reporting is read-only and side-effect free.

## 4. Web UI

Purpose: a human control plane to review analysis, manage strategies, and inspect
backtest results.

Stack: FastAPI (REST API + serves frontend). Frontend choice open (§15).

Views:
- **Dashboard** — ETH/USDT chart + latest analysis. A timeframe selector
  (`1m`…`1w`) drives both the chart and the analysis panel, so analysis is
  computed per selected timeframe.
- **Chart controls** — show/hide toggles and parameter inputs for overlays:
  EMA (three configurable periods, e.g. 20/50/200), Bollinger Bands
  (period, std-dev), and VWAP. Support/resistance are drawn as price lines from
  swing pivots. **Oscillators** (RSI, MACD, Stochastic, ADX, OBV) render as
  separate lightweight-charts below the main chart, time-synced via logical-range
  subscription so zoom/pan stays aligned. Overlays and oscillators are
  recomputed server-side on change. Indicators are registered plugins under
  `src/trading_analysis/indicators/`; each plugin declares its id, kind, output
  columns, warmup, and optional chart payload. New **oscillator panes** can be
  added without editing the analysis or oscillator chart builder. Price overlays
  share the same plugin contract; EMA/Bollinger/VWAP currently have dedicated
  chart builders because their UI controls differ.
- **Learn / "Why?"** — every signal and state carries a plain-language
  explanation: what the indicator means, the current reading, which way it voted
  and why, what would flip it, and a confidence breakdown (see §13).
- **Strategies** — list available strategies, edit params, enable/disable,
  see validation status.
- **Backtests** — trigger a run; view metrics table, equity curve, trade list;
  compare runs; benchmark vs buy-and-hold ETH.
- **Journal** — history of past analysis cycles and outcomes.
- **Settings** — pair, timeframes, costs (backed by `config.yaml`).

API endpoints (Phase 1):
- `GET /` — dashboard.
- `GET /api/timeframes` — supported timeframe codes.
- `GET /api/analysis?timeframe=` — analysis JSON for a timeframe.
- `GET /api/chart?timeframe=&limit=&ema=&bb_period=&bb_std=&show_bb=&show_vwap=&vwap_period=`
  — candles + overlay series + levels.
- `GET /api/overlays?<same params>` — overlay series only (no candles); used for
  show/hide and parameter changes so the chart view is never reset.
- `POST /analysis/run?timeframe=` — run + journal analysis, return summary partial.
- `GET /dca` — DCA ladder page.
- `GET /dca/run?<ladder params>` — DCA result partial (HTML).
- `GET /dca/report?<ladder params>` — downloadable Markdown report.
- `GET /api/dca?<ladder params>` — DCA result (JSON).

Performance:
- OHLCV is cached in memory per (symbol, timeframe) with a short TTL (~20s) and
  persisted to CSV; repeat requests are served from cache.
- Fetches are incremental (`since` = last cached candle), so refresh payloads stay
  small instead of re-downloading the full window.
- The initial chart is embedded in the page, avoiding a first round-trip; overlay
  changes call `/api/overlays` and preserve the visible price/time range.
- A **single reused CCXT client** is kept per market type — CCXT lazily loads all
  markets on first use (~1s), which was the main cause of slow timeframe switches.
- All configured timeframes are **warmed in a background thread at startup**, and a
  per-key lock prevents duplicate concurrent fetches.
- The analysis panel refreshes via non-journaling `GET /analysis/view` on timeframe
  change; explicit runs (`POST /analysis/run`) write to the journal.

Boundaries (aligned with RULES.md):
- Read-only at Level 0. The UI **may trigger compute jobs** (analysis, backtest)
  but has **no execution or account controls** until RULES.md is bumped.
- Never displays or stores API keys/secrets.
- Binds to `localhost` by default; requires auth before any network exposure.

## 5. Runtime & Reliability

**This is not a real-time system.** The trading horizon is hours–days, so the
latency budget is *seconds*, not microseconds. Prioritize reliability and
reproducibility over speed. No RTOS, no dedicated hardware.

Two runtime classes:

| Class | Used by | Need |
|-------|---------|------|
| Batch / offline | Analysis, Backtest | Run on demand or via cron; deterministic |
| Always-on | Paper, Live | Long-running process, auto-restart, persistent state |

Per-phase requirements:

| Phase | Host | Requirements |
|-------|------|--------------|
| 1 Analysis | any machine | retry/backoff, rate-limit handling, data cache |
| 2 Backtest | any machine | deterministic engine, recorded inputs |
| 3 Paper | always-on host | process supervision, WS reconnect, NTP clock sync |
| 6 Live auto | always-on host | idempotent orders (`clientOrderId`), state recovery, alerting |

Reliability checklist (whole system):
- Process supervision with auto-restart (`docker-compose` `restart: unless-stopped`
  or systemd).
- NTP time sync (candle boundaries and order timestamps depend on it).
- Retries with exponential backoff; respect Binance rate limits; cache data.
- Persistent storage for `journal/`, `results/`, and state (SQLite/parquet).
- Structured logging; alerting on errors/outages for always-on modes.

Failure modes to design for: missed/duplicate candles, clock drift, API outages
and rate limits, partial fills, duplicate orders, process crash mid-run.

Packaging & running (canonical: Docker):
- `docker compose up --build -d` → `http://localhost:${APP_PORT:-8000}`.
- Container listens on 8000; host port configurable via `APP_PORT`.
- `data/`, `journal/`, `results/` persist via host bind mounts; `config.yaml`
  is mounted read-only.
- Container runs as `${UID:-1000}:${GID:-1000}` so bind-mounted cache/journal
  files are owned by the host user (no root-owned files).
- Local fast path without Docker: `pip install --target .vendor -r requirements.txt`,
  then `./dev.sh python -m trading_analysis.app.pipeline` or `./dev.sh python -m uvicorn web.api:app`.

## 6. Project Layout

```
.
├── RULES.md                 # strict operating constraints
├── DESIGN.md                # this file
├── PLAN.md                  # roadmap
├── DCA_REPORT.md            # DCA study report
├── config.yaml              # pair, timeframes, indicators, risk, paths
├── pyproject.toml           # package metadata + CLI entry points
├── requirements.txt         # runtime dependencies for Docker
├── Dockerfile               # canonical runtime (python:3.12-slim)
├── docker-compose.yml       # web service, restart policy, volumes
├── dev.sh                   # local runner (adds src + .vendor to PYTHONPATH)
├── src/
│   └── trading_analysis/    # importable library
│       ├── config.py
│       ├── core/            # generic plugin registry + protocol
│       ├── indicators/      # one module per indicator/oscillator plugin
│       ├── data/            # exchange adapter, cache, timeframe helpers
│       ├── analysis/        # levels + confluence engine
│       │   └── checks/      # one module per confluence-check plugin
│       ├── strategies/
│       │   ├── base.py      # Strategy interface + registry
│       │   ├── builtin.py   # registered trend + DCA strategies
│       │   ├── backtest/    # checks, features, engine, metrics, runner, report, CLI
│       │   ├── dca/         # levels, engine, report
│       │   │   └── modes/   # registered level/target/reference/allocation/trend plugins
│       │   ├── walkforward.py
│       │   └── sweep.py
│       ├── analytics/       # shared metrics + curve blending
│       ├── reporting/       # Markdown, explanations, params, journal
│       └── app/             # UI-facing application service
├── web/
│   ├── api.py               # FastAPI composition root
│   ├── routes/              # analysis, chart, DCA routes
│   ├── query.py             # query-string parsing
│   ├── templates/           # Jinja templates
│   └── static/              # frontend assets (incl. vendored libs)
├── scripts/                 # reproducible research scripts
├── results/                 # backtest outputs, equity curves (gitignored)
├── journal/                 # decision log (gitignored)
└── tests/
```

### 6.1 Plugin Architecture

Shared extension points use `trading_analysis.core.Registry`. A plugin declares
a stable `id` and is registered with a decorator, so adding a feature does not
require editing a central `if/elif` chain.

- **Indicators/oscillators:** subclass `indicators.base.Indicator`, implement
  `compute(frame, params)`, and optionally `warmup(params)` and
  `chart(frame, params, limit)`. Register with `@INDICATORS.register`. The
  indicator automatically participates in `add_indicators`, warmup calculation,
  and oscillator chart payloads.
- **Confluence checks:** subclass `analysis.checks.base.Check`, implement
  `evaluate(ctx) -> CheckResult | None`, and register with `@CHECKS.register`.
  The check automatically appears in `ALL_CHECKS` and can be selected by id.
- **Strategies:** subclass `strategies.base.Strategy`, implement `run(frame,
  **params)`, and register with `@STRATEGIES.register`.
- **DCA modes:** subclass the relevant mode base (`LevelMode`, `TargetMode`,
  `ReferenceMode`, `AllocationMode`, `TrendFilter`) and register with its
  registry. The DCA loop resolves modes by id and never branches on mode names.

Keep each plugin in its own module and import it from the package `__init__` so
registration happens once at import time. A plugin should depend on the shared
context/contracts, not on another plugin's private internals.

## 7. Strategy Layer

- **Interface:** `strategies.base.Strategy` exposes `run(frame, **params)` and
  returns a result dictionary. Signal construction remains in `analysis/`; the
  strategy orchestrates data, checks, and its engine.
- **Pluggable:** strategies register in `STRATEGIES` and are selected by id.
- **Pure:** strategies are deterministic functions of their input data — no I/O,
  no state that can't be reconstructed from the data window.
- Strategies may compose shared indicator plugins but must not embed execution
  logic.

## 8. Backtesting Engine

Requirements:
- **No look-ahead bias:** act only on closed candles; execute at the next bar's
  open (or a specified slippage model).
- **Costs modeled:** taker/maker fees, slippage, and spread (configurable).
- **Same code path** as paper/live so results are representative.
- **Deterministic:** same inputs → same results.

Metrics reported (`metrics.py`):
- Total return, CAGR, Sharpe, Sortino
- Max drawdown + duration
- Win rate, profit factor, expectancy, average R/R
- Trade count, exposure, turnover
- Benchmark comparison: **buy-and-hold ETH**

Robustness protocol:
- Train / validation / out-of-sample splits.
- Walk-forward analysis (rolling re-fit) instead of one-shot optimization.
- Parameter-sensitivity checks; reject strategies that only work at one setting.

Implementation notes (first slice):
- `data.load_history()` pages Binance OHLCV into a dedicated `*_history.csv`
  cache and fetches extra warmup bars so EMA200/ADX are valid at the window
  start.
- `backtest.py` precomputes causal indicators and confirms swing pivots only
  `lookback` bars after they form; support/resistance never see the future.
  `analyze(..., at=i)` evaluates a single closed bar.
- Higher-timeframe checks are aligned with `merge_asof` on candle **close**
  times, so a primary bar only sees HTF bars that have already closed.
- Execution: signal on a closed bar → entry either at the next bar's open
  (`--entry market`) or via a limit at the proposal zone midpoint that stays
  valid for `--limit-bars` bars (`--entry limit`); structural stop from the
  proposal; target either the proposal T1 or `min_rr × risk` from the fill
  (`--target`); one position at a time; optional reverse on an opposite bias.
  On the entry bar of a limit fill, only the stop is evaluated (the target may
  have occurred before the intrabar fill).
- Optional hard regime gate (`--regime-filter aligned|loose`): `aligned` takes
  only signals matching the higher-timeframe regime bias, `loose` blocks only
  opposite signals; the filter uses the regime known at the signal bar, so it
  adds no look-ahead.
- Optional stop/target scaling: `--stop-mult` multiplies the structural stop
  distance from the fill (0.75 tighter, 2.0 wider) and `--target-r` fixes the
  target at an R-multiple of the adjusted risk, overriding `--target`. Both are
  applied at fill time from the signal and fill prices only.
- Walk-forward (`src/trading_analysis/strategies/walkforward.py`): rolls disjoint train/test windows,
  selects `(stop_mult, target_r)` on each train window by total R subject to a
  minimum trade count, then scores that combo on the next unseen window. Trades
  are assigned by entry time; the report also shows fixed 1x/2R and 2x/3R
  baselines over the same test windows.
- Sizing: `max_risk_pct` of current equity per trade, notional capped at equity.
- Costs: taker fee + slippage on both legs (configurable on the CLI).
- Outputs: `results/backtest_*` JSON + Markdown + equity/trade CSVs.
- CLI: `python -m trading_analysis.strategies.backtest --timeframe 1h --days 365`
  `[--checks default|all|ids] [--entry market|limit] [--limit-bars N]`
  `[--target proposal|rr] [--regime-filter none|aligned|loose]`
  `[--stop-mult X] [--target-r R] [--no-mtf]`.
- Walk-forward CLI: `python -m trading_analysis.strategies.walkforward --timeframe 4h --days 1095`
  `--train-days 180 --test-days 90 [--step-days N] [--min-train-trades N]`.

## 9. Execution Path (deferred)

Execution backends implement a common interface so strategies need no change:

1. **Backtest** — simulated fills on history (Phase 1+).
2. **Paper** — simulated fills on the live public feed.
3. **Live, human-approved** — agent proposes; user approves (requires RULES.md
   autonomy bump to Level ≥ 1).
4. **Live, guarded auto** — machine-executed within documented risk controls.

Each step is gated by an explicit amendment to RULES.md; none of 2–4 is enabled
by default.

## 10. Analysis Method

Run every dimension in order, then weigh confluence:

1. **Regime / Trend** — EMA stack (20/50/200), HH/HL vs LH/LL structure.
   Classify: trending-up / trending-down / ranging / transition.
2. **Momentum** — RSI(14), MACD(12,26,9), divergence checks.
3. **Volatility** — ATR(14), Bollinger Band width, range expansion.
4. **Key Levels** — swing highs/lows, S/R, round numbers, high-volume nodes.
5. **Volume / Flow** — volume vs 20-period average, spikes, VWAP.
6. **Confluence** — elevate a signal only when independent dimensions agree.

#### Selection-driven confluence

The confluence vote is computed only over the indicators the user has **enabled**
on the dashboard. Each enabled indicator contributes one scoring check; disabled
indicators are dropped from the score and the maximum score shrinks accordingly.
Directional checks are `regime`, `ema_position`, `vwap`, `bollinger`, `rsi`,
`macd`, `stoch`, `adx`, `obv`; `atr` is non-directional (risk sizing only). A
signal requires a clear majority (≥60%) of the enabled checks to agree **and**
`|score| ≥ 2`; ≥80% agreement with `|score| ≥ 3` is High confidence. With all five
original checks enabled this reduces exactly to the old `≥ 3 of 5` rule. An empty
selection yields `NEUTRAL-FLAT` with score `0 of 0`.

Method conventions:
- Prefer market structure and levels before indicators.
- Never use an indicator in isolation; always show the reasoning chain.
- If data is stale/missing/ambiguous, state it and lower confidence.

#### Parameter review & guidance

There is no single "correct" setting, but parameters can be internally
inconsistent or unexamined. `src/trading_analysis/reporting/params.py` (pure, deterministic) reviews the
current settings against the chart timeframe and available candle count and
returns findings in three levels — **never blocking** the user:

- **error** — an ordering that is almost certainly unintended: EMA periods not
  ascending, MACD fast ≥ slow, Stoch %D ≥ %K, non-positive std-dev, or too few
  candles for the chosen periods.
- **warning** — likely-unintended *relationships*: MACD slow ≥ the trend EMA it
  is meant to confirm (momentum that lags trend), MACD fast/slow duplicating the
  price EMA periods (redundant signals), an oscillator period as long as the long
  EMA, or an interestingly slow RSI/ADX.
- **tip** — a deviation from convention (e.g. RSI 14, MACD 12/26/9, BB 20/2σ),
  informational only.

The review drives a **"Parameter check"** card above the analysis, refreshed live
on any indicator change via `GET /params/review` (same query params as the chart),
and pairs a collapsed **"How to choose parameters"** guide explaining the
faster-vs-slower rule of thumb and how indicators complement each other. Errors
and warnings are advice, not restrictions — a knowledgeable user may proceed
regardless.

#### Multi-timeframe confluence

The selected timeframe is the **primary** frame. The `timeframes.regime` (`1d`) and
`timeframes.context` (`4h`, `15m`) frames are computed with the same rule engine
and the same enabled checks, then:

- every frame **higher** than the primary contributes a scored check
  (`Higher timeframe (<tf>) bias`, weight `+1`/`−1`/`0`) so confluence with the
  bigger trend strengthens the score and fighting it weakens it;
- an **opposing** higher frame **caps confidence at Medium** (a counter-trend
  setup can no longer read High), implemented as a post-score cap in the engine;
- all frames are shown in a **"Multi-timeframe"** block with agreement labels
  (aligned / mixed / counter) against the primary bias.

If no checks are enabled the MTF layer is skipped, and any frame that cannot be
loaded is ignored rather than failing the request.

### Default indicator parameters

| Indicator | Params |
|-----------|--------|
| EMA | 20, 50, 200 |
| RSI | 14 |
| MACD | 12, 26, 9 |
| ATR | 14 |
| Bollinger Bands | 20, 2σ |
| VWAP | 20 |
| Stochastic | 14, 3, 3 |
| ADX | 14 |
| OBV | 10 |
| Volume MA | 20 |

## 11. Signal Report Template

```
## ETH/USDT — <timeframe> — <timestamp>
Bias: LONG | SHORT | NEUTRAL-FLAT
Entry zone: <low> – <high>
Stop loss: <price>  (why: ...)
Targets: T1 <price> (why: ...) | T2 <price> (why: ...)
R/R: <ratio>
Confidence: Low | Medium | High  (because: ...)
Invalidation: <what proves this wrong>
Data as of: <data timestamp>
Assumptions/uncertainties: ...
```

## 12. Logging & Reproducibility

- Each analysis cycle writes to `journal/` recording: timestamp, data window,
  indicator params, market snapshot, signal, rationale, and later outcome.
- Each backtest writes to `results/` recording: config, params, costs, metrics,
  and equity curve.
- Every analysis and backtest must be reproducible from recorded inputs.

## 13. Learning & Explanations (Level 0)

Purpose: the tool must **teach while it analyzes**. A non-expert should be able to
see *why* a read is bullish/bearish, *why* the risk is what it is, and *why* the
confidence is high/medium/low — without leaving the dashboard.

This layer is **deterministic and rule-based — no LLM.** The analyzer is already a
set of explicit rules (`analysis.py`), so the "why" can be reconstructed exactly
from the same inputs. Deterministic text is preferred here because (a) an
explanation that contradicts the engine erodes trust, and (b) it is free,
reproducible, and cannot hallucinate.

`src/trading_analysis/reporting/explanations.py` (pure functions, no I/O) turns each rule's inputs into
structured explanation records:

- `indicator` — name + one-line plain-language meaning (from a glossary).
- `reading` — the current value(s) and what they indicate.
- `vote` — `bullish` / `bearish` / `neutral`, plus the exact rule/threshold that
  produced it (e.g. `RSI 62 ≥ 55 → bullish`).
- `weight` — the contribution to the confluence score.
- `flip` — what reading would change this vote (the invalidation/trigger).

Scope:
- Cover all six dimensions (regime, momentum, volatility, levels, volume,
  confluence) and every scoring check.
- **Confidence breakdown** = the contributing checks, how many agreed, and the
  thresholds (majority: `agreement ≥ 60%` and `|score| ≥ 2` → signal; `≥ 80%` and
  `|score| ≥ 3` → High). "Why confident" is literally the agreement count over the
  enabled checks.
- **Risk explanation** = how the stop is derived (ATR multiple + nearest swing
  support/resistance), the R/R math, and the `invalidation` sentence.
- **Glossary** — one entry per implemented indicator (EMA, Bollinger Bands, VWAP,
  ATR, RSI, MACD, Stochastic, ADX, OBV): plain meaning, how it is used here, and
  common pitfalls.
- **Context-aware coaching** — classify trend strength (ADX/DI) and volatility
  (ATR/BB), then explain which toolset is most informative *right now* (trend
  tools in a trend, mean-reversion oscillators in a range), rank the enabled
  indicators by relevance with a reason, and **compare** them: where they agree
  (confluence) vs conflict, and how their roles complement each other (trend =
  direction, momentum = timing, volatility = risk sizing, volume = confirmation).
  The selected oscillators are passed in so the comparison reflects what the user
  has enabled.

UI: a "Market context" summary (trend strength + volatility + which tools to
trust), a "Which indicators matter right now" ranking (relevance + reason), a
"How they compare" agreement/conflict block, then a "Why this read?" block with
an expandable row per check (vote badge, reading, meaning, why, rule, what would
flip it), the confidence breakdown, the risk/invalidation narrative, and a
collapsible **indicator glossary**. The "Why this read?" rows are exactly the
enabled indicators, and the score/bias recompute live as toggles or periods
change (the dashboard sends the enabled set as `checks` plus every period as query
params; the panel and chart both refresh on any indicator change). A
`GET /api/explain?timeframe=&osc=` endpoint returns the structured records
(reusing the same cached data as `/api/analysis`); the Markdown report includes a
"Why this read" section for the journal.

Guardrails: explanations **describe the computed rules** and must never introduce
claims the rule engine did not produce, nor be phrased as advice. Same inputs →
same text.

## 14. News, AI & Agent (future, optional)

Three distinct capabilities — deliberately not conflated:

1. **News ingestion (pipeline — no agent).**
   Sources: exchange announcements, reputable crypto RSS, macro/economic calendar.
   Steps: fetch → dedupe → relevance filter (ETH/USDT + macro) → event/sentiment
   tagging (keyword/entity rules first) → store with timestamp. Deterministic
   scoring by default; a **single** optional LLM summarization call produces a
   readable digest. Output is an additional, clearly-separated "context" block and
   does **not** override the rule engine.

2. **LLM narrative (optional).** One-shot call turning computed metrics +
   headlines into a plain-language summary, labeled non-authoritative. No tools,
   no loop.

3. **Agent (later).** LLM + tools + loop for autonomous multi-step research:
   choose sources, cross-check claims, blend news + on-chain + calendar, and
   maintain a thesis over time. This is an **upgrade**, not a prerequisite —
   **news analysis does not require an agent.**

Guardrails:
- The rule engine remains the source of truth; AI/news are supplementary context,
  never advice (RULES.md Level 0).
- Fetched content is untrusted input: sanitize and treat as data, not
  instructions (prompt-injection defense).
- LLM use needs a secret API key; the system must run fully **without** it by
  default. All external fetches and prompts are logged for reproducibility.
- The agent is gated like an execution backend: no autonomy/execution without a
  RULES.md amendment.

Sequencing: deterministic explanations (§13) → news ingestion → optional LLM
narrative → optional agent.

## 15. Open Decisions

- Indicator library: in-house vs `pandas-ta`.
- Backtest engine: fully in-house vs in-house core + vectorbt screening.
- **Web UI frontend:** decided — FastAPI + HTMX for Phase 1; React optional later
  if the live dashboard needs richer interactivity.
- Data caching strategy (in-memory vs parquet).
- Report delivery (console vs file vs web UI).
- Fill/slippage model defaults.
- Hosting target for always-on phases (local Docker vs VPS).


## 16. DCA Ladder (research)

A separate research view, not part of the live signal path.

- **Engine:** `src/trading_analysis/strategies/dca/` simulates a spot-only ladder. Each level is a
  fraction below a reference; capital is allocated across levels; each lot has
  its own profit target; profitable exits may reserve or reinvest.
- **Levels:** fixed gaps, Fibonacci retracements, trend-leg Fibonacci
  (`trend_fib`, recent swing high/low), geometric gaps, or ATR multiples.
- **References:** static anchor (start-of-window high), rolling prior high, or
  all-time high. Rolling uses `high.shift(1).rolling(lookback).max()` to avoid
  same-bar look-ahead.
- **Targets:** fixed percent, retrace of the reference, or ATR multiple.
- **Filter:** optional EMA200; entries only when price is above it.
- **Modes:** level, target, reference, allocation, and trend-filter modes are
  registered plugins under `strategies/dca/modes/`. Each declares a stable `id`
  and implements a small strategy method; new modes do not edit the DCA loop.
- **Allocations:** equal, front/back-loaded, deep/very-deep, Fibonacci,
  inverse, martingale/anti-martingale, or custom normalized weights.
- **Accounting:** fees 0.10% + slippage 0.05% on entries/exits; unspent cash is
  idle; reserve is tracked separately; open lots are marked to market; no
  leverage, shorts, or deposits.
- **Blending:** `src/trading_analysis/analytics/portfolio.py` aligns DCA `total_wealth` and trend `equity`
  curves on their inner join, normalizes weights, and computes CAGR/Sharpe/DD/
  Calmar. Trend risk is grossed up by `1/(1-w_dca)` before weighting so the
  combined initial capital stays $1,000.
- **UI:** `/dca` renders controls, metrics, ladder/rules, recent exits, and an
  equity chart; `/dca/report` returns Markdown; `/api/dca` returns JSON.
- **Guardrail:** DCA is an accumulation/regime tool. It does not replace the
  trend signal; the default research blend is 50% `fib_deep_percent15` + 50%
  trend, which improves ETH risk-adjusted return but is not BTC-positive.
- **Frequency/S-R:** 15m was tested and rejected (ETH trend -70.22%, BTC
  -83.25% with costs). Swing-pivot S/R anchors stops; PA/Donchian/extension
  were swept but did not survive the test window. Indicator-derived S/R is not
  a validated DCA level source.
