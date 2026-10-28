import logging
import time

import ccxt

from .base import EXCHANGES, ExchangePlugin

log = logging.getLogger(__name__)

RETRYABLE = (
    ccxt.NetworkError,
    ccxt.ExchangeNotAvailable,
    ccxt.RequestTimeout,
    ccxt.DDoSProtection,
    ccxt.RateLimitExceeded,
)


class ExchangeError(RuntimeError):
    pass


class BinanceAdapter:
    id = "binance"
    label = "Binance"
    description = "CCXT-backed Binance spot and futures market data adapter."

    def __init__(self, market_type="spot", enable_rate_limit=True, timeout=15000):
        self.market_type = market_type
        self._client = ccxt.binance(
            {
                "enableRateLimit": enable_rate_limit,
                "timeout": timeout,
                "options": {"defaultType": market_type},
            }
        )

    @property
    def client(self):
        return self._client

    def fetch_ohlcv(self, symbol, timeframe, limit=500, since=None, retries=4):
        delay = 1.0
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                return self._client.fetch_ohlcv(
                    symbol, timeframe=timeframe, since=since, limit=limit
                )
            except RETRYABLE as err:
                last_err = err
                log.warning(
                    "fetch_ohlcv %s %s failed (attempt %s/%s): %s",
                    symbol,
                    timeframe,
                    attempt,
                    retries,
                    err,
                )
                time.sleep(delay)
                delay *= 2
            except ccxt.ExchangeError as err:
                raise ExchangeError(str(err)) from err
        raise ExchangeError(f"fetch_ohlcv failed after {retries} attempts: {last_err}")

    def fetch_ticker(self, symbol):
        return self._client.fetch_ticker(symbol)

    def load_markets(self, reload=False):
        return self._client.load_markets(reload)


EXCHANGES.register(
    ExchangePlugin(
        id=BinanceAdapter.id,
        label=BinanceAdapter.label,
        description=BinanceAdapter.description,
        factory=BinanceAdapter,
    )
)

_CLIENTS = {}


def get_adapter(
    market_type="spot",
    enable_rate_limit=True,
    timeout=15000,
    exchange_id="binance",
):
    try:
        plugin = EXCHANGES.get(exchange_id)
    except KeyError as err:
        raise ExchangeError(f"unsupported exchange: {exchange_id}") from err
    key = (exchange_id, market_type, enable_rate_limit, timeout)
    adapter = _CLIENTS.get(key)
    if adapter is None:
        adapter = plugin.factory(
            market_type=market_type,
            enable_rate_limit=enable_rate_limit,
            timeout=timeout,
        )
        _CLIENTS[key] = adapter
    return adapter
