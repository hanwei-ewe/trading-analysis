DEFAULTS = {
    "ema": [20, 50, 200],
    "rsi": 14,
    "macd": [12, 26, 9],
    "bollinger": [20, 2.0],
    "vwap": 20,
    "stoch": [14, 3, 3],
    "adx": 14,
    "obv": 10,
}


def _finding(level, scope, message, hint=""):
    return {"level": level, "scope": scope, "message": message, "hint": hint}


def _err(scope, message, hint=""):
    return _finding("error", scope, message, hint)


def _warn(scope, message, hint=""):
    return _finding("warning", scope, message, hint)


def _tip(scope, message, hint=""):
    return _finding("tip", scope, message, hint)


def review(cfg, timeframe=None, candles=None):
    ind = cfg["indicators"]
    ema = list(ind["ema"])
    es, em, el = int(ema[0]), int(ema[1]), int(ema[2])
    rsi = int(ind["rsi"])
    mf, ms, msig = (int(x) for x in ind["macd"])
    bp, bstd = int(ind["bollinger"][0]), float(ind["bollinger"][1])
    vwap = int(ind.get("vwap", ind["volume_ma"]))
    sk, sd, ss = (int(x) for x in ind.get("stoch", DEFAULTS["stoch"]))
    adx = int(ind.get("adx", DEFAULTS["adx"]))
    obv = int(ind.get("obv", DEFAULTS["obv"]))

    errors = []
    warnings = []
    tips = []

    if not (es < em < el):
        errors.append(
            _err(
                "EMA",
                f"Periods should rise short → mid → long; you have {es}/{em}/{el}.",
                "Try 20/50/200 (or 9/21/50 for faster response).",
            )
        )

    if mf >= ms:
        errors.append(
            _err(
                "MACD",
                f"Fast EMA ({mf}) must be shorter than slow EMA ({ms}).",
                "Conventional is 12/26/9.",
            )
        )
    elif ms >= el:
        warnings.append(
            _warn(
                "MACD",
                f"Slow EMA ({ms}) is not shorter than your long trend EMA ({el}).",
                "MACD is meant to react faster than the trend it confirms.",
            )
        )
    elif ms >= em:
        warnings.append(
            _warn(
                "MACD",
                f"Slow EMA ({ms}) is at or above your mid trend EMA ({em}).",
                "It will lag price momentum; keep MACD below your trend EMAs.",
            )
        )

    if mf == es or ms == em:
        warnings.append(
            _warn(
                "MACD / EMA",
                f"MACD fast/slow ({mf}/{ms}) duplicate your price EMAs ({es}/{em}).",
                "Overlapping periods make the two signals redundant.",
            )
        )

    if rsi < 2:
        errors.append(_err("RSI", f"Period must be at least 2; you have {rsi}."))
    elif rsi > 30:
        warnings.append(
            _warn("RSI", f"Period {rsi} is very slow.", "Typical RSI is 7–21.")
        )
    elif rsi >= el:
        warnings.append(
            _warn(
                "RSI",
                f"Period ({rsi}) is as long as your long EMA ({el}).",
                "Momentum then turns no faster than trend.",
            )
        )
    elif rsi != DEFAULTS["rsi"]:
        tips.append(_tip("RSI", f"Convention is 14; you set {rsi}."))

    if sk < 2 or sd < 1 or ss < 1:
        errors.append(
            _err("Stochastic", "Periods must be ≥2 for %K and ≥1 for %D/smooth.")
        )
    elif sd >= sk:
        warnings.append(
            _warn(
                "Stochastic",
                f"%D ({sd}) should be shorter than %K ({sk}).",
                "Otherwise the signal is over-smoothed.",
            )
        )

    if bp < 2:
        errors.append(_err("Bollinger", f"Period must be ≥2; you have {bp}."))
    if bstd <= 0:
        errors.append(_err("Bollinger", f"Std-dev must be > 0; you have {bstd}."))
    if bp != 20 or abs(bstd - 2.0) > 1e-9:
        tips.append(_tip("Bollinger", f"Convention is 20 / 2σ; you set {bp} / {bstd}."))

    if vwap < 2:
        errors.append(_err("VWAP", f"Window must be ≥2; you have {vwap}."))
    elif vwap != DEFAULTS["vwap"]:
        tips.append(_tip("VWAP", f"Convention is 20; you set {vwap}."))

    if adx < 2:
        errors.append(_err("ADX", f"Period must be ≥2; you have {adx}."))
    elif adx >= el:
        warnings.append(
            _warn(
                "ADX",
                f"Period ({adx}) is as long as your long EMA ({el}).",
                "Trend strength will update very slowly.",
            )
        )
    elif adx != DEFAULTS["adx"]:
        tips.append(_tip("ADX", f"Convention is 14; you set {adx}."))

    if obv < 2:
        errors.append(_err("OBV", f"Lookback must be ≥2; you have {obv}."))

    need = (
        max(
            el,
            ms + msig,
            bp,
            rsi,
            adx,
            sk + sd + ss,
            vwap,
            obv,
        )
        + 5
    )
    if candles and candles < need:
        errors.append(
            _err(
                "History",
                f"These periods need ~{need} candles but only {candles} are "
                f"available on {timeframe}.",
                "Shorten the longest period or use a lower timeframe.",
            )
        )

    findings = errors + warnings + tips
    return {
        "findings": findings,
        "errors": len(errors),
        "warnings": len(warnings),
        "tips": len(tips),
        "ok": not errors,
        "timeframe": timeframe,
        "candles": candles,
        "needed": need,
    }
