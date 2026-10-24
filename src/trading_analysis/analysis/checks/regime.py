from .base import CHECKS, Check, CheckResult


@CHECKS.register
class RegimeCheck(Check):
    id = "regime"

    def evaluate(self, ctx):
        if ctx.regime == "trending-up":
            vote = 1
        elif ctx.regime == "trending-down":
            vote = -1
        else:
            vote = 0
        short, mid, long = ctx.periods
        return CheckResult(
            id=self.id,
            label=f"Trend structure (EMA {short}/{mid}/{long})",
            vote=vote,
            reading=(
                f"EMA{short} {ctx.ema_short:,.2f}, EMA{mid} {ctx.ema_mid:,.2f}, "
                f"EMA{long} {ctx.ema_long:,.2f} -> {ctx.regime}"
            ),
        )
