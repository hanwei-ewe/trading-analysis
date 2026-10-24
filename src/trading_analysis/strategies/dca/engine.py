import math

import numpy as np
import pandas as pd

from ... import indicators as ind_mod
from .levels import FIB_LEVELS, _resolve_levels, _target_price, _trend_leg, _validate


def run_dca(
    df,
    initial_capital=1000.0,
    levels=None,
    allocations=None,
    level_mode="fixed",
    level_base=0.10,
    atr_period=14,
    profit_target=0.10,
    target_mode="percent",
    target_retrace=0.382,
    target_atr=3.0,
    reference_mode="anchor",
    reference_lookback=180,
    swing_lookback=50,
    reinvest_pct=0.5,
    allocation_mode="equity",
    trend_filter="none",
    ema_period=200,
    allow_reentry=True,
    fee=0.001,
    slippage=0.0005,
    min_notional=5.0,
    include_curve=False,
):
    if level_mode not in ("fixed", "fib", "trend_fib", "atr", "geometric"):
        raise ValueError("level_mode must be fixed, fib, trend_fib, atr, or geometric")
    if target_mode not in ("percent", "retrace", "atr"):
        raise ValueError("target_mode must be percent, retrace, or atr")
    if reference_mode not in ("anchor", "rolling", "ath"):
        raise ValueError("reference_mode must be anchor, rolling, or ath")
    if allocation_mode not in ("equity", "fixed"):
        raise ValueError("allocation_mode must be equity or fixed")
    if trend_filter not in ("none", "ema200"):
        raise ValueError("trend_filter must be none or ema200")
    if not 0 <= float(reinvest_pct) <= 1:
        raise ValueError("reinvest_pct must be in [0, 1]")
    if float(profit_target) <= 0:
        raise ValueError("profit_target must be > 0")
    if not 0 < float(target_retrace) < 1:
        raise ValueError("target_retrace must be in (0, 1)")
    if float(target_atr) <= 0:
        raise ValueError("target_atr must be > 0")
    if int(reference_lookback) < 2:
        raise ValueError("reference_lookback must be >= 2")
    if int(swing_lookback) < 2:
        raise ValueError("swing_lookback must be >= 2")
    if int(atr_period) < 2:
        raise ValueError("atr_period must be >= 2")
    if int(ema_period) < 2:
        raise ValueError("ema_period must be >= 2")

    levels, allocations = _resolve_levels(
        level_mode, levels, allocations, level_base
    )
    _validate(level_mode, levels, allocations)

    frame = df.sort_index()
    if len(frame) <= int(reference_lookback) + 1:
        raise ValueError("not enough bars for reference_lookback")
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    open_ = frame["open"].astype(float)
    close = frame["close"].astype(float)

    lookback = int(reference_lookback)
    if reference_mode == "anchor":
        anchor = float(high.iloc[:lookback].max())
        refs = pd.Series(anchor, index=frame.index)
    elif reference_mode == "rolling":
        refs = high.shift(1).rolling(lookback).max()
    else:
        refs = high.shift(1).cummax()

    atr_series = ind_mod.atr(high, low, close, int(atr_period))
    ema_series = (
        ind_mod.ema(close, int(ema_period)) if trend_filter == "ema200" else None
    )

    cash = float(initial_capital)
    reserve = 0.0
    realized_profit = 0.0
    lots = []
    armed = [None] * len(levels)
    sells = []
    buys = []
    curve = []
    min_cash = cash
    max_deployed = 0.0

    for i in range(lookback, len(frame)):
        ts = frame.index[i]
        o = float(open_.iloc[i])
        h = float(high.iloc[i])
        l = float(low.iloc[i])
        c = float(close.iloc[i])
        ref = float(refs.iloc[i])
        atr = float(atr_series.iloc[i - 1]) if i > 0 else float("nan")
        prev_close = float(close.iloc[i - 1]) if i > 0 else c
        prev_ema = (
            float(ema_series.iloc[i - 1])
            if ema_series is not None and i > 0
            else float("nan")
        )
        trend_ok = (
            trend_filter == "none"
            or (math.isfinite(prev_ema) and prev_close > prev_ema)
        )

        sold_levels = set()
        remaining = []
        for lot in lots:
            if h < lot["target"]:
                remaining.append(lot)
                continue
            fill = max(o, lot["target"])
            proceeds = lot["units"] * fill * (1.0 - fee)
            pnl = proceeds - lot["cost"]
            cash += proceeds
            if pnl > 0:
                reserved = pnl * (1.0 - reinvest_pct)
                reserve += reserved
                cash -= reserved
                realized_profit += pnl
            sells.append(
                {
                    "entry_time": lot["entry_time"],
                    "exit_time": ts.isoformat(),
                    "entry_price": lot["entry_price"],
                    "exit_price": fill,
                    "units": lot["units"],
                    "pnl": pnl,
                    "r_multiple": pnl / lot["cost"] if lot["cost"] else 0.0,
                    "bars_held": i - lot["entry_index"],
                    "level": levels[lot["level_index"]],
                    "reason": "target",
                }
            )
            sold_levels.add(lot["level_index"])
            if allow_reentry and i > lot["entry_index"]:
                armed[lot["level_index"]] = True
        lots = remaining

        level_prices = None
        target_ref = ref
        if level_mode == "trend_fib":
            leg = _trend_leg(
                high.to_numpy(), low.to_numpy(), i, int(swing_lookback)
            )
            if leg is not None:
                leg_high, leg_low = leg
                if leg_high > leg_low:
                    target_ref = leg_high
                    level_prices = [
                        leg_high - level * (leg_high - leg_low)
                        for level in levels
                    ]
        elif math.isfinite(ref) and ref > 0:
            if level_mode == "atr":
                if math.isfinite(atr) and atr > 0:
                    level_prices = [ref - level * atr for level in levels]
            else:
                level_prices = [ref * (1.0 - level) for level in levels]
        if level_prices is not None and any(price <= 0 for price in level_prices):
            level_prices = None

        if level_prices is not None and trend_ok:
            order = sorted(range(len(levels)), key=lambda j: -level_prices[j])
            for j in order:
                if j in sold_levels:
                    continue
                if any(lot["level_index"] == j for lot in lots):
                    continue
                level_price = level_prices[j]
                if armed[j] is None:
                    armed[j] = prev_close > level_price
                if l > level_price:
                    if c > level_price:
                        armed[j] = True
                    continue
                if not armed[j]:
                    continue
                fill = min(o, level_price) * (1.0 + slippage)
                market_value = sum(lot["units"] * o for lot in lots)
                trading_equity = cash + market_value
                if allocation_mode == "fixed":
                    desired = initial_capital * allocations[j]
                else:
                    desired = trading_equity * allocations[j]
                budget = min(desired, cash)
                if budget < min_notional:
                    continue
                units = budget / (fill * (1.0 + fee))
                cost = units * fill * (1.0 + fee)
                cash -= cost
                min_cash = min(min_cash, cash)
                target = _target_price(
                    fill,
                    target_ref,
                    atr,
                    target_mode,
                    profit_target,
                    target_retrace,
                    target_atr,
                )
                lots.append(
                    {
                        "entry_time": ts.isoformat(),
                        "entry_index": i,
                        "entry_price": fill,
                        "units": units,
                        "cost": cost,
                        "target": target,
                        "level_index": j,
                    }
                )
                buys.append(
                    {
                        "time": ts.isoformat(),
                        "price": fill,
                        "units": units,
                        "cost": cost,
                        "level": levels[j],
                        "target": target,
                    }
                )
                armed[j] = False

        market_value = sum(lot["units"] * c for lot in lots)
        deployed = sum(lot["cost"] for lot in lots)
        max_deployed = max(max_deployed, deployed)
        curve.append(
            {
                "time": ts,
                "cash": cash,
                "reserve": reserve,
                "market_value": market_value,
                "trading_equity": cash + market_value,
                "total_wealth": cash + market_value + reserve,
            }
        )

    final = curve[-1] if curve else None
    if final is None:
        raise ValueError("no bars processed")
    total_wealth = float(final["total_wealth"])
    trading_equity = float(final["trading_equity"])
    total_return = total_wealth / initial_capital - 1.0
    step_seconds = (
        (frame.index[-1] - frame.index[0]).total_seconds() / (len(frame) - 1)
        if len(frame) > 1
        else 0.0
    )
    years = len(curve) * step_seconds / (365.25 * 24 * 3600.0)
    cagr = (total_wealth / initial_capital) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    wealth = pd.Series([row["total_wealth"] for row in curve])
    trading = pd.Series([row["trading_equity"] for row in curve])
    max_dd = float((wealth / wealth.cummax() - 1.0).min()) if len(wealth) else 0.0
    trading_dd = float((trading / trading.cummax() - 1.0).min()) if len(trading) else 0.0
    open_lots = [
        {
            **lot,
            "unrealized": lot["units"] * float(close.iloc[-1]) - lot["cost"],
        }
        for lot in lots
    ]
    return {
        "initial_capital": float(initial_capital),
        "final_total_wealth": total_wealth,
        "final_trading_equity": trading_equity,
        "final_reserve": float(reserve),
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "trading_drawdown": trading_dd,
        "realized_profit": float(realized_profit),
        "buys": len(buys),
        "sells": len(sells),
        "open_lots": open_lots,
        "open_lot_count": len(open_lots),
        "min_cash": float(min_cash),
        "max_deployed": float(max_deployed),
        "exposure": (
            sum(1 for row in curve if row["market_value"] > 0) / len(curve)
            if curve
            else 0.0
        ),
        "avg_hold_bars": (
            float(np.mean([t["bars_held"] for t in sells])) if sells else 0.0
        ),
        "win_rate": (
            sum(1 for t in sells if t["pnl"] > 0) / len(sells) if sells else 0.0
        ),
        "buy_hold_return": float(close.iloc[-1] / close.iloc[lookback] - 1.0),
        "level_mode": level_mode,
        "bars": len(df),
        "levels": list(levels),
        "allocations": list(allocations),
        "target_mode": target_mode,
        "profit_target": float(profit_target),
        "target_retrace": float(target_retrace),
        "target_atr": float(target_atr),
        "reference_mode": reference_mode,
        "reference_lookback": int(reference_lookback),
        "swing_lookback": int(swing_lookback),
        "reinvest_pct": float(reinvest_pct),
        "trend_filter": trend_filter,
        "ema_period": int(ema_period),
        "atr_period": int(atr_period),
        "level_base": float(level_base),
        "buy_trades": buys if include_curve else [],
        "sell_trades": sells if include_curve else [],
        "equity_curve": curve if include_curve else [],
    }
