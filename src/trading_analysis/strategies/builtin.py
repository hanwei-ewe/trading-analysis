from .backtest import run_backtest
from .base import STRATEGIES, Strategy
from .dca import run_dca


@STRATEGIES.register
class TrendStrategy(Strategy):
    id = "trend"
    label = "Trend confluence"
    description = "Long-only trend strategy driven by confluence checks"

    def run(self, frame, **params):
        return run_backtest(df=frame, **params)


@STRATEGIES.register
class DCAStrategy(Strategy):
    id = "dca"
    label = "DCA ladder"
    description = "Spot-only ladder accumulation strategy"

    def run(self, frame, **params):
        return run_dca(frame, **params)
