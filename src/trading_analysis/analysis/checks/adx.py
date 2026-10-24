from ...indicators import adx
from .base import CHECKS, Check, CheckResult


@CHECKS.register
class ADXCheck(Check):
    id = "adx"

    def evaluate(self, ctx):
        period = int(ctx.cfg["indicators"].get("adx", 14))
        if "adx" in ctx.ind.columns and "plus_di" in ctx.ind.columns:
            value = ctx.value("adx")
            plus_di = ctx.value("plus_di")
            minus_di = ctx.value("minus_di")
        else:
            value = plus_di = minus_di = float("nan")
            if len(ctx.ind) > period + 1:
                values = adx(
                    ctx.ind["high"], ctx.ind["low"], ctx.ind["close"], period
                )
                value = float(values["adx"].iloc[ctx.pos])
                plus_di = float(values["plus_di"].iloc[ctx.pos])
                minus_di = float(values["minus_di"].iloc[ctx.pos])
        if value != value:
            return None
        vote = 0 if value < 20 else (1 if plus_di > minus_di else -1)
        return CheckResult(
            id=self.id,
            label=f"ADX (Average Directional Index) / DI ({period})",
            vote=vote,
            reading=f"ADX {value:.1f}, +DI {plus_di:.1f}, -DI {minus_di:.1f}",
        )
