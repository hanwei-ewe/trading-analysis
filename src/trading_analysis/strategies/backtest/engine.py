import pandas as pd

from .checks import _warmup_bars
from .features import _regime_allows


def _fill(raw, side, slippage, entering):
    if entering:
        return raw * (1.0 + slippage) if side == "LONG" else raw * (1.0 - slippage)
    return raw * (1.0 - slippage) if side == "LONG" else raw * (1.0 + slippage)


def _exit_check(position, bar_open, bar_high, bar_low, target_ok=True):
    side = position["side"]
    stop = position["stop"]
    target = position["target"]
    if side == "LONG":
        if bar_open <= stop:
            return bar_open, "stop"
        if bar_low <= stop:
            return stop, "stop"
        if target_ok:
            if bar_open >= target:
                return bar_open, "target"
            if bar_high >= target:
                return target, "target"
    else:
        if bar_open >= stop:
            return bar_open, "stop"
        if bar_high >= stop:
            return stop, "stop"
        if target_ok:
            if bar_open <= target:
                return bar_open, "target"
            if bar_low <= target:
                return target, "target"
    return None, None


def _limit_fill(side, limit, bar_open, bar_high, bar_low):
    if side == "LONG":
        if bar_low <= limit:
            return min(bar_open, limit)
    else:
        if bar_high >= limit:
            return max(bar_open, limit)
    return None


def _target_price(side, entry, stop, proposal_t1, cfg, target_mode, target_r=None):
    if target_r is not None:
        rr = float(target_r)
    elif target_mode == "rr":
        rr = float(cfg["risk"]["min_rr"])
    else:
        return float(proposal_t1)
    risk = abs(entry - stop)
    return entry + rr * risk if side == "LONG" else entry - rr * risk


def _adjust_stop(side, entry, stop, mult):
    if side == "LONG":
        return entry - float(mult) * (entry - stop)
    return entry + float(mult) * (stop - entry)


def _position_units(equity, risk_pct, risk_per_unit, entry, cash_buffer, min_notional):
    if equity <= 0 or risk_per_unit <= 0 or entry <= 0:
        return 0.0
    risk_amount = equity * risk_pct / 100.0
    max_notional = equity * (1.0 - cash_buffer)
    units = min(risk_amount / risk_per_unit, max_notional / entry)
    if units * entry < min_notional:
        return 0.0
    return units


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
    return max(equity + net, 0.0), trade


def _run_engine(
    ind,
    results,
    cfg,
    window_start,
    initial_equity,
    fee_rate,
    slippage,
    target_mode="proposal",
    entry_mode="market",
    limit_bars=5,
    regime_bias=None,
    regime_filter="none",
    stop_mult=1.0,
    target_r=None,
    long_only=False,
    risk_pct=None,
    cash_buffer=0.02,
    min_notional=5.0,
    window_end=None,
):
    risk_pct = float(
        risk_pct if risk_pct is not None else cfg["risk"]["max_risk_pct"]
    )
    cash_buffer = float(cash_buffer)
    n = len(ind)
    warm = _warmup_bars(cfg)
    start_idx = warm
    while start_idx < n and ind.index[start_idx] < window_start:
        start_idx += 1
    if start_idx >= n:
        raise ValueError("not enough candles in the requested window")
    end_idx = n
    if window_end is not None:
        end_idx = int(ind.index.searchsorted(pd.Timestamp(window_end)))
        if end_idx <= start_idx:
            raise ValueError("window_end must be after window_start")

    by_pos = {i: res for i, res in results}
    equity = float(initial_equity)
    position = None
    pending = None
    prev_bias = None
    prev_signal = None
    trades = []
    curve = []
    bars_in_position = 0

    for i in range(start_idx, end_idx):
        ts = ind.index[i]
        bar_open = float(ind["open"].iloc[i])
        bar_high = float(ind["high"].iloc[i])
        bar_low = float(ind["low"].iloc[i])
        bar_close = float(ind["close"].iloc[i])
        exited_this_bar = False
        entered_this_bar = False
        target_ok = True

        if position is not None:
            if (
                prev_bias in ("LONG", "SHORT")
                and prev_bias != position["side"]
            ):
                equity, trade = _close(
                    position, bar_open, ts, i, equity, fee_rate, slippage, "signal"
                )
                trades.append(trade)
                position = None
                pending = None
                exited_this_bar = True
            else:
                raw_exit, reason = _exit_check(
                    position, bar_open, bar_high, bar_low
                )
                if raw_exit is not None:
                    equity, trade = _close(
                        position,
                        raw_exit,
                        ts,
                        i,
                        equity,
                        fee_rate,
                        slippage,
                        reason,
                    )
                    trades.append(trade)
                    position = None
                    exited_this_bar = True

        if position is None and not exited_this_bar:
            if entry_mode == "limit":
                if (
                    pending is not None
                    and prev_bias in ("LONG", "SHORT")
                    and prev_bias != pending["side"]
                ):
                    pending = None
                if pending is not None and i > pending["expires_index"]:
                    pending = None
                if pending is not None:
                    side = pending["side"]
                    original_stop = pending["stop"]
                    fill_raw = _limit_fill(
                        side, pending["limit"], bar_open, bar_high, bar_low
                    )
                    if fill_raw is not None:
                        entry = _fill(fill_raw, side, slippage, entering=True)
                        stop = _adjust_stop(
                            side, entry, original_stop, stop_mult
                        )
                        risk_per_unit = abs(entry - stop)
                        valid = (
                            entry > stop if side == "LONG" else entry < stop
                        )
                        if valid and risk_per_unit > 0:
                            target = _target_price(
                                side,
                                entry,
                                stop,
                                pending["t1"],
                                cfg,
                                target_mode,
                                target_r,
                            )
                            units = _position_units(
                                equity,
                                risk_pct,
                                risk_per_unit,
                                entry,
                                cash_buffer,
                                min_notional,
                            )
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
                                    "score": pending["score"],
                                    "confidence": pending["confidence"],
                                }
                                entered_this_bar = True
                                target_ok = fill_raw == bar_open
                        pending = None
            elif prev_signal is not None:
                side = prev_signal["direction"]
                original_stop = float(prev_signal["stop"])
                entry = _fill(bar_open, side, slippage, entering=True)
                stop = _adjust_stop(side, entry, original_stop, stop_mult)
                risk_per_unit = abs(entry - stop)
                target = _target_price(
                    side,
                    entry,
                    stop,
                    prev_signal["t1"],
                    cfg,
                    target_mode,
                    target_r,
                )
                if target_mode == "rr" or target_r is not None:
                    valid = (
                        entry > stop if side == "LONG" else entry < stop
                    )
                else:
                    valid = (
                        original_stop < bar_open < target
                        if side == "LONG"
                        else target < bar_open < original_stop
                    )
                if valid and risk_per_unit > 0:
                    units = _position_units(
                        equity,
                        risk_pct,
                        risk_per_unit,
                        entry,
                        cash_buffer,
                        min_notional,
                    )
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
                        entered_this_bar = True

        if entered_this_bar and position is not None:
            raw_exit, reason = _exit_check(
                position, bar_open, bar_high, bar_low, target_ok
            )
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
                candidate = dict(res["signal"])
                candidate["_score"] = res["score"]
                candidate["_confidence"] = res["confidence"]
                allowed = _regime_allows(
                    (regime_bias or {}).get(i),
                    candidate["direction"],
                    regime_filter,
                )
                if long_only and candidate["direction"] == "SHORT":
                    prev_signal = None
                    if pending is not None:
                        pending = None
                else:
                    prev_signal = candidate if allowed else None
                if (
                    entry_mode == "limit"
                    and position is None
                    and (not long_only or candidate["direction"] == "LONG")
                ):
                    if pending is not None and (
                        pending["side"] != candidate["direction"]
                        or not _regime_allows(
                            (regime_bias or {}).get(i),
                            pending["side"],
                            regime_filter,
                        )
                    ):
                        pending = None
                    if pending is None and allowed:
                        limit = (
                            float(candidate["entry_low"])
                            + float(candidate["entry_high"])
                        ) / 2.0
                        pending = {
                            "side": candidate["direction"],
                            "limit": limit,
                            "stop": float(candidate["stop"]),
                            "t1": float(candidate["t1"]),
                            "expires_index": i + int(limit_bars),
                            "score": res["score"],
                            "confidence": res["confidence"],
                        }
            else:
                prev_signal = None
                if entry_mode == "limit" and pending is not None:
                    if not _regime_allows(
                        (regime_bias or {}).get(i),
                        pending["side"],
                        regime_filter,
                    ):
                        pending = None

    if position is not None:
        last = end_idx - 1
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
        "end_index": end_idx,
    }

