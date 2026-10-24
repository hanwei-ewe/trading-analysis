from .. import indicators as ind_mod
from ..indicators import add_indicators
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

    periods = cfg["indicators"]["ema"]
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
        active = {"regime", "ema_position", "rsi", "macd", "vwap"}
    active = set(active)

    checks = []

    def add_check(cid, label, vote, reading):
        checks.append(
            {
                "id": cid,
                "label": label,
                "vote": vote,
                "weight": vote,
                "reading": reading,
            }
        )

    if "regime" in active:
        if regime == "trending-up":
            regime_vote = 1
        elif regime == "trending-down":
            regime_vote = -1
        else:
            regime_vote = 0
        add_check(
            "regime",
            f"Trend structure (EMA {periods[0]}/{periods[1]}/{periods[2]})",
            regime_vote,
            (
                f"EMA{periods[0]} {ema_short:,.2f}, EMA{periods[1]} {ema_mid:,.2f}, "
                f"EMA{periods[2]} {ema_long:,.2f} -> {regime}"
            ),
        )

    if "ema_position" in active:
        ema_pos_vote = 1 if price > ema_mid else -1
        add_check(
            "ema_position",
            f"Price vs EMA{periods[1]}",
            ema_pos_vote,
            (
                f"price {price:,.2f} is "
                f"{'above' if price > ema_mid else 'below'} "
                f"EMA{periods[1]} {ema_mid:,.2f}"
            ),
        )

    if "rsi" in active:
        if rsi_v > 55:
            rsi_vote = 1
        elif rsi_v < 45:
            rsi_vote = -1
        else:
            rsi_vote = 0
        add_check("rsi", "RSI (Relative Strength Index)", rsi_vote, f"RSI {rsi_v:.1f}")

    if "macd" in active:
        macd_vote = 1 if macd_hist > 0 else -1
        add_check(
            "macd",
            "MACD histogram (Moving Avg Convergence Divergence)",
            macd_vote,
            f"histogram {macd_hist:+.3f}",
        )

    if "vwap" in active:
        vwap_vote = 1 if price > vwap_v else -1
        add_check(
            "vwap",
            "Price vs VWAP (Volume-Weighted Avg Price)",
            vwap_vote,
            f"price {price:,.2f} vs VWAP {vwap_v:,.2f}",
        )

    if "bollinger" in active:
        span = bb_upper - bb_lower
        pct_b = (price - bb_lower) / span if span else 0.5
        if pct_b > 1:
            pct_b_vote = 1
        elif pct_b < 0:
            pct_b_vote = -1
        else:
            pct_b_vote = 0
        add_check(
            "bollinger",
            "Bollinger Bands (%B)",
            pct_b_vote,
            f"%B {pct_b:.2f}, width {bb_width / price * 100.0:.2f}%",
        )

    if "stoch" in active:
        kp, dp, sp = [int(x) for x in cfg["indicators"].get("stoch", [14, 3, 3])]
        if "stoch_k" in ind.columns and "stoch_d" in ind.columns:
            k = float(ind["stoch_k"].iloc[pos])
            d = float(ind["stoch_d"].iloc[pos])
        else:
            k = d = float("nan")
            if len(ind) > max(kp, dp, sp):
                s = ind_mod.stochastic(ind["high"], ind["low"], ind["close"], kp, dp, sp)
                k = float(s["stoch_k"].iloc[pos])
                d = float(s["stoch_d"].iloc[pos])
        if k == k and d == d:
            add_check(
                "stoch",
                f"Stochastic ({kp},{dp},{sp})",
                1 if k > d else -1,
                f"%K {k:.1f} vs %D {d:.1f}",
            )

    if "adx" in active:
        ap = int(cfg["indicators"].get("adx", 14))
        if "adx" in ind.columns and "plus_di" in ind.columns:
            adx_v = float(ind["adx"].iloc[pos])
            pdi = float(ind["plus_di"].iloc[pos])
            mdi = float(ind["minus_di"].iloc[pos])
        else:
            adx_v = pdi = mdi = float("nan")
            if len(ind) > ap + 1:
                a = ind_mod.adx(ind["high"], ind["low"], ind["close"], ap)
                adx_v = float(a["adx"].iloc[pos])
                pdi = float(a["plus_di"].iloc[pos])
                mdi = float(a["minus_di"].iloc[pos])
        if adx_v == adx_v:
            adx_vote = 0 if adx_v < 20 else (1 if pdi > mdi else -1)
            add_check(
                "adx",
                f"ADX (Average Directional Index) / DI ({ap})",
                adx_vote,
                f"ADX {adx_v:.1f}, +DI {pdi:.1f}, -DI {mdi:.1f}",
            )

    if "obv" in active:
        obl = int(cfg["indicators"].get("obv", 10))
        if "obv" in ind.columns:
            o = ind["obv"]
            ok = pos - obl >= 0
            rising = ok and float(o.iloc[pos]) > float(o.iloc[pos - obl])
        else:
            ok = len(ind) > obl + 1
            rising = False
            if ok:
                o = ind_mod.obv(ind["close"], ind["volume"])
                rising = float(o.iloc[pos]) > float(o.iloc[pos - obl])
        if ok:
            add_check(
                "obv",
                f"OBV (On-Balance Volume, {obl})",
                1 if rising else -1,
                f"{'rising' if rising else 'falling'} over the last {obl} bars",
            )

    if "pa" in active:
        prev = ind.iloc[pos - 1]
        o = float(last["open"])
        h = float(last["high"])
        l = float(last["low"])
        c = float(last["close"])
        po = float(prev["open"])
        pc = float(prev["close"])
        body = max(abs(c - o), 1e-12)
        bull_engulf = c > o and pc < po and c >= po and o <= pc
        bear_engulf = c < o and pc > po and c <= po and o >= pc
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        bull_pin = lower_wick > 2.0 * body and lower_wick > upper_wick
        bear_pin = upper_wick > 2.0 * body and upper_wick > lower_wick
        if bull_engulf or bull_pin:
            pa_vote = 1
        elif bear_engulf or bear_pin:
            pa_vote = -1
        else:
            pa_vote = 0
        add_check(
            "pa",
            "Price action (engulfing/pin bar)",
            pa_vote,
            (
                f"{'bullish' if pa_vote > 0 else 'bearish' if pa_vote < 0 else 'none'}"
                f" candle, body {body:.2f}, wicks {lower_wick:.2f}/{upper_wick:.2f}"
            ),
        )

    if "breakout" in active:
        bp = int(cfg["indicators"].get("breakout", 20))
        if pos >= bp:
            prior_high = float(ind["high"].iloc[pos - bp:pos].max())
            prior_low = float(ind["low"].iloc[pos - bp:pos].min())
            if price > prior_high:
                breakout_vote = 1
            elif price < prior_low:
                breakout_vote = -1
            else:
                breakout_vote = 0
            add_check(
                "breakout",
                f"Donchian breakout ({bp})",
                breakout_vote,
                f"close {price:,.2f} vs {prior_low:,.2f}-{prior_high:,.2f}",
            )

    if "extension" in active:
        threshold = float(cfg["indicators"].get("extension_atr", 2.5))
        dist = (price - ema_mid) / atr_v if atr_v else 0.0
        if dist > threshold:
            extension_vote = -1
        elif dist < -threshold:
            extension_vote = 1
        else:
            extension_vote = 0
        add_check(
            "extension",
            f"Distance from EMA{periods[1]} ({threshold:.1f} ATR)",
            extension_vote,
            f"{dist:+.2f} ATR from EMA{periods[1]}",
        )

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
