import numpy as np

FIXED_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50)


FIB_LEVELS = (0.236, 0.382, 0.500, 0.618, 0.786)


ATR_LEVELS = (3.0, 6.0, 9.0, 12.0, 15.0)


TREND_FIB_LEVELS = (0.236, 0.382, 0.500, 0.618, 0.786)


def _validate(level_mode, levels, allocations):
    if len(levels) != len(allocations):
        raise ValueError("levels and allocations must have the same length")
    if not levels:
        raise ValueError("levels must not be empty")
    if level_mode == "atr":
        if any(level <= 0 for level in levels):
            raise ValueError("ATR level multipliers must be positive")
    else:
        if any(level <= 0 or level >= 1 for level in levels):
            raise ValueError("drop levels must be fractions in (0, 1)")
        if any(b <= a for a, b in zip(levels, levels[1:])):
            raise ValueError("drop levels must be strictly increasing")
    if any(weight <= 0 for weight in allocations):
        raise ValueError("allocations must be positive")
    if sum(allocations) > 1.0 + 1e-9:
        raise ValueError("allocations must sum to <= 1")


def _resolve_levels(level_mode, levels, allocations, level_base):
    if allocations is None:
        n_levels = len(levels) if levels is not None else 5
        allocations = tuple(1.0 / n_levels for _ in range(n_levels))
    else:
        allocations = tuple(float(x) for x in allocations)
    n_levels = len(allocations)

    if levels is not None:
        levels = tuple(float(x) for x in levels)
        return levels, allocations

    if level_mode == "fixed":
        levels = FIXED_LEVELS
    elif level_mode in ("fib", "trend_fib"):
        levels = FIB_LEVELS
    elif level_mode == "atr":
        levels = ATR_LEVELS
    elif level_mode == "geometric":
        levels = tuple(
            1.0 - (1.0 - float(level_base)) ** n for n in range(1, n_levels + 1)
        )
    else:
        raise ValueError("level_mode must be fixed, fib, trend_fib, atr, or geometric")

    if len(levels) != n_levels:
        if level_mode == "geometric":
            levels = tuple(
                1.0 - (1.0 - float(level_base)) ** n
                for n in range(1, n_levels + 1)
            )
        else:
            raise ValueError("levels length must match allocations length")
    return levels, allocations


def _target_price(
    fill, reference, atr, target_mode, profit_target, target_retrace, target_atr
):
    if target_mode == "retrace" and reference > fill:
        target = fill + float(target_retrace) * (reference - fill)
    elif target_mode == "atr" and atr > 0:
        target = fill + float(target_atr) * atr
    else:
        target = fill * (1.0 + float(profit_target))
    return max(target, fill * 1.0001)


def _trend_leg(highs, lows, end, lookback):
    start = max(0, end - lookback)
    window_high = highs[start:end]
    window_low = lows[start:end]
    if len(window_high) < 2:
        return None
    hi = int(np.argmax(window_high))
    lo = int(np.argmin(window_low))
    if lo >= hi:
        return None
    return float(window_high[hi]), float(window_low[lo])

