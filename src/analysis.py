from . import indicators as ind_mod
from .indicators import add_indicators


def _swing_points(df, lookback):
    high = df["high"]
    low = df["low"]
    window = 2 * lookback + 1
    roll_max = high.rolling(window, center=True).max()
    roll_min = low.rolling(window, center=True).min()
    return high[high >= roll_max], low[low <= roll_min]


def _nearest_above(levels, price):
    candidates = levels[levels > price]
    return float(candidates.min()) if len(candidates) else None


def _nearest_below(levels, price):
    candidates = levels[levels < price]
    return float(candidates.max()) if len(candidates) else None


def _build_signal(direction, price, atr_v, support, resistance, cfg, timeframe="1h"):
    min_rr = float(cfg["risk"]["min_rr"])

    if direction == "LONG":
        anchor = max(support, price - 0.5 * atr_v)
        entry_low = anchor - 0.25 * atr_v
        entry_high = anchor + 0.25 * atr_v
        stop = min(support, entry_low) - atr_v
        mid = (entry_low + entry_high) / 2.0
        risk = mid - stop
        t1 = mid + 2.0 * risk
        t2 = mid + 3.0 * risk
        invalidation = f"{timeframe} close below {stop:,.2f}"
    else:
        anchor = min(resistance, price + 0.5 * atr_v)
        entry_low = anchor - 0.25 * atr_v
        entry_high = anchor + 0.25 * atr_v
        stop = max(resistance, entry_high) + atr_v
        mid = (entry_low + entry_high) / 2.0
        risk = stop - mid
        t1 = mid - 2.0 * risk
        t2 = mid - 3.0 * risk
        invalidation = f"{timeframe} close above {stop:,.2f}"

    if risk <= 0:
        return None

    rr = abs(t1 - mid) / risk
    if rr < min_rr:
        return None

    return {
        "direction": direction,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "rr": rr,
        "invalidation": invalidation,
    }


def analyze(df, cfg, ind=None, active=None, timeframe=None):
    if ind is None:
        ind = add_indicators(df, cfg)
    tf = timeframe or cfg["timeframes"]["primary"]
    min_history = int(cfg["indicators"]["ema"][-1]) + 5
    if len(ind) < min_history:
        raise ValueError(f"need >= {min_history} candles, got {len(ind)}")

    last = ind.iloc[-1]
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

    swing_highs, swing_lows = _swing_points(ind, cfg["swings"]["lookback"])
    resistance = _nearest_above(swing_highs, price)
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
        if len(ind) > max(kp, dp, sp):
            s = ind_mod.stochastic(ind["high"], ind["low"], ind["close"], kp, dp, sp)
            k = float(s["stoch_k"].iloc[-1])
            d = float(s["stoch_d"].iloc[-1])
            add_check(
                "stoch",
                f"Stochastic ({kp},{dp},{sp})",
                1 if k > d else -1,
                f"%K {k:.1f} vs %D {d:.1f}",
            )

    if "adx" in active:
        ap = int(cfg["indicators"].get("adx", 14))
        if len(ind) > ap + 1:
            a = ind_mod.adx(ind["high"], ind["low"], ind["close"], ap)
            adx_v = float(a["adx"].iloc[-1])
            pdi = float(a["plus_di"].iloc[-1])
            mdi = float(a["minus_di"].iloc[-1])
            adx_vote = 0 if adx_v < 20 else (1 if pdi > mdi else -1)
            add_check(
                "adx",
                f"ADX (Average Directional Index) / DI ({ap})",
                adx_vote,
                f"ADX {adx_v:.1f}, +DI {pdi:.1f}, -DI {mdi:.1f}",
            )

    if "obv" in active:
        obl = int(cfg["indicators"].get("obv", 10))
        if len(ind) > obl + 1:
            o = ind_mod.obv(ind["close"], ind["volume"])
            rising = float(o.iloc[-1]) > float(o.iloc[-1 - obl])
            add_check(
                "obv",
                f"OBV (On-Balance Volume, {obl})",
                1 if rising else -1,
                f"{'rising' if rising else 'falling'} over the last {obl} bars",
            )

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
