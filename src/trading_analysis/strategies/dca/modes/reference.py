from abc import abstractmethod

import pandas as pd

from ....core import Registry
from .base import Mode


REFERENCE_MODES = Registry("DCA reference mode")


class ReferenceMode(Mode):
    @abstractmethod
    def series(self, high, lookback):
        raise NotImplementedError


@REFERENCE_MODES.register
class AnchorReference(ReferenceMode):
    id = "anchor"
    label = "Fixed anchor"
    description = "Use the highest high in the initial lookback window"

    def series(self, high, lookback):
        anchor = float(high.iloc[:lookback].max())
        return pd.Series(anchor, index=high.index)


@REFERENCE_MODES.register
class RollingReference(ReferenceMode):
    id = "rolling"
    label = "Rolling high"
    description = "Use the highest high over the trailing lookback window"

    def series(self, high, lookback):
        return high.shift(1).rolling(lookback).max()


@REFERENCE_MODES.register
class ATHReference(ReferenceMode):
    id = "ath"
    label = "All-time high"
    description = "Use the running all-time high"

    def series(self, high, lookback):
        return high.shift(1).cummax()


def get_reference_mode(mode_id):
    try:
        return REFERENCE_MODES.get(mode_id)
    except KeyError as err:
        choices = ", ".join(REFERENCE_MODES.ids())
        raise ValueError(f"reference_mode must be one of: {choices}") from err
