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

