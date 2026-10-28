from abc import abstractmethod

from ....core import Registry
from .base import Mode


TARGET_MODES = Registry("DCA target mode")


class TargetMode(Mode):
    @abstractmethod
    def price(self, fill, reference, atr, profit_target, target_retrace, target_atr):
        raise NotImplementedError


@TARGET_MODES.register
class PercentTarget(TargetMode):
    id = "percent"
    label = "Percentage target"
    description = "Sell at a fixed percentage above the fill"

    def price(self, fill, reference, atr, profit_target, target_retrace, target_atr):
        return fill * (1.0 + float(profit_target))


@TARGET_MODES.register
class RetraceTarget(TargetMode):
    id = "retrace"
    label = "Retracement target"
    description = "Sell at a fraction of the move back to the reference"

    def price(self, fill, reference, atr, profit_target, target_retrace, target_atr):
        if reference > fill:
            return fill + float(target_retrace) * (reference - fill)
        return fill * (1.0 + float(profit_target))


@TARGET_MODES.register
class ATRTarget(TargetMode):
    id = "atr"
    label = "ATR target"
    description = "Sell a fixed number of ATRs above the fill"

    def price(self, fill, reference, atr, profit_target, target_retrace, target_atr):
        if atr > 0:
            return fill + float(target_atr) * atr
        return fill * (1.0 + float(profit_target))


def get_target_mode(mode_id):
    try:
        return TARGET_MODES.get(mode_id)
    except KeyError as err:
        choices = ", ".join(TARGET_MODES.ids())
        raise ValueError(f"target_mode must be one of: {choices}") from err
