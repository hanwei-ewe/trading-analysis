from .base import CHECKS, Check, CheckResult


@CHECKS.register
class BollingerCheck(Check):
    id = "bollinger"

    def evaluate(self, ctx):
        upper = ctx.value("bb_upper")
        lower = ctx.value("bb_lower")
        width = ctx.value("bb_width")
        span = upper - lower
        pct_b = (ctx.price - lower) / span if span else 0.5
        if pct_b > 1:
            vote = 1
        elif pct_b < 0:
            vote = -1
        else:
            vote = 0
        return CheckResult(
            id=self.id,
            label="Bollinger Bands (%B)",
            vote=vote,
            reading=f"%B {pct_b:.2f}, width {width / ctx.price * 100.0:.2f}%",
        )
