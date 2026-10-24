from .base import CHECKS, Check, CheckResult


@CHECKS.register
class RSICheck(Check):
    id = "rsi"

    def evaluate(self, ctx):
        value = ctx.value("rsi")
        if value > 55:
            vote = 1
        elif value < 45:
            vote = -1
        else:
            vote = 0
        return CheckResult(
            id=self.id,
            label="RSI (Relative Strength Index)",
            vote=vote,
            reading=f"RSI {value:.1f}",
        )
