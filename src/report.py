def _money(value):
    return "n/a" if value is None else f"{value:,.2f}"


def to_markdown(result):
    symbol = result.get("symbol", "ETH/USDT")
    timeframe = result.get("timeframe", "1h")
    generated = result.get("generated_at", "")
    data_as_of = result.get("data_as_of", "")

    lines = [
        f"## {symbol} — {timeframe} — {generated}",
        "",
        f"**Bias:** {result['bias']}",
        f"**Confidence:** {result['confidence']} (score {result['score']:+d})",
        f"**Price:** {_money(result['price'])}",
        "",
    ]

    signal = result.get("signal")
    if signal:
        lines += [
            "### Proposal",
            f"- Entry zone: {_money(signal['entry_low'])} – {_money(signal['entry_high'])}",
            f"- Stop loss: {_money(signal['stop'])}",
            f"- Targets: T1 {_money(signal['t1'])} | T2 {_money(signal['t2'])}",
            f"- R/R: {signal['rr']:.2f}",
            f"- Invalidation: {signal['invalidation']}",
            "",
        ]
    else:
        lines += [
            "_No actionable proposal (NEUTRAL-FLAT or R/R below the minimum)._",
            "",
        ]

    regime = result["regime"]
    momentum = result["momentum"]
    volatility = result["volatility"]
    levels = result["levels"]
    volume = result["volume"]

    lines += [
        "### Dimensions",
        f"- **Regime:** {regime['state']} "
        f"(EMA {regime['ema_short']:.2f}/{regime['ema_mid']:.2f}/{regime['ema_long']:.2f})",
        f"- **Momentum:** {momentum['state']} "
        f"(RSI {momentum['rsi']:.1f}, MACD hist {momentum['macd_hist']:.2f})",
        f"- **Volatility:** {volatility['state']} "
        f"(ATR {volatility['atr']:.2f}, {volatility['atr_pct']:.2f}%)",
        f"- **Levels:** support {_money(levels['support'])}, "
        f"resistance {_money(levels['resistance'])}, VWAP {_money(levels['vwap'])}",
        f"- **Volume:** {volume['state']} "
        f"({volume['volume']:.0f} vs MA {volume['volume_ma']:.0f})",
        "",
    ]

    ex = result.get("explanations")
    if ex:
        lines += ["### Why this read", ex["confidence"]["text"], ""]
        for check in ex["checks"]:
            lines.append(
                f"- **{check['label']}** ({check['vote']}): {check['reading']} — "
                f"{check['why']} _Changes if: {check['flip']}_"
            )
        lines.append("")
        risk = ex["risk"]
        if risk.get("has_signal"):
            lines += [
                f"**Risk:** {risk['text']}",
                f"**Invalidation:** {risk['invalidation']}",
                "",
            ]
        else:
            lines += [f"**Risk:** {risk['text']}", ""]

    lines += [
        f"**Data as of:** {data_as_of}",
        "",
        "### Assumptions / uncertainties",
    ]
    for item in result.get("assumptions", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
