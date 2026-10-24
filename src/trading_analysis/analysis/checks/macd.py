from .base import CHECKS, Check, CheckResult


@CHECKS.register
class MACDCheck(Check):
    id = "macd"

    def evaluate(self, ctx):
        hist = ctx.value("macd_hist")
        return CheckResult(
            id=self.id,
            label="MACD histogram (Moving Avg Convergence Divergence)",
            vote=1 if hist > 0 else -1,
            reading=f"histogram {hist:+.3f}",
        )
