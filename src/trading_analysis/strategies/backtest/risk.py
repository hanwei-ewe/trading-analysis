from abc import ABC, abstractmethod

from ...core import Registry


class RiskModel(ABC):
    id: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def position_units(
        self,
        equity,
        risk_pct,
        risk_per_unit,
        entry,
        cash_buffer,
        min_notional,
    ):
        raise NotImplementedError


class PercentRiskModel(RiskModel):
    id = "percent"
    label = "Percent risk"
    description = (
        "Risk a fixed percent of equity per trade, capped by available notional."
    )

    def position_units(
        self,
        equity,
        risk_pct,
        risk_per_unit,
        entry,
        cash_buffer,
        min_notional,
    ):
        if equity <= 0 or risk_per_unit <= 0 or entry <= 0:
            return 0.0
        risk_amount = equity * risk_pct / 100.0
        max_notional = equity * (1.0 - cash_buffer)
        units = min(risk_amount / risk_per_unit, max_notional / entry)
        if units * entry < min_notional:
            return 0.0
        return units


RISK_MODELS = Registry[RiskModel]("risk")
RISK_MODELS.register(PercentRiskModel())


def get_risk_model(model_id="percent"):
    try:
        return RISK_MODELS.get(model_id)
    except KeyError as err:
        raise ValueError(f"unknown risk model: {model_id}") from err
