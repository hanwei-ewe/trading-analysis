# DCA Ladder Study — 2026-10-24

Status: completed research run. Analysis-only; no orders, no leverage, no shorts.

## Executive summary

- The 4h trend strategy (`rsi21`, 2x stop, 4R target, MTF, long-only) remains the
  cross-market core: ETH 5y **+49.99% / DD -8.44% / Calmar 1.00**; BTC 5y
  **+46.05% / DD -8.45% / Calmar 0.93**.
- Fibonacci DCA with an EMA200 filter and adaptive targets can beat trend on raw
  ETH return, but not on risk-adjusted return. `fib_deep_percent15` made
  **+61.72% / DD -18.56% / Calmar 0.54** over 5y.
- A 50/50 blend of `fib_deep_percent15` and trend is the best ETH compromise:
  **+89.35% / DD -11.36% / Calmar 1.20** over 5y and **+25.58% / DD -6.63% /
  Calmar 1.82** in the 2024-2026 test.
- The same blend is worse on BTC, and DCA made **0.0%** in the BTC test. Do not
  use the DCA blend as a BTC replacement.
- DCA is an accumulation/regime tool. In the 2024-2026 bull test, deep levels
  rarely filled, so DCA mostly sat in cash.
- 15m was tested and rejected. The same trend logic lost **-70.22%** on ETH and
  **-83.25%** on BTC over two years with costs; DCA did not rescue it.
- Support/resistance checks exist (`pa`, `breakout`, `extension`, swing pivots),
  but adding them to the final trend filter did not improve out-of-sample
  robustness. DCA does not yet use indicator-derived S/R as a level source.

## Test run

Commands executed for this report:

```bash
./dev.sh python tests/run.py
./dev.sh python scripts/dca_study.py
./dev.sh python scripts/frequency_study.py
```

Results:

- Test suite: **74/74 passed**.
- Canonical blend study: rewrote `results/study_blend_dca_trend.csv` in
  **314.6s**.
- 15m frequency study: wrote `results/study_15m_sr.csv` for ETH and BTC over
  two years, including 0.10% fee + 0.05% slippage.
- HTTP smoke test: `/dca`, `/dca/run`, `/api/dca`, and `/dca/report` all
  returned HTTP 200.

## Method

- Windows:
  - 5y: `2021-10-21` → `2026-10-20`.
  - Test: `2024-10-20` → `2026-10-20`.
- ETH/USDT is primary; BTC/USDT is the cross-check.
- Costs: 0.10% fee + 0.05% slippage on entries and exits.
- Initial capital: $1,000.
- Trend: 4h, checks `regime,rsi,vwap,bollinger,adx,obv`, RSI 21, 2x ATR stop,
  4R target, MTF on, long-only, 1% risk per trade.
- DCA: Fibonacci levels `0.236, 0.382, 0.5, 0.618, 0.786`; deep allocation
  `5%, 10%, 15%, 25%, 45%`; anchor reference; EMA200 filter; 15% target or 50%
  retrace target; 50% profit reinvestment.
- DCA reference uses a **30-day pre-window anchor**, so the test does not build
  its anchor from test-window highs. This is why test DCA returns are small.
- Blend: trend risk is grossed up by `1/(1-w_dca)` before weighting so the
  combined initial capital stays $1,000. No rebalancing.

## Results

### ETH 5y

| Strategy | Return | Max DD | Calmar |
| --- | ---: | ---: | ---: |
| Trend `rsi21` | +49.99% | -8.44% | 1.00 |
| DCA `fib_deep_percent15` | +61.72% | -18.56% | 0.54 |
| DCA `fib_deep_retrace50` | +90.93% | -29.29% | 0.47 |
| DCA `fib_fib_retrace50` | +118.52% | -33.97% | 0.50 |
| DCA `fib_equal_retrace50` | +131.36% | -36.20% | 0.50 |
| DCA `fixed_deep_percent15` | +188.23% | -36.32% | 0.65 |

### ETH test (2024-2026)

| Strategy | Return | Max DD | Calmar |
| --- | ---: | ---: | ---: |
| Trend `rsi21` | +22.67% | -6.44% | 1.67 |
| DCA `fib_deep_percent15` | +3.72% | -0.87% | 2.12 |
| DCA `fib_deep_retrace50` | +3.55% | -0.87% | 2.02 |
| DCA `fib_fib_retrace50` | +6.67% | -1.61% | 2.04 |
| DCA `fib_equal_retrace50` | +14.44% | -3.35% | 2.08 |
| DCA `fixed_deep_percent15` | +13.45% | -5.88% | 1.11 |

### BTC cross-check

| Strategy | 5y return | 5y DD | 5y Calmar | Test return | Test DD | Test Calmar |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Trend `rsi21` | +46.05% | -8.45% | 0.93 | +10.54% | -7.84% | 0.66 |
| DCA `fib_deep_percent15` | +19.48% | -20.09% | 0.18 | 0.00% | 0.00% | 0.00 |
| DCA `fib_deep_retrace50` | +41.03% | -21.57% | 0.33 | 0.00% | 0.00% | 0.00 |
| DCA `fixed_deep_percent15` | +55.22% | -35.47% | 0.26 | 0.00% | 0.00% | 0.00 |

### Blend sensitivity

`fib_deep_percent15` + trend:

| Asset | Window | 25% DCA | 50% DCA | 75% DCA |
| --- | --- | ---: | ---: | ---: |
| ETH | 5y | +68.20% / -9.88% / 1.11 | +89.35% / -11.36% / 1.20 | +116.94% / -14.51% / 1.16 |
| ETH | test | +24.05% / -6.51% / 1.75 | +25.58% / -6.63% / 1.82 | +24.40% / -6.92% / 1.67 |
| BTC | 5y | +53.26% / -11.56% / 0.77 | +58.63% / -15.23% / 0.64 | +54.67% / -21.18% / 0.43 |
| BTC | test | +10.46% / -7.99% / 0.64 | +9.55% / -8.21% / 0.57 | +4.27% / -7.33% / 0.29 |

Values are return / max drawdown / Calmar.

### 15m frequency test (2024-10-24 → 2026-10-20)

Same trend checks (`regime,rsi,vwap,bollinger,adx,obv`, RSI 21, MTF on,
long-only, 1% risk) and DCA variants on 15m bars, with costs.

| Asset | Strategy | Return | Max DD | Trades |
| --- | --- | ---: | ---: | ---: |
| ETH | Trend 2x/4R | -70.22% | -71.87% | 688 |
| ETH | Trend 1.5x/3R | -85.37% | -87.02% | 920 |
| BTC | Trend 2x/4R | -83.25% | -84.55% | 662 |
| BTC | Trend 1.5x/3R | -91.68% | -92.19% | 912 |

DCA on 15m with a 1-day rolling reference: `fixed` and `fib` produced **zero
buys** because 23.6-78.6% below a 1-day high almost never filled. `trend_fib`
(dynamic swing-leg levels) did trade, but results were weak:

| Asset | 1% target | 2% target | 5% target |
| --- | ---: | ---: | ---: |
| ETH | -23.02% / -58.79% DD | -10.36% / -56.75% DD | +0.71% / -55.18% DD |
| BTC | +0.51% / -45.46% DD | +15.68% / -43.39% DD | +17.96% / -43.80% DD |

Values are return / max drawdown. The 15m DCA rows use 96-bar swing lookback,
96-bar rolling reference, EMA200 filter, and 50% reinvestment. They are not
competitive with the 4h core.

### Support/resistance and oscillator checks

- Swing-pivot support/resistance is implemented in `src/trading_analysis/analysis/`; the
  nearest support below price and resistance above price anchor entry proposals
  and stops.
- `pa` (engulfing/pin bar), `breakout` (Donchian 20), and `extension` (distance
  from EMA in ATR) are implemented and were included in subset sweeps.
- `bollinger` and `vwap` already act as dynamic support/resistance proxies in
  the final trend filter.
- The final `rsi21` set is `regime,rsi,vwap,bollinger,adx,obv`; it does not use
  `pa`, `breakout`, or `extension`.
- In `results/study_subset_test_all.csv`, the selected six-check set made
  **20.69R train / 17.37R test**. A PA-heavy set
  (`ema_position,macd,bollinger,stoch,adx,pa`) made **22.24R train / 5.24R
  test** — better in-sample, much worse out-of-sample.
- DCA currently uses price anchors, Fibonacci, geometric, ATR, and the new
  `trend_fib` swing-leg mode; it does not use indicator-derived S/R levels.
  The 15m test is evidence against adding them for frequency alone.

## Findings

1. **Fixed gaps alone were misleading.** Fibonacci levels + EMA200 + percent or
   retrace targets produced materially better DCA results than fixed 10-50%
   gaps.
2. **DCA can win raw ETH return, but not risk-adjusted return.** The best 5y DCA
   Calmar was 0.65 (`fixed_deep_percent15`) versus 1.00 for trend.
3. **The 50/50 ETH blend is the useful result.** It improves 5y Calmar to 1.20
   and test Calmar to 1.82, with a smaller drawdown than DCA alone.
4. **BTC does not benefit.** DCA made 0.0% in the BTC test and every blend
   reduced BTC Calmar. The blend is ETH-only.
5. **Deep levels rarely fill in a strong bull market.** The 2024-2026 test is a
   trend regime; DCA waits for 23.6-78.6% retracements that do not arrive, so it
   holds cash.
6. **ATR/geometric levels and martingale allocations are unstable.** ATR train
   results were negative; geometric variants reached -60% to -73% drawdown;
   anti-martingale had about -59% train drawdown. Do not use them as defaults.
7. **Anchor choice matters.** Using the first 30 days of the test as the anchor
   while trading starts 30 days later inflated earlier DCA test results. The
   corrected pre-window anchor is the number reported here.
8. **Higher frequency did not mean higher profit.** 15m trend lost 70-92% with
   costs; DCA either did not fill or had 43-59% drawdowns. Fees, slippage, and
   noise dominate at 15m.
9. **Indicator-derived S/R was not a free win.** PA/Donchian/extension checks
   helped in-sample but failed out-of-sample; the final trend filter keeps only
   the checks that survived the test window.

## Recommendation

- Keep the trend strategy as the core.
- Use `fib_deep_percent15` as the DCA default for research and the dashboard.
- Treat the 50/50 ETH blend as the best paper-trading candidate; do not apply it
  to BTC.
- Do not promote DCA or the blend to real capital without paper trading and a
  walk-forward/robustness pass.

## Caveats

- Open DCA lots are marked to market, not forced closed.
- The blend has no rebalancing; weights drift after the initial allocation.
- DCA variants were selected with in-sample information; the 2-year test is
  short and regime-specific.
- 15m is tested but rejected; 1m/5m microstructure and order-book data are not
  tested.
- Results are sensitive to fees, slippage, anchor, and the chosen target.
- Support/resistance is swing-pivot based, not volume-profile or order-block
  based; oscillator-derived S/R has not been validated as a DCA level source.

## Reproduce

```bash
./dev.sh python tests/run.py
./dev.sh python scripts/dca_study.py
./dev.sh python scripts/frequency_study.py
```

Interactive report:

```text
http://localhost:8000/dca
```

Downloadable Markdown for any parameter set:

```text
http://localhost:8000/dca/report?symbol=ETH/USDT&timeframe=4h&days=1900&level_mode=fib&allocation=deep&reference_mode=anchor&target_mode=percent&profit_target=15&reinvest_pct=50&trend_filter=ema200
```

Artifacts:

- `results/study_dca_5y.csv`
- `results/study_dca_test.csv`
- `results/study_dca_variants.csv`
- `results/study_dca_targets.csv`
- `results/study_dca_finalists_5y.csv`
- `results/study_blend_dca_trend.csv`
- `results/study_15m_sr.csv`
- `scripts/dca_study.py`
- `scripts/frequency_study.py`
- `src/trading_analysis/strategies/dca/`
- `src/trading_analysis/reporting/dca.py`
- `src/trading_analysis/analytics/portfolio.py`
