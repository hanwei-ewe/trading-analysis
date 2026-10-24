from ...indicators import stochastic
from .base import CHECKS, Check, CheckResult


@CHECKS.register
class StochasticCheck(Check):
    id = "stoch"

    def evaluate(self, ctx):
        k_period, d_period, smooth = [
            int(value) for value in ctx.cfg["indicators"].get("stoch", [14, 3, 3])
        ]
        if "stoch_k" in ctx.ind.columns and "stoch_d" in ctx.ind.columns:
            k = ctx.value("stoch_k")
            d = ctx.value("stoch_d")
        else:
            k = d = float("nan")
            if len(ctx.ind) > max(k_period, d_period, smooth):
                values = stochastic(
                    ctx.ind["high"],
                    ctx.ind["low"],
                    ctx.ind["close"],
                    k_period,
                    d_period,
                    smooth,
                )
                k = float(values["stoch_k"].iloc[ctx.pos])
                d = float(values["stoch_d"].iloc[ctx.pos])
        if k != k or d != d:
            return None
        return CheckResult(
            id=self.id,
            label=f"Stochastic ({k_period},{d_period},{smooth})",
            vote=1 if k > d else -1,
            reading=f"%K {k:.1f} vs %D {d:.1f}",
        )
