from .base import CHECKS, Check, CheckResult


@CHECKS.register
class ExtensionCheck(Check):
    id = "extension"

    def evaluate(self, ctx):
        threshold = float(ctx.cfg["indicators"].get("extension_atr", 2.5))
        atr_value = ctx.value("atr")
        distance = (ctx.price - ctx.ema_mid) / atr_value if atr_value else 0.0
        if distance > threshold:
            vote = -1
        elif distance < -threshold:
            vote = 1
        else:
            vote = 0
        mid = ctx.periods[1]
        return CheckResult(
            id=self.id,
            label=f"Distance from EMA{mid} ({threshold:.1f} ATR)",
            vote=vote,
            reading=f"{distance:+.2f} ATR from EMA{mid}",
        )
