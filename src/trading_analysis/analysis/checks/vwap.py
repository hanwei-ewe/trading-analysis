from .base import CHECKS, Check, CheckResult


@CHECKS.register
class VWAPCheck(Check):
    id = "vwap"

    def evaluate(self, ctx):
        value = ctx.value("vwap")
        return CheckResult(
            id=self.id,
            label="Price vs VWAP (Volume-Weighted Avg Price)",
            vote=1 if ctx.price > value else -1,
            reading=f"price {ctx.price:,.2f} vs VWAP {value:,.2f}",
        )
