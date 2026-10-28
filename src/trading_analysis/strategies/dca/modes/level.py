import math
from abc import abstractmethod

from ....core import Registry
from .base import Mode


FIXED_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50)
FIB_LEVELS = (0.236, 0.382, 0.500, 0.618, 0.786)
ATR_LEVELS = (3.0, 6.0, 9.0, 12.0, 15.0)
TREND_FIB_LEVELS = (0.236, 0.382, 0.500, 0.618, 0.786)


LEVEL_MODES = Registry("DCA level mode")


class LevelMode(Mode):
    uses_atr = False

    @abstractmethod
    def default_levels(self, n_levels, level_base):
        raise NotImplementedError

    def validate(self, levels):
        if self.uses_atr:
            if any(level <= 0 for level in levels):
                raise ValueError("ATR level multipliers must be positive")
            return
        if any(level <= 0 or level >= 1 for level in levels):
            raise ValueError("drop levels must be fractions in (0, 1)")
        if any(b <= a for a, b in zip(levels, levels[1:])):
            raise ValueError("drop levels must be strictly increasing")

    def prices(self, levels, reference, atr, leg):
        if not math.isfinite(reference) or reference <= 0:
            return None, reference
        return [reference * (1.0 - level) for level in levels], reference


@LEVEL_MODES.register
class FixedLevels(LevelMode):
    id = "fixed"
    label = "Fixed percentages"
    description = "Fixed percentage drops from the reference price"

    def default_levels(self, n_levels, level_base):
        return FIXED_LEVELS


@LEVEL_MODES.register
class FibonacciLevels(LevelMode):
    id = "fib"
    label = "Fibonacci retracements"
    description = "Fibonacci retracement levels from the reference price"

    def default_levels(self, n_levels, level_base):
        return FIB_LEVELS


@LEVEL_MODES.register
class TrendFibonacciLevels(LevelMode):
    id = "trend_fib"
    label = "Trend-leg Fibonacci"
    description = "Fibonacci levels measured from the current swing leg"

    def default_levels(self, n_levels, level_base):
        return TREND_FIB_LEVELS

    def prices(self, levels, reference, atr, leg):
        if leg is None:
            return None, reference
        leg_high, leg_low = leg
        if leg_high <= leg_low:
            return None, reference
        return [
            leg_high - level * (leg_high - leg_low) for level in levels
        ], leg_high


@LEVEL_MODES.register
class ATRLevels(LevelMode):
    id = "atr"
    label = "ATR multiples"
    description = "Levels offset from the reference by ATR multiples"
    uses_atr = True

    def default_levels(self, n_levels, level_base):
        return ATR_LEVELS

    def prices(self, levels, reference, atr, leg):
        if not math.isfinite(reference) or reference <= 0:
            return None, reference
        if not math.isfinite(atr) or atr <= 0:
            return None, reference
        return [reference - level * atr for level in levels], reference


@LEVEL_MODES.register
class GeometricLevels(LevelMode):
    id = "geometric"
    label = "Geometric drops"
    description = "Compounding percentage drops from the reference price"

    def default_levels(self, n_levels, level_base):
        return tuple(
            1.0 - (1.0 - float(level_base)) ** n
            for n in range(1, n_levels + 1)
        )


def get_level_mode(mode_id):
    try:
        return LEVEL_MODES.get(mode_id)
    except KeyError as err:
        choices = ", ".join(LEVEL_MODES.ids())
        raise ValueError(f"level_mode must be one of: {choices}") from err
