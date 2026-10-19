import argparse
import json
import math
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import data as data_mod
from . import indicators as ind_mod
from .analysis import analyze
from .config import load_config, resolve_path
from .exchange import get_adapter

DEFAULT_CHECKS = ("regime", "ema_position", "bollinger", "vwap", "rsi")
ALL_CHECKS = (
    "regime",
    "ema_position",
    "rsi",
    "macd",
    "vwap",
    "bollinger",
    "stoch",
    "adx",
    "obv",
)


def _parse_checks(raw):
    if not raw or raw == "default":
        return list(DEFAULT_CHECKS)
    if raw == "all":
        return list(ALL_CHECKS)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    bad = set(parts) - set(ALL_CHECKS)
    if bad:
        raise ValueError(f"unknown checks: {', '.join(sorted(bad))}")
    return parts


def _warmup_bars(cfg):
    ind = cfg["indicators"]
    macd_cfg = ind["macd"]
    stoch_cfg = ind.get("stoch", [14, 3, 3])
    adx_period = ind.get("adx", 14)
    obv_period = ind.get("obv", 10)
    vwap_period = ind.get("vwap", ind.get("volume_ma", 20))
    need = max(
        max(ind["ema"]),
        ind["rsi"],
        macd_cfg[1] + macd_cfg[2],
        ind["atr"],
        ind["bollinger"][0],
        vwap_period,
        ind.get("volume_ma", 20),
        stoch_cfg[0] + stoch_cfg[1] + stoch_cfg[2],
        adx_period * 2,
        obv_period + 1,
    )
    return int(need) + int(cfg["swings"]["lookback"]) + 5


def _prep(df, cfg):
    ind = ind_mod.add_indicators(df, cfg)
    kp, dp, sp = [int(x) for x in cfg["indicators"].get("stoch", [14, 3, 3])]
    stoch = ind_mod.stochastic(ind["high"], ind["low"], ind["close"], kp, dp, sp)
    ind["stoch_k"] = stoch["stoch_k"]
    ind["stoch_d"] = stoch["stoch_d"]
    ap = int(cfg["indicators"].get("adx", 14))
    adx = ind_mod.adx(ind["high"], ind["low"], ind["close"], ap)
    ind["adx"] = adx["adx"]
    ind["plus_di"] = adx["plus_di"]
    ind["minus_di"] = adx["minus_di"]
    ind["obv"] = ind_mod.obv(ind["close"], ind["volume"])
    return ind


def _pivot_schedule(df, lookback):
    window = 2 * lookback + 1
    high = df["high"]
    low = df["low"]
    roll_high = high.rolling(window, center=True).max()
    roll_low = low.rolling(window, center=True).min()
    highs = defaultdict(list)
    lows = defaultdict(list)
    n = len(df)
    for j in range(n):
        confirm = j + lookback
        if confirm >= n:
            break
        rh = roll_high.iloc[j]
        rl = roll_low.iloc[j]
        if rh == rh and high.iloc[j] >= rh:
            highs[confirm].append(float(high.iloc[j]))
        if rl == rl and low.iloc[j] <= rl:
            lows[confirm].append(float(low.iloc[j]))
    return highs, lows


def _evaluate_frame(ind, cfg, active, timeframe, htf_checks_by_pos=None):
    n = len(ind)
    warm = _warmup_bars(cfg)
    if n <= warm:
        return []
    highs_by, lows_by = _pivot_schedule(ind, cfg["swings"]["lookback"])
    highs = []
    lows = []
    rows = []
    for i in range(warm, n):
        for level in highs_by.get(i, ()):
            insort(highs, level)
        for level in lows_by.get(i, ()):
            insort(lows, level)

        price = float(ind["close"].iloc[i])
        atr_v = float(ind["atr"].iloc[i])
        idx = bisect_right(highs, price)
        resistance = highs[idx] if idx < len(highs) else price + 2.0 * atr_v
        idx = bisect_left(lows, price) - 1
        support = lows[idx] if idx >= 0 else price - 2.0 * atr_v

        htf = (htf_checks_by_pos or {}).get(i)
        res = analyze(
            ind,
            cfg,
            ind=ind,
            active=active,
            timeframe=timeframe,
            htf_checks=htf,
            at=i,
            support=support,
            resistance=resistance,
        )
        rows.append(
            (
                i,
                {
                    "bias": res["bias"],
                    "signal": res["signal"],
                    "score": res["score"],
                    "max_score": res["max_score"],
                    "confidence": res["confidence"],
                },
            )
        )
    return rows


def _bias_frame(df, cfg, active, timeframe):
    ind = _prep(df, cfg)
    step = data_mod.parse_timeframe(timeframe)
    rows = []
    for i, res in _evaluate_frame(ind, cfg, active, timeframe):
        rows.append(
            {
                "close_time": ind.index[i] + pd.Timedelta(seconds=step),
                "bias": res["bias"],
                "score": res["score"],
                "max_score": res["max_score"],
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("close_time").drop_duplicates("close_time", keep="last")
    return out


def _align_bias(close_times, bias):
    base = pd.DataFrame({"close_time": close_times})
    return pd.merge_asof(base, bias, on="close_time", direction="backward")


def _htf_check_map(primary_ind, cfg, active, frames, primary_tf):
    step = data_mod.parse_timeframe(primary_tf)
    close_times = primary_ind.index + pd.Timedelta(seconds=step)
    out = {i: [] for i in range(len(primary_ind))}
    for htf, hdf in frames:
        bias = _bias_frame(hdf, cfg, active, htf)
        if bias.empty:
            continue
        aligned = _align_bias(close_times, bias)
        biases = aligned["bias"].tolist()
        scores = aligned["score"].tolist()
        max_scores = aligned["max_score"].tolist()
        for i, state in enumerate(biases):
            if pd.isna(state):
                continue
            vote = 1 if state == "LONG" else (-1 if state == "SHORT" else 0)
            out[i].append(
                {
                    "id": f"htf_{htf}",
                    "label": f"Higher timeframe ({htf}) bias",
                    "vote": vote,
                    "weight": vote,
                    "reading": (
                        f"{htf} reads {state} "
                        f"(score {int(scores[i]):+d}/{int(max_scores[i])})"
                    ),
                }
            )
    return {i: checks for i, checks in out.items() if checks}


def _fill(raw, side, slippage, entering):
    if entering:
        return raw * (1.0 + slippage) if side == "LONG" else raw * (1.0 - slippage)
    return raw * (1.0 - slippage) if side == "LONG" else raw * (1.0 + slippage)


def _exit_check(position, bar_open, bar_high, bar_low):
    side = position["side"]
    stop = position["stop"]
    target = position["target"]
    if side == "LONG":
        if bar_open <= stop:
            return bar_open, "stop"
        if bar_low <= stop:
            return stop, "stop"
        if bar_open >= target:
            return bar_open, "target"
        if bar_high >= target:
            return target, "target"
    else:
        if bar_open >= stop:
            return bar_open, "stop"
        if bar_high >= stop:
            return stop, "stop"
        if bar_open <= target:
            return bar_open, "target"
        if bar_low <= target:
            return target, "target"
    return None, None


def _close(position, raw_exit, exit_time, exit_index, equity, fee_rate, slippage, reason):
    side = position["side"]
    exit_price = _fill(raw_exit, side, slippage, entering=False)
    entry = position["entry"]
    units = position["units"]
    gross = units * (exit_price - entry) if side == "LONG" else units * (entry - exit_price)
    fees = units * fee_rate * (entry + exit_price)
    net = gross - fees
    trade = {
        "side": side,
        "entry_time": position["entry_time"].isoformat(),
        "exit_time": exit_time.isoformat(),
        "entry_price": entry,
        "exit_price": exit_price,
        "stop": position["stop"],
        "target": position["target"],
        "units": units,
        "risk": position["risk"],
        "pnl": net,
        "return_pct": net / equity if equity else 0.0,
        "r_multiple": net / position["risk"] if position["risk"] else 0.0,
        "reason": reason,
        "bars_held": max(0, exit_index - position["entry_index"]),
        "score": position["score"],
        "confidence": position["confidence"],
    }
    return equity + net, trade


def _run_engine(
    ind,
    results,
    cfg,
    window_start,
    initial_equity,
    fee_rate,
    slippage,
    target_mode="proposal",
):
    n = len(ind)
    warm = _warmup_bars(cfg)
    start_idx = warm
    while start_idx < n and ind.index[start_idx] < window_start:
        start_idx += 1
    if start_idx >= n:
        raise ValueError("not enough candles in the requested window")

    by_pos = {i: res for i, res in results}
    equity = float(initial_equity)
    position = None
    prev_bias = None
    prev_signal = None
    trades = []
    curve = []
    bars_in_position = 0

    for i in range(start_idx, n):
        ts = ind.index[i]
        bar_open = float(ind["open"].iloc[i])
        bar_high = float(ind["high"].iloc[i])
        bar_low = float(ind["low"].iloc[i])
        bar_close = float(ind["close"].iloc[i])

        if (
            position is not None
            and prev_bias in ("LONG", "SHORT")
            and prev_bias != position["side"]
        ):
            equity, trade = _close(
                position, bar_open, ts, i, equity, fee_rate, slippage, "signal"
            )
            trades.append(trade)
            position = None

        if position is None and prev_signal is not None:
            side = prev_signal["direction"]
            stop = float(prev_signal["stop"])
            entry = _fill(bar_open, side, slippage, entering=True)
            risk_per_unit = abs(entry - stop)
            if target_mode == "rr":
                rr = float(cfg["risk"]["min_rr"])
                target = (
                    entry + rr * risk_per_unit
                    if side == "LONG"
                    else entry - rr * risk_per_unit
                )
                valid = entry > stop if side == "LONG" else entry < stop
            else:
                target = float(prev_signal["t1"])
                valid = (
                    stop < bar_open < target
                    if side == "LONG"
                    else target < bar_open < stop
                )
            if valid and risk_per_unit > 0:
                risk_amount = equity * float(cfg["risk"]["max_risk_pct"]) / 100.0
                units = min(risk_amount / risk_per_unit, equity / entry)
                if units > 0:
                    position = {
                        "side": side,
                        "entry": entry,
                        "stop": stop,
                        "target": target,
                        "units": units,
                        "risk": units * risk_per_unit,
                        "entry_time": ts,
                        "entry_index": i,
                        "score": prev_signal.get("_score"),
                        "confidence": prev_signal.get("_confidence"),
                    }

        if position is not None:
            raw_exit, reason = _exit_check(position, bar_open, bar_high, bar_low)
            if raw_exit is not None:
                equity, trade = _close(
                    position, raw_exit, ts, i, equity, fee_rate, slippage, reason
                )
                trades.append(trade)
                position = None

        if position is not None:
            bars_in_position += 1
            if position["side"] == "LONG":
                unrealized = position["units"] * (bar_close - position["entry"])
            else:
                unrealized = position["units"] * (position["entry"] - bar_close)
            mtm = equity + unrealized
        else:
            mtm = equity
        curve.append({"time": ts, "equity": mtm})

        res = by_pos.get(i)
        if res is None:
            prev_bias = None
            prev_signal = None
        else:
            prev_bias = res["bias"]
            if res["bias"] in ("LONG", "SHORT") and res["signal"]:
                prev_signal = dict(res["signal"])
                prev_signal["_score"] = res["score"]
                prev_signal["_confidence"] = res["confidence"]
            else:
                prev_signal = None

    if position is not None:
        last = n - 1
        equity, trade = _close(
            position,
            float(ind["close"].iloc[last]),
            ind.index[last],
            last,
            equity,
            fee_rate,
            slippage,
            "end",
        )
        trades.append(trade)
        curve[-1]["equity"] = equity

    return {
        "equity_curve": curve,
        "trades": trades,
        "bars_in_position": bars_in_position,
        "initial_equity": float(initial_equity),
        "start_index": start_idx,
    }


def _metrics(engine, ind, timeframe, buy_hold):
    curve = engine["equity_curve"]
    trades = engine["trades"]
    initial = engine["initial_equity"]
    step = data_mod.parse_timeframe(timeframe)
    periods = 365.25 * 24 * 3600 / step

    equity = pd.Series([c["equity"] for c in curve])
    equity.index = pd.DatetimeIndex([c["time"] for c in curve])
    returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    final = float(equity.iloc[-1]) if len(equity) else initial
    total_return = final / initial - 1.0
    years = len(equity) / periods if periods else 0.0
    cagr = (final / initial) ** (1.0 / years) - 1.0 if years > 0 and final > 0 else 0.0
    vol = float(returns.std()) if len(returns) > 1 else 0.0
    sharpe = float(returns.mean() / vol * math.sqrt(periods)) if vol > 0 else 0.0
    downside = returns.clip(upper=0.0)
    downside_std = float(np.sqrt((downside**2).mean())) if len(returns) else 0.0
    sortino = (
        float(returns.mean() / downside_std * math.sqrt(periods))
        if downside_std > 0
        else 0.0
    )
    drawdown = float((equity / equity.cummax() - 1.0).min()) if len(equity) else 0.0
    calmar = cagr / abs(drawdown) if drawdown < 0 else 0.0

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0.0
    )
    r_values = [t["r_multiple"] for t in trades]
    exposure = (
        engine["bars_in_position"] / len(curve) if curve else 0.0
    )

    return {
        "initial_equity": initial,
        "final_equity": final,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": drawdown,
        "calmar": calmar,
        "buy_hold_return": buy_hold,
        "excess_return": total_return - buy_hold,
        "trades": len(trades),
        "long_trades": sum(1 for t in trades if t["side"] == "LONG"),
        "short_trades": sum(1 for t in trades if t["side"] == "SHORT"),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "profit_factor": profit_factor,
        "avg_r": float(np.mean(r_values)) if r_values else 0.0,
        "best_r": max(r_values) if r_values else 0.0,
        "worst_r": min(r_values) if r_values else 0.0,
        "avg_trade_pct": (
            float(np.mean([t["return_pct"] for t in trades])) if trades else 0.0
        ),
        "exposure": exposure,
        "bars": len(curve),
        "start": curve[0]["time"].isoformat() if curve else None,
        "end": curve[-1]["time"].isoformat() if curve else None,
        "timeframe": timeframe,
    }


def _buy_hold(ind, start_idx):
    first = float(ind["close"].iloc[start_idx])
    last = float(ind["close"].iloc[-1])
    return last / first - 1.0 if first else 0.0


def run_backtest(
    config_path=None,
    timeframe=None,
    days=365,
    checks=None,
    initial_equity=10000.0,
    fee=0.001,
    slippage=0.0005,
    use_cache=True,
    use_mtf=True,
    target_mode="proposal",
    adapter=None,
    df=None,
    htf_dfs=None,
):
    cfg = load_config(config_path)
    pair = cfg["universe"]["pair"]
    tf = timeframe or cfg["timeframes"]["primary"]
    active = set(checks or DEFAULT_CHECKS)
    step = data_mod.parse_timeframe(tf)
    warm = _warmup_bars(cfg)
    cache_dir = cfg["paths"]["cache"]

    if df is None:
        adapter = adapter or get_adapter(cfg["exchange"]["market_type"])
        extra_days = warm * step / 86400.0 + 2.0
        df = data_mod.load_history(
            adapter, pair, tf, days + extra_days, cache_dir=cache_dir, use_cache=use_cache
        )
    df = df.sort_index()
    if len(df) <= warm + 10:
        raise ValueError(
            f"need more than {warm + 10} candles, got {len(df)}"
        )

    primary_ind = _prep(df, cfg)

    htf_frames = []
    if use_mtf:
        specs = [cfg["timeframes"]["regime"], *cfg["timeframes"]["context"]]
        for htf in dict.fromkeys(specs):
            htf_step = data_mod.parse_timeframe(htf)
            if htf == tf or htf_step <= step:
                continue
            if htf_dfs is not None:
                if htf in htf_dfs:
                    htf_frames.append((htf, htf_dfs[htf].sort_index()))
                continue
            extra_days = warm * htf_step / 86400.0 + 2.0
            hdf = data_mod.load_history(
                adapter,
                pair,
                htf,
                days + extra_days,
                cache_dir=cache_dir,
                use_cache=use_cache,
            )
            htf_frames.append((htf, hdf.sort_index()))

    htf_by_pos = (
        _htf_check_map(primary_ind, cfg, active, htf_frames, tf)
        if htf_frames
        else {}
    )
    results = _evaluate_frame(primary_ind, cfg, active, tf, htf_by_pos)

    window_start = primary_ind.index[-1] - pd.Timedelta(days=days)
    warm_start = primary_ind.index[min(warm, len(primary_ind) - 1)]
    if window_start < warm_start:
        window_start = warm_start

    engine = _run_engine(
        primary_ind,
        results,
        cfg,
        window_start,
        initial_equity,
        float(fee),
        float(slippage),
        target_mode=target_mode,
    )
    start_idx = engine["start_index"]
    metrics = _metrics(
        engine, primary_ind, tf, _buy_hold(primary_ind, start_idx)
    )
    return {
        "symbol": pair,
        "timeframe": tf,
        "days": days,
        "checks": sorted(active),
        "htf_frames": [htf for htf, _ in htf_frames],
        "fee": float(fee),
        "slippage": float(slippage),
        "target_mode": target_mode,
        "metrics": metrics,
        "trades": engine["trades"],
        "equity_curve": engine["equity_curve"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _json_ready(value):
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def to_markdown(result):
    m = result["metrics"]
    lines = [
        f"# Backtest — {result['symbol']} {result['timeframe']}",
        "",
        f"- Window: {m['start']} → {m['end']} ({m['bars']} bars)",
        f"- Checks: {', '.join(result['checks'])}",
        f"- Higher frames: {', '.join(result['htf_frames']) or 'none'}",
        f"- Costs: {result['fee'] * 100:.3f}% fee, "
        f"{result['slippage'] * 100:.3f}% slippage",
        f"- Target: {'2R from fill' if result.get('target_mode') == 'rr' else 'proposal T1'}",
        "",
        "## Performance",
        "",
        "| Metric | Strategy | Buy & hold |",
        "| --- | ---: | ---: |",
        f"| Total return | {m['total_return'] * 100:.2f}% | "
        f"{m['buy_hold_return'] * 100:.2f}% |",
        f"| CAGR | {m['cagr'] * 100:.2f}% | — |",
        f"| Sharpe | {m['sharpe']:.2f} | — |",
        f"| Sortino | {m['sortino']:.2f} | — |",
        f"| Max drawdown | {m['max_drawdown'] * 100:.2f}% | — |",
        f"| Calmar | {m['calmar']:.2f} | — |",
        "",
        "## Trading",
        "",
        f"- Trades: {m['trades']} "
        f"({m['long_trades']} long / {m['short_trades']} short)",
        f"- Win rate: {m['win_rate'] * 100:.1f}%",
        f"- Profit factor: {m['profit_factor']:.2f}",
        f"- Avg R: {m['avg_r']:.2f} (best {m['best_r']:.2f}, "
        f"worst {m['worst_r']:.2f})",
        f"- Exposure: {m['exposure'] * 100:.1f}%",
        f"- Final equity: {m['final_equity']:,.2f} "
        f"from {m['initial_equity']:,.2f}",
    ]
    return "\n".join(lines) + "\n"


def save_results(result, config_path=None):
    cfg = load_config(config_path)
    out_dir = resolve_path(cfg["paths"]["results"])
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    symbol = result["symbol"].replace("/", "_")
    base = out_dir / f"backtest_{symbol}_{result['timeframe']}_{result['days']}d_{stamp}"

    payload = dict(result)
    payload["equity_curve"] = result["equity_curve"]
    base.with_suffix(".json").write_text(
        json.dumps(_json_ready(payload), indent=2), encoding="utf-8"
    )
    base.with_suffix(".md").write_text(to_markdown(result), encoding="utf-8")

    trades = pd.DataFrame(result["trades"])
    if not trades.empty:
        trades.to_csv(base.parent / f"{base.name}_trades.csv", index=False)
    curve = pd.DataFrame(result["equity_curve"])
    curve.to_csv(base.parent / f"{base.name}_equity.csv", index=False)
    return {
        "json": str(base.with_suffix(".json")),
        "markdown": str(base.with_suffix(".md")),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Backtest the confluence strategy")
    parser.add_argument("--config", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--checks", default="default",
                        help="default, all, or comma-separated check ids")
    parser.add_argument("--equity", type=float, default=10000.0)
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--no-mtf", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--target", choices=("proposal", "rr"), default="proposal")
    args = parser.parse_args(argv)

    result = run_backtest(
        config_path=args.config,
        timeframe=args.timeframe,
        days=args.days,
        checks=_parse_checks(args.checks),
        initial_equity=args.equity,
        fee=args.fee,
        slippage=args.slippage,
        use_cache=not args.no_cache,
        use_mtf=not args.no_mtf,
        target_mode=args.target,
    )
    paths = save_results(result, args.config)
    print(to_markdown(result))
    print(f"Saved: {paths['json']}")
    print(f"Saved: {paths['markdown']}")
    return result


if __name__ == "__main__":
    main()
