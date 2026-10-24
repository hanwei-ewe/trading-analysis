from ...indicators import obv
from .base import CHECKS, Check, CheckResult


@CHECKS.register
class OBVCheck(Check):
    id = "obv"

    def evaluate(self, ctx):
        lookback = int(ctx.cfg["indicators"].get("obv", 10))
        if "obv" in ctx.ind.columns:
            series = ctx.ind["obv"]
            valid = ctx.pos - lookback >= 0
            rising = (
                valid
                and float(series.iloc[ctx.pos]) > float(series.iloc[ctx.pos - lookback])
            )
        else:
            valid = len(ctx.ind) > lookback + 1
            rising = False
            if valid:
                series = obv(ctx.ind["close"], ctx.ind["volume"])
                rising = (
                    float(series.iloc[ctx.pos])
                    > float(series.iloc[ctx.pos - lookback])
                )
        if not valid:
            return None
        return CheckResult(
            id=self.id,
            label=f"OBV (On-Balance Volume, {lookback})",
            vote=1 if rising else -1,
            reading=f"{'rising' if rising else 'falling'} over the last {lookback} bars",
        )
