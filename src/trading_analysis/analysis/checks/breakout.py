from .base import CHECKS, Check, CheckResult


@CHECKS.register
class BreakoutCheck(Check):
    id = "breakout"

    def evaluate(self, ctx):
        period = int(ctx.cfg["indicators"].get("breakout", 20))
        if ctx.pos < period:
            return None
        prior_high = float(ctx.ind["high"].iloc[ctx.pos - period:ctx.pos].max())
        prior_low = float(ctx.ind["low"].iloc[ctx.pos - period:ctx.pos].min())
        if ctx.price > prior_high:
            vote = 1
        elif ctx.price < prior_low:
            vote = -1
        else:
            vote = 0
        return CheckResult(
            id=self.id,
            label=f"Donchian breakout ({period})",
            vote=vote,
            reading=f"close {ctx.price:,.2f} vs {prior_low:,.2f}-{prior_high:,.2f}",
        )
