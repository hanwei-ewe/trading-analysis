from .base import CHECKS, Check, CheckResult


@CHECKS.register
class PriceActionCheck(Check):
    id = "pa"

    def evaluate(self, ctx):
        prev = ctx.ind.iloc[ctx.pos - 1]
        row = ctx.row
        open_ = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        prev_open = float(prev["open"])
        prev_close = float(prev["close"])
        body = max(abs(close - open_), 1e-12)
        bull_engulf = close > open_ and prev_close < prev_open and close >= prev_open and open_ <= prev_close
        bear_engulf = close < open_ and prev_close > prev_open and close <= prev_open and open_ >= prev_close
        lower_wick = min(open_, close) - low
        upper_wick = high - max(open_, close)
        bull_pin = lower_wick > 2.0 * body and lower_wick > upper_wick
        bear_pin = upper_wick > 2.0 * body and upper_wick > lower_wick
        if bull_engulf or bull_pin:
            vote = 1
        elif bear_engulf or bear_pin:
            vote = -1
        else:
            vote = 0
        return CheckResult(
            id=self.id,
            label="Price action (engulfing/pin bar)",
            vote=vote,
            reading=(
                f"{'bullish' if vote > 0 else 'bearish' if vote < 0 else 'none'}"
                f" candle, body {body:.2f}, wicks {lower_wick:.2f}/{upper_wick:.2f}"
            ),
        )
