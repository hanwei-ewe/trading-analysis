from abc import ABC, abstractmethod

from ...core import Registry


class ExecutionModel(ABC):
    id: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def fill(self, raw, side, slippage, entering):
        raise NotImplementedError

    @abstractmethod
    def limit_fill(self, side, limit, bar_open, bar_high, bar_low):
        raise NotImplementedError

    @abstractmethod
    def exit_check(self, position, bar_open, bar_high, bar_low, target_ok=True):
        raise NotImplementedError


class DefaultExecution(ExecutionModel):
    id = "default"
    label = "Default execution"
    description = (
        "Next-open fills with slippage, intrabar limit fills, and stop-first exits."
    )

    def fill(self, raw, side, slippage, entering):
        if entering:
            return raw * (1.0 + slippage) if side == "LONG" else raw * (1.0 - slippage)
        return raw * (1.0 - slippage) if side == "LONG" else raw * (1.0 + slippage)

    def limit_fill(self, side, limit, bar_open, bar_high, bar_low):
        if side == "LONG":
            if bar_low <= limit:
                return min(bar_open, limit)
        else:
            if bar_high >= limit:
                return max(bar_open, limit)
        return None

    def exit_check(self, position, bar_open, bar_high, bar_low, target_ok=True):
        side = position["side"]
        stop = position["stop"]
        target = position["target"]
        if side == "LONG":
            if bar_open <= stop:
                return bar_open, "stop"
            if bar_low <= stop:
                return stop, "stop"
            if target_ok:
                if bar_open >= target:
                    return bar_open, "target"
                if bar_high >= target:
                    return target, "target"
        else:
            if bar_open >= stop:
                return bar_open, "stop"
            if bar_high >= stop:
                return stop, "stop"
            if target_ok:
                if bar_open <= target:
                    return bar_open, "target"
                if bar_low <= target:
                    return target, "target"
        return None, None


DEFAULT_EXECUTION = DefaultExecution()

EXECUTION_MODELS = Registry[ExecutionModel]("execution")
EXECUTION_MODELS.register(DEFAULT_EXECUTION)


def get_execution_model(model_id="default"):
    try:
        return EXECUTION_MODELS.get(model_id)
    except KeyError as err:
        raise ValueError(f"unknown execution model: {model_id}") from err
