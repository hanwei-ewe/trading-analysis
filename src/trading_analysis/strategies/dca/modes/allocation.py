from abc import abstractmethod

from ....core import Registry
from .base import Mode


ALLOCATION_MODES = Registry("DCA allocation mode")


class AllocationMode(Mode):
    @abstractmethod
    def desired(self, equity, initial_capital, weight):
        raise NotImplementedError


@ALLOCATION_MODES.register
class EquityAllocation(AllocationMode):
    id = "equity"
    label = "Equity percentage"
    description = "Allocate a percentage of current trading equity"

    def desired(self, equity, initial_capital, weight):
        return equity * weight


@ALLOCATION_MODES.register
class FixedAllocation(AllocationMode):
    id = "fixed"
    label = "Initial capital percentage"
    description = "Allocate a percentage of the initial capital"

    def desired(self, equity, initial_capital, weight):
        return initial_capital * weight


def get_allocation_mode(mode_id):
    try:
        return ALLOCATION_MODES.get(mode_id)
    except KeyError as err:
        choices = ", ".join(ALLOCATION_MODES.ids())
        raise ValueError(f"allocation_mode must be one of: {choices}") from err
