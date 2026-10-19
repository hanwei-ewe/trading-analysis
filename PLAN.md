# PLAN.md — Roadmap

_Version 2.1 — 2026-10-19._
_Companion to RULES.md (constraints) and DESIGN.md (architecture)._

## Phase 1 — Analysis + Foundations (done)

- Universe: `ETH/USDT` spot.
- Data: Binance public REST/WS. No API key.
- Level 0 autonomy (see RULES.md).
- Deliverable: reproducible ETH/USDT analysis reports (1h/4h/15m) viewable in a
  minimal web UI.

Milestones:
- [x] Scaffold project layout (see DESIGN.md §6).
- [x] `exchange.py` + `data.py`: fetch and cache ETH/USDT OHLCV (retry/backoff,
      rate-limit handling, closed-candle only).
- [x] `indicators.py`: EMA, RSI, MACD, ATR, Bollinger, VWAP.
- [x] `analysis.py`: implement the 6-dimension framework.
- [x] `report.py`: Markdown + JSON output.
- [x] First end-to-end ETH/USDT report.
- [x] Journal logging for reproducibility.
- [x] `web/api.py`: FastAPI + HTMX dashboard to review the latest analysis
      (read-only).
- [x] Dockerize the service (`Dockerfile` + `docker-compose.yml`).
- [x] Configurable timeframe set (`1m`…`1w`) selectable in the UI; analysis is
      computed per selected timeframe.
- [x] Chart overlays: EMA (tunable periods), Bollinger Bands (period/std),
      VWAP, with show/hide toggles and support/resistance price lines.
- [x] Oscillator panes: RSI, MACD, Stochastic, ADX, OBV as separate charts
      time-synced to the main chart (tunable params, individually toggleable).
- [x] Learning layer: rule-based explanations (`explanations.py`), "Why?" UI,
      confidence breakdown, and an indicator glossary (see DESIGN.md §13).
- [x] Selection-driven analysis: enabled indicators define the confluence checks
      and UI periods flow into the engine; panel and chart refresh live on any
      indicator change (see DESIGN.md §10).
- [x] Parameter review & guidance: deterministic error/warning/tip checks for
      inconsistent or inconsistent-with-each-other settings, plus a "how to
      choose" guide in the UI (see DESIGN.md §10).
- [x] Phase-1 polish: timeframe-aware proposal text; report `Inputs` section and
      `score of N`; journal records effective inputs (timeframe, active checks,
      parameters) for reproducibility; test runner + engine/parameter tests
      (`tests/run.py`).
- [x] Multi-timeframe confluence: `1d` regime and `4h`/`15m` context feeds scored
      higher-timeframe checks and caps confidence when counter-trend; shown in a
      "Multi-timeframe" block (see DESIGN.md §10).

## Phase 2 — Strategy Framework + Backtesting (current)

- Expand the price-overlay library via a registry (SMA/WMA/Keltner/Donchian/
  Ichimoku) without touching the chart core.
- `strategy/base.py`: pluggable `Strategy` interface (signals only).
- `risk.py`: sizing + RULES.md §5 limits, decoupled from strategies.
- [x] `data.load_history`: paged historical OHLCV + warmup for long windows.
- [x] `backtest.py`: event-driven engine, no look-ahead bias, modeled costs.
- [x] `metrics.py`: return, Sharpe/Sortino, max drawdown, win rate, profit
      factor, benchmark vs buy-and-hold ETH (currently inside `backtest.py`;
      extract when a second strategy exists).
- [x] `results/`: persist config, params, metrics, equity curves, trades.
- [ ] Web UI: Strategy editor + Backtests view (metrics, equity curve,
      comparison).
- [ ] Robustness: train/validation/out-of-sample + walk-forward.
- Deliverable: author a strategy, backtest it, review results in the UI — no
  live trading.

First validation (365 days ending 2026-10-19, default 5 checks + MTF, 1% risk,
0.10% fee + 0.05% slippage, market entry at next open):

| Frame | Return | Buy & hold | Sharpe | Max DD | Trades | Win | PF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1h, proposal T1 | -50.8% | -38.2% | -3.23 | -52.1% | 337 | 40.9% | 0.70 |
| 1h, 2R target | -40.0% | -38.2% | -2.17 | -42.5% | 281 | 33.8% | 0.77 |
| 4h, proposal T1 | -4.1% | -38.3% | -0.34 | -10.4% | 89 | 44.9% | 0.92 |
| 4h, 2R target | -6.8% | -38.3% | -0.58 | -13.4% | 74 | 35.1% | 0.86 |

Finding: MTF materially improved 1h (no-MTF was -87.3%), but the market entry
after a pullback proposal yields sub-2R fills and costs erase the remaining
edge. Next experiments: limit entries at the proposal zone, regime filters,
and 4h/1d walk-forward.

## Phase 3 — Paper Trading

- `execution/paper.py`: simulated fills on the live public feed.
- Run a backtested strategy in paper mode to validate live behavior.
- Runtime: first always-on deployment (supervision, WS reconnect, NTP).
- Still Level 0–0.5: no real orders, no API key.

## Phase 4 — Broader coverage

- Add more pairs (e.g. BTC/USDT).
- Optional private **read-only** API key for account-aware analysis.
- Requires: version bump of RULES.md scope.

## Phase 5 — Human-approved live

- `execution/live.py`: agent proposes orders; user approves each one.
- Requires: explicit RULES.md autonomy bump to Level ≥ 1.

## Phase 6 — Guarded automation

- Machine-executed trades within documented risk controls.
- Requires: explicit user opt-in, risk review, and RULES.md amendment.

## Phase 7 — News & AI context (optional)

- News ingestion pipeline (fetch → dedupe → relevance → sentiment/event tagging);
  deterministic first, optional single LLM summarization call.
- Optional LLM narrative layer, clearly labeled non-authoritative.
- Optional research **agent** (LLM + tools + loop) — an upgrade, not required for
  news. Gated by a RULES.md amendment; no execution.
- See DESIGN.md §14. The system must run fully without an LLM key by default.

## Cross-cutting — Runtime & Reliability

- Process supervision / auto-restart from Phase 3 onward.
- NTP clock sync before any always-on mode.
- Persistent storage for `journal/`, `results/`, and state.
- Structured logging + alerting for always-on modes.
- See DESIGN.md §5 for the full checklist and failure modes.
