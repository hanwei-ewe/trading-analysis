from ..indicators import add_indicators
from .checks import ANALYSIS_DEFAULT_CHECKS, CHECKS, CheckContext
from .levels import _build_signal, _nearest_above, _nearest_below, _swing_points


def analyze(
    df,
    cfg,
    ind=None,
    active=None,
    timeframe=None,
    htf_checks=None,
    at=None,
    support=None,
    resistance=None,
):
    if ind is None:
        ind = add_indicators(df, cfg)
    tf = timeframe or cfg["timeframes"]["primary"]
    min_history = int(cfg["indicators"]["ema"][-1]) + 5
    if len(ind) < min_history:
        raise ValueError(f"need >= {min_history} candles, got {len(ind)}")

    pos = len(ind) - 1 if at is None else (at if at >= 0 else len(ind) + at)
    last = ind.iloc[pos]
    price = float(last["close"])

    periods = tuple(int(value) for value in cfg["indicators"]["ema"])
    ema_short = float(last[f"ema_{periods[0]}"])
    ema_mid = float(last[f"ema_{periods[1]}"])
    ema_long = float(last[f"ema_{periods[2]}"])

    atr_v = float(last["atr"])
    rsi_v = float(last["rsi"])
    macd_line = float(last["macd"])
    macd_signal = float(last["macd_signal"])
    macd_hist = float(last["macd_hist"])
    vwap_v = float(last["vwap"])
    volume = float(last["volume"])
    vol_ma = float(last["vol_ma"])
    bb_upper = float(last["bb_upper"])
    bb_lower = float(last["bb_lower"])
    bb_width = float(last["bb_width"])

    if ema_short > ema_mid > ema_long and price > ema_mid:
        regime = "trending-up"
    elif ema_short < ema_mid < ema_long and price < ema_mid:
        regime = "trending-down"
    elif abs(ema_mid - ema_long) / price < 0.005:
        regime = "ranging"
    else:
        regime = "transition"

    if rsi_v >= 55 and macd_hist > 0:
        momentum = "bullish"
    elif rsi_v <= 45 and macd_hist < 0:
        momentum = "bearish"
    else:
        momentum = "neutral"

    atr_pct = atr_v / price * 100.0
    if atr_pct >= 3.0:
        vol_state = "high"
    elif atr_pct <= 1.0:
        vol_state = "low"
    else:
        vol_state = "normal"

    if support is None or resistance is None:
        swing_highs, swing_lows = _swing_points(ind, cfg["swings"]["lookback"])
        if resistance is None:
            resistance = _nearest_above(swing_highs, price)
        if support is None:
            support = _nearest_below(swing_lows, price)
        if resistance is None:
            resistance = price + 2.0 * atr_v
        if support is None:
            support = price - 2.0 * atr_v

    if vol_ma and volume >= 1.5 * vol_ma:
        volume_state = "spike"
    elif vol_ma and volume <= 0.5 * vol_ma:
        volume_state = "thin"
    else:
        volume_state = "normal"

    if active is None:
        active = set(ANALYSIS_DEFAULT_CHECKS)
    active = set(active)

    ctx = CheckContext(
        ind=ind,
        cfg=cfg,
        pos=pos,
        timeframe=tf,
        support=support,
        resistance=resistance,
        regime=regime,
        ema_short=ema_short,
        ema_mid=ema_mid,
        ema_long=ema_long,
        periods=periods,
    )
    checks = []
    for check in CHECKS:
        if check.id not in active:
            continue
        result = check.evaluate(ctx)
        if result is not None:
            checks.append(result.as_dict())

    for htf in htf_checks or []:
        checks.append(dict(htf))

    n_checks = len(checks)
    score = sum(c["weight"] for c in checks)
    agree = abs(score) / n_checks if n_checks else 0.0

    if n_checks < 2 or abs(score) < 2 or agree < 0.6:
        bias = "NEUTRAL-FLAT"
    else:
        bias = "LONG" if score > 0 else "SHORT"

    if bias == "NEUTRAL-FLAT":
        confidence = "Low"
    elif agree >= 0.8 and abs(score) >= 3:
        confidence = "High"
    else:
        confidence = "Medium"

    if htf_checks and bias in ("LONG", "SHORT"):
        opposing = any(
            (bias == "LONG" and c["weight"] < 0)
            or (bias == "SHORT" and c["weight"] > 0)
            for c in htf_checks
        )
        if opposing and confidence == "High":
            confidence = "Medium"

    signal = None
    if bias in ("LONG", "SHORT"):
        signal = _build_signal(bias, price, atr_v, support, resistance, cfg, tf)
        if signal is None:
            bias = "NEUTRAL-FLAT"
            confidence = "Low"

    return {
        "price": price,
        "bias": bias,
        "confidence": confidence,
        "score": score,
        "max_score": n_checks,
        "active": [c["id"] for c in checks],
        "checks": checks,
        "regime": {
            "state": regime,
            "ema_short": ema_short,
            "ema_mid": ema_mid,
            "ema_long": ema_long,
        },
        "momentum": {
            "state": momentum,
            "rsi": rsi_v,
            "macd": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
        },
        "volatility": {
            "state": vol_state,
            "atr": atr_v,
            "atr_pct": atr_pct,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_width": bb_width,
        },
        "levels": {
            "support": support,
            "resistance": resistance,
            "vwap": vwap_v,
        },
        "volume": {
            "state": volume_state,
            "volume": volume,
            "volume_ma": vol_ma,
        },
        "signal": signal,
        "assumptions": [
            "Indicators computed on closed candles only.",
            "Levels derived from 5-bar swing pivots, not volume profile.",
            "No order-book or funding-rate data used.",
        ],
    }
