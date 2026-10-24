from .. import indicators as ind

GLOSSARY = {
    "ema": {
        "name": "EMA — Exponential Moving Average",
        "meaning": (
            "An average of recent prices that weights the newest candles more, "
            "so it hugs price more closely than a plain average."
        ),
        "usage": (
            "We plot EMA 20/50/200. Stacked in order (20 above 50 above 200) the "
            "trend is up; reversed, it is down. Price above EMA50 is a basic "
            "bullish tell."
        ),
        "pitfall": (
            "Averages lag — they confirm a move already underway rather than "
            "predict a new one."
        ),
    },
    "vwap": {
        "name": "VWAP — Volume-Weighted Average Price",
        "meaning": (
            "The average price over the window weighted by how much volume traded "
            "at each price — a proxy for the price buyers and sellers actually "
            "transacted at."
        ),
        "usage": (
            "Price above VWAP means buyers are paying up (bullish); below means "
            "sellers dominate."
        ),
        "pitfall": (
            "VWAP depends on the window you choose; a short window reacts fast and "
            "can look noisy."
        ),
    },
    "rsi": {
        "name": "RSI — Relative Strength Index",
        "meaning": (
            "A 0–100 gauge comparing the size of recent gains against recent "
            "losses."
        ),
        "usage": (
            "Above 55 = up-momentum, below 45 = down-momentum; above 70 is often "
            "called 'overbought', below 30 'oversold'."
        ),
        "pitfall": (
            "In a strong trend RSI can stay overbought/oversold for a long time — "
            "it is not a standalone buy/sell trigger."
        ),
    },
    "macd": {
        "name": "MACD — Moving Average Convergence Divergence",
        "meaning": (
            "The gap between a fast EMA and a slow EMA. A 'signal' line smooths "
            "it, and the histogram is the difference between the two."
        ),
        "usage": (
            "A positive/rising histogram means upward momentum is strengthening; a "
            "negative/falling one means it is fading."
        ),
        "pitfall": (
            "MACD lags and can whipsaw in choppy, range-bound markets."
        ),
    },
    "atr": {
        "name": "ATR — Average True Range",
        "meaning": (
            "The average size of a candle's full range — how much price typically "
            "moves per bar."
        ),
        "usage": (
            "We size stops with ATR: one ATR beyond a level gives the trade room to "
            "breathe without being arbitrary."
        ),
        "pitfall": (
            "ATR rises in volatile conditions, so stops widen — position size "
            "should shrink to compensate."
        ),
    },
    "bollinger": {
        "name": "Bollinger Bands",
        "meaning": (
            "A moving average with bands drawn ±2 standard deviations above and "
            "below it, showing price relative to its own recent volatility."
        ),
        "usage": (
            "Bands squeeze when volatility is low and expand when it is high; "
            "touches show stretched moves."
        ),
        "pitfall": (
            "A band touch is not automatically a reversal — in trends price can "
            "'ride the band'."
        ),
    },
    "stochastic": {
        "name": "Stochastic Oscillator",
        "meaning": (
            "Measures where the close sits within the recent high–low range, on a "
            "0–100 scale."
        ),
        "usage": (
            "Above 80 means the close is near the top of its range (strong, often "
            "called overbought); below 20 near the bottom (weak, oversold)."
        ),
        "pitfall": (
            "Like RSI it can stay pinned in a strong trend — read it with trend and "
            "level context."
        ),
    },
    "adx": {
        "name": "ADX — Average Directional Index",
        "meaning": (
            "Measures trend strength (not direction) on a 0–100 scale; +DI/−DI show "
            "which side is stronger."
        ),
        "usage": (
            "ADX above ~25 signals a real trend, below ~20 a choppy range. +DI above "
            "−DI favors bulls."
        ),
        "pitfall": (
            "ADX tells you strength, not direction — read it alongside the DI lines."
        ),
    },
    "obv": {
        "name": "OBV — On-Balance Volume",
        "meaning": (
            "A running total that adds volume on up-closes and subtracts it on "
            "down-closes, approximating cumulative buying vs selling pressure."
        ),
        "usage": (
            "OBV rising with price confirms buying pressure; diverging from price "
            "hints the move is not backed by volume."
        ),
        "pitfall": (
            "Volume can be distorted by exchange quirks — treat OBV as confirmation, "
            "not a trigger."
        ),
    },
}

CHECK_TEXT = {
    "regime": {
        "meaning": (
            "When the short, medium and long EMAs are stacked in order, the market "
            "is trending."
        ),
        "why": (
            "Stacked averages mean buyers (or sellers) have controlled the short, "
            "medium and long term at once — the strongest trend signature."
        ),
        "rule": (
            "EMA20 > EMA50 > EMA200 (+1) · EMA20 < EMA50 < EMA200 (−1) · "
            "otherwise 0."
        ),
        "flip": "The vote flips if the averages unstack, e.g. EMA20 crossing EMA50.",
    },
    "ema_position": {
        "meaning": "Whether price trades above or below the medium-term average.",
        "why": (
            "Price above the medium EMA is the simplest evidence of an up-bias; "
            "below is a down-bias."
        ),
        "rule": "Price > EMA50 (+1) · Price < EMA50 (−1).",
        "flip": "A close the other side of EMA50 flips this vote.",
    },
    "rsi": {
        "meaning": (
            "RSI measures recent momentum on a 0–100 scale; above 50 is up, below "
            "50 is down."
        ),
        "why": (
            "Readings above 55 show buyers are pushing price up; below 45 shows "
            "sellers in control."
        ),
        "rule": "RSI > 55 (+1) · RSI < 45 (−1) · 45–55 (0).",
        "flip": (
            "RSI drifting back into 45–55 removes the vote; crossing 45 would flip "
            "it bearish."
        ),
    },
    "macd": {
        "meaning": (
            "MACD tracks the gap between a fast and slow EMA; its histogram (MACD "
            "minus signal) shows momentum accelerating or fading."
        ),
        "why": (
            "A positive histogram means upward momentum is strengthening; negative "
            "means downward momentum dominates."
        ),
        "rule": "Histogram > 0 (+1) · Histogram < 0 (−1).",
        "flip": "The histogram crossing zero flips the vote.",
    },
    "vwap": {
        "meaning": (
            "VWAP is the volume-weighted average price over the window — where most "
            "volume actually traded."
        ),
        "why": (
            "Trading above VWAP suggests buyers are paying up (bullish); below "
            "suggests sellers dominate."
        ),
        "rule": "Price > VWAP (+1) · Price < VWAP (−1).",
        "flip": "A close the other side of VWAP flips the vote.",
    },
    "stoch": {
        "meaning": (
            "Stochastic measures where the close sits within its recent high–low "
            "range, on a 0–100 scale."
        ),
        "why": (
            "%K crossing above %D shows short-term buyers taking control; below "
            "shows sellers."
        ),
        "rule": "%K > %D (+1) · %K < %D (−1).",
        "flip": "A %K/%D crossover the other way flips the vote.",
    },
    "adx": {
        "meaning": (
            "ADX measures trend strength (not direction); +DI / −DI show which side "
            "is stronger."
        ),
        "why": (
            "When ADX is meaningful (≥20) we take direction from whichever DI line "
            "is on top."
        ),
        "rule": "ADX < 20 (0) · else +DI > −DI (+1) · −DI > +DI (−1).",
        "flip": "The DI lines crossing, or ADX falling below 20, changes the vote.",
    },
    "obv": {
        "meaning": (
            "OBV (On-Balance Volume) adds volume on up-closes and subtracts it on "
            "down-closes, tracking cumulative buying vs selling pressure."
        ),
        "why": (
            "OBV rising over the window means up-moves are backed by volume "
            "(bullish); falling means they are not."
        ),
        "rule": "OBV higher than the window ago (+1) · lower (−1).",
        "flip": "OBV turning the other way over the window flips the vote.",
    },
    "bollinger": {
        "meaning": (
            "Bollinger Bands draw a moving average with bands ±2 standard "
            "deviations above/below it; %B shows where price sits within the bands "
            "(0 = lower band, 1 = upper band)."
        ),
        "why": (
            "Closing above the upper band signals a strong upward push (momentum "
            "continuation); closing below the lower band signals a strong downward "
            "push."
        ),
        "rule": "%B > 1 (+1) · %B < 0 (−1) · otherwise 0.",
        "flip": "Price moving back inside the bands removes the vote.",
    },
    "htf": {
        "meaning": (
            "The higher-timeframe read checks whether the bigger trend agrees with "
            "your chosen timeframe."
        ),
        "why": (
            "A signal that lines up with the higher timeframe is far more reliable; "
            "fighting the bigger trend is a common way to get whipsawed."
        ),
        "rule": (
            "Higher frame bias LONG (+1) · SHORT (−1) · NEUTRAL (0); an opposing "
            "higher frame caps confidence at Medium."
        ),
        "flip": "The higher timeframe flipping its bias changes this vote.",
    },
}

_VOTE_WORD = {1: "bullish", -1: "bearish", 0: "neutral"}


def _confidence(result):
    checks = result.get("checks", [])
    total = len(checks)
    bull = sum(1 for c in checks if c["weight"] > 0)
    bear = sum(1 for c in checks if c["weight"] < 0)
    neutral = total - bull - bear
    score = result["score"]
    label = result["confidence"]

    if score > 0:
        text = (
            f"{bull} of {total} checks voted bullish and {bear} bearish "
            f"({neutral} neutral). Net score {score:+d} of {total} -> {label} "
            f"confidence."
        )
    elif score < 0:
        text = (
            f"{bear} of {total} checks voted bearish and {bull} bullish "
            f"({neutral} neutral). Net score {score:+d} of {total} -> {label} "
            f"confidence."
        )
    else:
        text = (
            f"The checks are balanced ({bull} bullish, {bear} bearish, "
            f"{neutral} neutral). Net score 0 -> no directional bias."
        )

    return {
        "label": label,
        "score": score,
        "max_score": total,
        "bullish": bull,
        "bearish": bear,
        "neutral": neutral,
        "text": text,
        "note": (
            "A trade is only proposed when a clear majority (at least 60%) of the "
            "enabled checks agree AND the net score is 2 or more; 80% agreement with "
            "a score of 3+ is High confidence."
        ),
    }


def _risk(result, cfg):
    signal = result.get("signal")
    atr_v = result["volatility"]["atr"]
    min_rr = float(cfg["risk"]["min_rr"])

    if not signal:
        return {
            "has_signal": False,
            "text": (
                "No trade is proposed, so there is nothing to risk right now. A "
                "setup only appears when a clear majority of the enabled checks "
                "agree AND the stop/target geometry offers the minimum "
                "reward-to-risk."
            ),
            "invalidation": None,
        }

    direction = signal["direction"]
    side = "below" if direction == "LONG" else "above"
    text = (
        f"For this {direction}, the stop sits {side} the nearest swing level by "
        f"about one ATR ({atr_v:,.2f}) at {signal['stop']:,.2f} — far enough to "
        f"survive normal noise, but a genuine break of structure invalidates it. "
        f"Entering around {signal['entry_low']:,.2f}–{signal['entry_high']:,.2f} "
        f"with the first target at {signal['t1']:,.2f} gives roughly "
        f"{signal['rr']:.1f}:1 reward-to-risk (minimum accepted {min_rr:.1f}:1)."
    )
    return {
        "has_signal": True,
        "direction": direction,
        "stop": signal["stop"],
        "rr": signal["rr"],
        "text": text,
        "invalidation": signal["invalidation"],
    }


_ROLE = {
    "regime": "trend",
    "ema_position": "trend",
    "adx": "trend",
    "rsi": "momentum",
    "macd": "momentum",
    "stoch": "momentum",
    "vwap": "volume",
    "obv": "volume",
    "bollinger": "volatility",
}


def _readings(checks, ind_df, selected, params=None):
    readings = []
    for c in checks:
        readings.append(
            {
                "key": c["id"],
                "name": c["label"],
                "role": _ROLE.get(
                    c["id"], "trend" if c["id"].startswith("htf_") else "other"
                ),
                "lean": _VOTE_WORD.get(c["weight"], "neutral"),
                "reading": c["reading"],
            }
        )

    if ind_df is None or not selected:
        return readings

    have = {r["key"] for r in readings}
    stoch = (params or {}).get("stoch") or [14, 3, 3]
    adx_period = (params or {}).get("adx") or 14

    if "stoch" in selected and "stoch" not in have and len(ind_df) > max(int(stoch[0]), int(stoch[2]), int(stoch[1])):
        s = ind.stochastic(
            ind_df["high"], ind_df["low"], ind_df["close"],
            int(stoch[0]), int(stoch[1]), int(stoch[2]),
        )
        k = float(s["stoch_k"].iloc[-1])
        d = float(s["stoch_d"].iloc[-1])
        if k >= 80:
            note = (
                "The close is near the top of its range (often called overbought) — "
                "in a trend this can persist."
            )
        elif k <= 20:
            note = (
                "The close is near the bottom of its range (oversold) — in a trend "
                "this can persist."
            )
        else:
            note = "Measures where the close sits within its recent range."
        readings.append(
            {
                "key": "stoch",
                "name": f"Stochastic ({stoch[0]},{stoch[1]},{stoch[2]})",
                "role": "momentum",
                "lean": "bullish" if k > d else "bearish",
                "reading": f"%K {k:.1f} vs %D {d:.1f}",
                "note": note,
            }
        )

    if "adx" in selected and "adx" not in have and len(ind_df) > int(adx_period) + 1:
        a = ind.adx(
            ind_df["high"], ind_df["low"], ind_df["close"], int(adx_period)
        )
        adx_v = float(a["adx"].iloc[-1])
        pdi = float(a["plus_di"].iloc[-1])
        mdi = float(a["minus_di"].iloc[-1])
        readings.append(
            {
                "key": "adx",
                "name": f"ADX / DI ({adx_period})",
                "role": "trend",
                "lean": "bullish" if pdi > mdi else "bearish",
                "reading": f"ADX {adx_v:.1f}, +DI {pdi:.1f}, -DI {mdi:.1f}",
                "note": "ADX measures trend strength; +DI vs -DI shows which side is winning.",
            }
        )

    obl = int((params or {}).get("obv") or 10)
    if "obv" in selected and "obv" not in have and len(ind_df) > obl + 1:
        o = ind.obv(ind_df["close"], ind_df["volume"])
        rising = float(o.iloc[-1]) > float(o.iloc[-1 - obl])
        readings.append(
            {
                "key": "obv",
                "name": f"OBV ({obl})",
                "role": "volume",
                "lean": "bullish" if rising else "bearish",
                "reading": f"{'rising' if rising else 'falling'} over the last {obl} bars",
                "note": "OBV confirms whether price moves are backed by volume.",
            }
        )

    return readings


def _context(ind_df, result, params=None):
    vol = result["volatility"]
    atr_pct = float(vol["atr_pct"])
    adx_period = (params or {}).get("adx") or 14

    adx_v = pdi = mdi = None
    if ind_df is not None and len(ind_df) > int(adx_period) + 1:
        a = ind.adx(
            ind_df["high"], ind_df["low"], ind_df["close"], int(adx_period)
        )
        adx_v = float(a["adx"].iloc[-1])
        pdi = float(a["plus_di"].iloc[-1])
        mdi = float(a["minus_di"].iloc[-1])

    if adx_v is None:
        state = result["regime"]["state"]
        strength_text = f"The EMA structure reads '{state}'."
        direction = (
            "up" if "up" in state else ("down" if "down" in state else "flat")
        )
    else:
        if adx_v >= 25:
            state = "strong-trend"
            strength_text = f"ADX {adx_v:.0f} shows a strong, established trend."
        elif adx_v >= 20:
            state = "developing-trend"
            strength_text = f"ADX {adx_v:.0f} shows a trend that is developing."
        else:
            state = "ranging"
            strength_text = (
                f"ADX {adx_v:.0f} shows weak trend strength — the market is "
                f"choppy/ranging."
            )
        direction = "up" if pdi > mdi else ("down" if mdi > pdi else "flat")

    trending = state in ("strong-trend", "developing-trend")
    if trending:
        guidance = (
            "In a trend, direction tools (EMA, ADX/DI) carry the most information; "
            "momentum oscillators can stay pinned, so use them to time entries, not "
            "to call reversals."
        )
    else:
        guidance = (
            "In a range, mean-reversion tools (RSI, Stochastic, Bollinger Bands) are "
            "more informative than EMA crossovers, which whipsaw."
        )

    if atr_pct >= 3.0:
        vol_text = (
            f"Volatility is high (ATR {atr_pct:.2f}% of price): use wider stops and "
            f"smaller size."
        )
    elif atr_pct <= 1.0:
        vol_text = (
            f"Volatility is low (ATR {atr_pct:.2f}% of price): moves are small, and a "
            f"squeeze often precedes expansion."
        )
    else:
        vol_text = f"Volatility is normal (ATR {atr_pct:.2f}% of price)."

    return {
        "trend": {
            "state": state,
            "direction": direction,
            "adx": adx_v,
            "plus_di": pdi,
            "minus_di": mdi,
            "text": strength_text,
        },
        "volatility": {"state": vol["state"], "atr_pct": atr_pct, "text": vol_text},
        "trending": trending,
        "summary": f"{strength_text} {vol_text} {guidance}",
    }


def _focus(readings, context):
    trending = context["trending"]
    items = []
    for r in readings:
        role = r["role"]
        if role == "trend":
            rel = "High" if trending else "Low"
            reason = (
                "A real trend is present, so trend tools are the primary guide."
                if trending
                else "Little trend strength, so crossovers whipsaw — use for bias only."
            )
        elif role == "momentum":
            rel = "High" if not trending else "Medium"
            reason = (
                "In a range, oscillators flag swing extremes (buy low / sell high)."
                if not trending
                else "In a trend, momentum times entries rather than calling reversals."
            )
        elif role == "volume":
            rel = "Medium"
            reason = "Confirms whether moves are backed by real participation."
        elif role == "volatility":
            rel = "Medium"
            reason = (
                "Frames how stretched price is — helps size risk and flags band "
                "breaks."
            )
        else:
            rel = "Medium"
            reason = ""
        items.append(
            {
                "name": r["name"],
                "lean": r["lean"],
                "relevance": rel,
                "reason": reason,
                "reading": r["reading"],
            }
        )
    order = {"High": 0, "Medium": 1, "Low": 2}
    items.sort(key=lambda x: order.get(x["relevance"], 3))
    return items


def _majority(readings, role):
    group = [r for r in readings if r["role"] == role]
    bull = sum(1 for r in group if r["lean"] == "bullish")
    bear = sum(1 for r in group if r["lean"] == "bearish")
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def _comparison(readings):
    bull = sum(1 for r in readings if r["lean"] == "bullish")
    bear = sum(1 for r in readings if r["lean"] == "bearish")
    neutral = len(readings) - bull - bear

    trend = _majority(readings, "trend")
    momentum = _majority(readings, "momentum")
    volume = _majority(readings, "volume")

    notes = []
    if trend != "neutral" and momentum != "neutral":
        if trend == momentum:
            notes.append(
                f"Trend and momentum both lean {trend} — this agreement (confluence) "
                f"is the strongest kind of setup."
            )
        else:
            notes.append(
                f"Trend leans {trend} while momentum leans {momentum}. They disagree, "
                f"which usually means a pullback against the trend or a range — wait "
                f"for them to align before trusting a signal."
            )
    if volume != "neutral" and trend != "neutral":
        if volume == trend:
            notes.append(f"Volume tools lean {volume}: they confirm the price trend.")
        else:
            notes.append(
                f"Volume leans {volume} while the price trend leans {trend} — "
                f"divergence like this is a caution flag."
            )

    return {
        "bullish": bull,
        "bearish": bear,
        "neutral": neutral,
        "groups": {"trend": trend, "momentum": momentum, "volume": volume},
        "text": (
            f"Of the indicators selected, {bull} lean bullish, {bear} bearish and "
            f"{neutral} neutral."
        ),
        "notes": notes,
        "complement": (
            "They play different roles: trend indicators (EMA, ADX/DI) set direction, "
            "momentum (RSI, MACD, Stochastic) times entries, volatility (ATR, "
            "Bollinger) sizes risk, and volume (VWAP, OBV) confirms participation."
        ),
    }


def explain(result, cfg, ind_df=None, selected=None, params=None):
    checks = []
    for c in result.get("checks", []):
        info = CHECK_TEXT.get(c["id"])
        if info is None:
            info = CHECK_TEXT.get("htf", {}) if c["id"].startswith("htf_") else {}
        checks.append(
            {
                "id": c["id"],
                "label": c["label"],
                "vote": _VOTE_WORD.get(c["weight"], "neutral"),
                "weight": c["weight"],
                "reading": c["reading"],
                "meaning": info.get("meaning", ""),
                "why": info.get("why", ""),
                "rule": info.get("rule", ""),
                "flip": info.get("flip", ""),
            }
        )

    readings = _readings(result.get("checks", []), ind_df, selected or [], params)
    context = _context(ind_df, result, params)

    return {
        "confidence": _confidence(result),
        "checks": checks,
        "readings": readings,
        "context": context,
        "focus": _focus(readings, context),
        "comparison": _comparison(readings),
        "risk": _risk(result, cfg),
        "glossary": [{"key": key, **entry} for key, entry in GLOSSARY.items()],
    }
