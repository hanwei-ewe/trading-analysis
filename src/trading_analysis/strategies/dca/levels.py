import numpy as np

from .modes import (
    ATR_LEVELS,
    FIB_LEVELS,
    FIXED_LEVELS,
    TREND_FIB_LEVELS,
    get_level_mode,
    get_target_mode,
)


def _validate(level_mode, levels, allocations):
    if len(levels) != len(allocations):
        raise ValueError("levels and allocations must have the same length")
    if not levels:
        raise ValueError("levels must not be empty")
    get_level_mode(level_mode).validate(levels)
    if any(weight <= 0 for weight in allocations):
        raise ValueError("allocations must be positive")
    if sum(allocations) > 1.0 + 1e-9:
        raise ValueError("allocations must sum to <= 1")


def _resolve_levels(level_mode, levels, allocations, level_base):
    mode = get_level_mode(level_mode)
    if allocations is None:
        n_levels = len(levels) if levels is not None else 5
        allocations = tuple(1.0 / n_levels for _ in range(n_levels))
    else:
        allocations = tuple(float(x) for x in allocations)
    n_levels = len(allocations)

    if levels is not None:
        levels = tuple(float(x) for x in levels)
        return levels, allocations

    levels = mode.default_levels(n_levels, level_base)
    if len(levels) != n_levels:
        raise ValueError("levels length must match allocations length")
    return levels, allocations


def _target_price(
    fill, reference, atr, target_mode, profit_target, target_retrace, target_atr
):
    target = get_target_mode(target_mode).price(
        fill,
        reference,
        atr,
        profit_target,
        target_retrace,
        target_atr,
    )
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
