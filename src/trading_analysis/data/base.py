from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from ..core import Registry


@runtime_checkable
class ExchangeAdapter(Protocol):
    market_type: str

    def fetch_ohlcv(self, symbol, timeframe, limit=500, since=None, retries=4):
        ...

    def fetch_ticker(self, symbol):
        ...

    def load_markets(self, reload=False):
        ...


@dataclass(frozen=True)
class ExchangePlugin:
    id: str
    label: str
    description: str
    factory: Callable[..., ExchangeAdapter]


EXCHANGES = Registry[ExchangePlugin]("exchange")
