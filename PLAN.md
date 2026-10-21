# PLAN.md — Roadmap

_Version 2.7 — 2026-10-19._
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

First validation (365 days ending 2026-10-20, default 5 checks, 1% risk,
0.10% fee + 0.05% slippage). Buy & hold over the window: **-38.5%**.

| Experiment | Return | Sharpe | Max DD | Trades | Win | PF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1h, market, T1 | -49.1% | -3.08 | -52.2% | 330 | 41.2% | 0.71 |
| 1h, market, 2R | -36.7% | -1.95 | -42.6% | 277 | 34.3% | 0.80 |
| 1h, limit 5, T1 | -51.9% | -3.18 | -53.6% | 295 | 33.6% | 0.68 |
| 1h, market, T1, 1d aligned | -40.2% | -2.80 | -43.7% | 225 | 40.0% | 0.68 |
| 1h, limit 5, T1, 1d aligned | -42.3% | -2.82 | -44.9% | 198 | 32.3% | 0.65 |
| 4h, market, T1 | -3.6% | -0.30 | -10.8% | 85 | 44.7% | 0.93 |
| 4h, market, 2R | -2.6% | -0.19 | -12.5% | 65 | 35.4% | 0.94 |
| 4h, market, T1, 1d aligned | -6.6% | -0.65 | -11.8% | 69 | 42.0% | 0.84 |
| 4h, limit 5, T1, 1d aligned | -8.3% | -0.77 | -15.5% | 62 | 32.3% | 0.80 |

Findings:
- MTF materially improved 1h (no-MTF: -86.3%, 775 trades) and cut 4h churn
  (152 → 85 trades).
- Market entries after a pullback proposal produce sub-2R fills; a 2R-from-fill
  target is the most consistent improvement, but does not create an edge.
- Limit entries at the zone midpoint **hurt**: fills only happen when the
  pullback continues against the signal (adverse selection), so win rate fell
  from ~41-45% to ~32-35%.
- A hard 1d `aligned` filter cut the 1h loss (-49.1% → -40.2%) mostly by trading
  less (330 → 225 trades); profit factor fell (0.71 → 0.68). On 4h it made
  things worse (-3.6% → -6.6%). `loose` was neutral on 4h.
- 4h market + 2R was the closest to breakeven in the first pass (-2.6%,
  PF 0.94) but still not a positive expectancy after costs. Next: cost-aware
  stop/target widths (below), then walk-forward validation.

### Cost-aware stops and targets

Costs are a fixed percent of price, so widening the stop reduces the notional
needed for the same 1% risk and shrinks costs as a fraction of R. Combining a
stop multiplier with a fixed R-multiple target (365d, market entry, MTF):

| Frame | Stop | Target | Return | PF | Trades |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1h | 1.0x | 2R | -36.7% | 0.80 | 277 |
| 1h | 1.5x | 3R | -1.9% | 0.98 | 115 |
| 1h | 2.0x | 3R | +0.3% | 1.00 | 96 |
| 4h | 1.0x | 2R | -2.6% | 0.94 | 65 |
| 4h | 1.0x | 3R | +2.1% | 1.07 | 50 |
| 4h | 1.5x | 3R | +9.9% | 1.60 | 35 |
| 4h | 2.0x | 3R | +12.5% | 2.16 | 30 |

Robustness checks:
- 730d: 4h 2x/3R +7.6% (PF 1.17; halves +0.9% / +6.6%); 4h 1x/3R +5.5%
  (PF 1.04; halves -1.4% / +6.9%); 1h 2x/3R +10.7% (PF 1.06; halves
  +10.8% / 0.0%).
- Concentration: the top 3 trades are 75% of the 4h 2x/3R net over 365d.
- Costs (365d): 4h 2x/3R +14.0% gross → +12.5% base → +11.3% at 2x costs;
  4h 1x/3R +7.0% → +2.1% → -1.8%; 1h 2x/3R +21.8% → +0.3% → -9.9%.

Wider stops plus a 3R target is the first configuration to move 4h clearly
positive (≈+10% to +12.5%), and 4h is the only frame that survives doubled
costs. The edge is still thin and trade-concentrated (and 1h remains
cost-sensitive), so it is a candidate for walk-forward, not a validated edge.

### Walk-forward

Parameter-selection walk-forward on 4h over 1095 days: train 180d, test 90d,
step 90d; grid of 3 stop multipliers × 3 R targets; select the best train
total R with at least 5 train trades, then score that combo on the next unseen
90d. Test windows are disjoint; trades are assigned by entry time.

| Test window | 1x/2R R (n) | 2x/3R R (n) |
| --- | ---: | ---: |
| 2024-04-18 → 2024-07-17 | -6.5 (25) | -2.4 (11) |
| 2024-07-17 → 2024-10-15 | +2.4 (34) | +0.8 (11) |
| 2024-10-15 → 2025-01-13 | +5.2 (40) | +0.4 (12) |
| 2025-01-13 → 2025-04-13 | -2.5 (34) | -0.9 (14) |
| 2025-04-13 → 2025-07-12 | +6.1 (37) | +4.0 (16) |
| 2025-07-12 → 2025-10-10 | +4.1 (21) | +0.8 (10) |
| 2025-10-10 → 2026-01-08 | +1.4 (27) | +1.5 (12) |
| 2026-01-08 → 2026-04-08 | +4.1 (33) | +1.0 (12) |
| 2026-04-08 → 2026-07-07 | +5.5 (33) | +3.1 (6) |
| 2026-07-07 → 2026-10-05 | -6.0 (25) | +3.1 (8) |

- Selected OOS: 221 trades, +4.5R, +0.021R/trade, PF 1.03. Selection swung
  between 1.0x/2R (×4), 1.5x/3R (×3), 1.0x/3R, 1.5x/1.5R, 2.0x/2R.
- Fixed 1.0x/2R: 309 trades, +13.8R, +0.045R/trade, PF 1.07.
- Fixed 2.0x/3R: 112 trades, +11.5R, +0.102R/trade, PF 1.19.
- Split at 2025-10: 2.0x/3R +1.9R over 64 trades before, +8.7R over 38 after;
  1.0x/2R +4.7R over 170 before, +5.0R over 118 after.

Selection by train total R has no edge: it is unstable and underperforms both
fixed configs. The fixed 2x/3R config is the exception (next section).

### Long-history holdout

Fixed configs over 1825 days (2021-10-21 → 2026-10-20), split by year. The
period before 2024-10 was never used during tuning, so it is a true holdout.
Columns are total R, trades, and profit factor.

| Year | Buy & hold | 1x/2R | 2x/3R |
| --- | ---: | ---: | ---: |
| 2021 (partial) | -9.3% | +0.5 (17, 1.05) | -1.8 (9, 0.62) |
| 2022 | -67.9% | -4.1 (67, 0.90) | +2.9 (34, 1.22) |
| 2023 | +91.1% | -20.9 (123, 0.78) | 0.0 (38, 1.00) |
| 2024 | +46.8% | +2.9 (153, 1.03) | +8.0 (50, 1.31) |
| 2025 | -11.4% | +7.0 (132, 1.08) | +2.1 (49, 1.07) |
| 2026 (partial) | -17.8% | +2.1 (111, 1.03) | +7.0 (31, 1.44) |

- 2x/3R holdout: +7.7R over 121 trades, +0.064R/trade, PF 1.13.
- 2x/3R tuning era: +10.5R over 90 trades, +0.116R/trade, PF 1.21.
- 1x/2R holdout: -23.7R over 323 trades, PF 0.90; tuning era +11.1R, PF 1.06.
- 5y: 2x/3R +17.3% (CAGR 3.25%, Sharpe 0.38, max DD -12.1%, PF 1.15);
  1x/2R -17.3% (max DD -33.0%, PF 0.95); buy & hold -39.6%.
- Costs (5y, 2x/3R): +31.5% gross → +17.3% base → +6.5% at 2x costs.
- Concentration (2x/3R): the top 3 trades are 59% of the 5y net and roughly
  9.4R of the +7.7R holdout, so without them the holdout is about -1.7R.

The fixed 2x/3R config is the first to show positive expectancy in both the
true holdout and the tuning era, and it survives doubled costs. But the edge is
fat-tailed (three trades carry each period), Sharpe is low, and train-window
selection remains unusable. It is a paper-trading candidate, not a
real-capital strategy.

### Cross-asset holdout (BTC)

The same fixed configs on BTC/USDT over the same 5-year span, with no
BTC-specific tuning. Columns are total R, trades, and profit factor.

| Year | Buy & hold | 1x/2R | 2x/3R |
| --- | ---: | ---: | ---: |
| 2021 (partial) | -25.7% | -0.7 (11, 0.89) | +1.0 (6, 1.40) |
| 2022 | -64.7% | -4.7 (62, 0.88) | -0.8 (37, 0.95) |
| 2023 | +155.8% | +16.3 (95, 1.28) | +13.6 (36, 1.84) |
| 2024 | +121.1% | +8.5 (119, 1.11) | +12.3 (40, 1.68) |
| 2025 | -6.6% | +6.9 (91, 1.12) | -3.5 (47, 0.86) |
| 2026 (partial) | -5.5% | -14.4 (105, 0.82) | +1.9 (33, 1.10) |

- 2x/3R 5y: +25.3% (CAGR 4.62%, Sharpe 0.56, max DD -10.6%, PF 1.22,
  199 trades) vs BTC buy & hold +33.5% with much larger drawdown.
- 2x/3R holdout: +29.3R over 111 trades, +0.264R/trade, PF 1.64; tuning era
  -4.7R over 88 trades, PF 0.90.
- 1x/2R 5y: +6.6%, PF 1.02; holdout +20.0R, tuning era -8.2R.
- Costs (5y, 2x/3R): +49.6% gross → +25.3% base → +13.0% at 2x costs.
- Concentration: top 3 trades are 45% of the 5y net (below ETH's 59%).
- Combined ETH+BTC at 1% risk each: +37.0R in the holdout, +5.8R in the tuning
  era; 2025 -1.4R, 2026 +8.9R.

The 2x/3R config is positive over 5 years on both assets and survives doubled
costs, and its BTC holdout is stronger than ETH's. But recent periods diverge
(ETH +10.5R, BTC -4.7R), so the edge is regime-dependent. The 1x/2R config
fails on at least one asset in each period. 2x/3R is the only config worth
paper trading.

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
