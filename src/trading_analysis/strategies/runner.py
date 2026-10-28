from .base import STRATEGIES


def run_strategy(strategy_id, frame=None, **params):
    try:
        strategy = STRATEGIES.get(strategy_id)
    except KeyError as err:
        raise ValueError(f"unknown strategy: {strategy_id}") from err
    return strategy.run(frame, **params)
