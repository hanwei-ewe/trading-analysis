from .base import CHECKS, Check, CheckResult


@CHECKS.register
class EMAPositionCheck(Check):
    id = "ema_position"

    def evaluate(self, ctx):
        mid = ctx.periods[1]
        vote = 1 if ctx.price > ctx.ema_mid else -1
        return CheckResult(
            id=self.id,
            label=f"Price vs EMA{mid}",
            vote=vote,
            reading=(
                f"price {ctx.price:,.2f} is "
                f"{'above' if ctx.price > ctx.ema_mid else 'below'} "
                f"EMA{mid} {ctx.ema_mid:,.2f}"
            ),
        )
