"""Binance async collector: WebSocket + REST backfill skeleton.

This module prefers to use `aiohttp`/`websockets` and `ccxt` when available.
If those libraries are not installed, the classes fall back to simulated behavior
so the codebase remains runnable without external deps.

Features:
- `BinanceWSClient` async iterator that yields trade dicts
- `BinanceRESTClient.fetch_trades` async method that returns a list of trades
- basic reconnect/backoff strategy skeleton
"""
import asyncio
import sys
import time
from typing import AsyncIterator, Dict, List, Optional

# Ensure selector event loop on Windows to avoid aiodns/asyncio compatibility errors
if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

try:
    import aiohttp
    HAVE_AIOHTTP = True
except Exception:
    aiohttp = None  # type: ignore
    HAVE_AIOHTTP = False

try:
    import ccxt.async_support as ccxt
    HAVE_CCXT = True
except Exception:
    ccxt = None  # type: ignore
    HAVE_CCXT = False


class BinanceWSClient:
    def __init__(self, symbols: Optional[List[str]] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.symbols = symbols or ["btcusdt"]
        self.loop = loop or asyncio.get_event_loop()
        self._running = False
        # read proxy settings from env (HTTP_PROXY/HTTPS_PROXY)
        import os
        self._proxy = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or None

    async def _connect_and_listen(self) -> AsyncIterator[Dict]:
        """Real implementation would connect to Binance websocket and yield trade events.

        This skeleton tries to use `aiohttp` websocket; if unavailable, falls back to simulation.
        """
        if HAVE_AIOHTTP:
            # Example: wss URL for Binance futures aggregate trade or trade streams
            url = 'wss://fstream.binance.com/ws'
            # pass proxy to ws_connect if provided
            session_kwargs = {}
            if getattr(self, '_proxy', None):
                session_kwargs['trust_env'] = True
            async with aiohttp.ClientSession(**session_kwargs) as session:
                # if proxy present, pass to ws_connect via 'proxy' param
                ws_connect_kwargs = {}
                if getattr(self, '_proxy', None):
                    ws_connect_kwargs['proxy'] = self._proxy
                async with session.ws_connect(url, **ws_connect_kwargs) as ws:
                    # subscription payload should be sent here per Binance API
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            # parse msg.json() and yield trade dicts (left as exercise)
                            try:
                                data = msg.json()
                                # translate to our trade dict format
                                yield {
                                    'trade_id': data.get('t'),
                                    'price': float(data.get('p', 0)),
                                    'qty': float(data.get('q', 0)),
                                    'is_buyer_maker': data.get('m', False),
                                    'ts_ms': int(data.get('T', int(time.time() * 1000)))
                                }
                            except Exception:
                                continue
        else:
            # Fallback: simulated trades
            now_ms = int(time.time() * 1000)
            for i in range(12):
                await asyncio.sleep(0.01)
                yield {
                    'trade_id': f'sim-ws-{now_ms}-{i}',
                    'price': 40000 + (i % 10),
                    'qty': 0.1 + (i % 3) * 0.05,
                    'is_buyer_maker': (i % 4 == 0),
                    'ts_ms': now_ms - i * 1000,
                }

    async def trades(self, symbol: str) -> AsyncIterator[Dict]:
        backoff = 1.0
        while True:
            try:
                async for t in self._connect_and_listen():
                    yield t
                # if stream ends normally, break
                break
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)


class BinanceRESTClient:
    def __init__(self):
        import os
        # build proxies dict for ccxt if environment proxy exists
        proxy = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY') or None
        proxies = None
        if proxy:
            # ensure scheme present
            if proxy.startswith('http://') or proxy.startswith('https://'):
                p = proxy
            else:
                p = 'http://' + proxy
            proxies = {'http': p, 'https': p}

        if HAVE_CCXT:
            # instantiate ccxt binance futures exchange with optional proxies
            params = {'enableRateLimit': True}
            if proxies:
                params['proxies'] = proxies
            # set defaultType to future (Perpetual) by default
            params['options'] = {'defaultType': 'future'}
            try:
                self._exchange = ccxt.binance(params)
            except Exception:
                # fallback to None to allow simulated behavior
                self._exchange = None
        else:
            self._exchange = None

    async def fetch_trades(self, symbol: str, since: Optional[int] = None, limit: int = 500) -> List[Dict]:
        """Fetch trades via REST. Returns list of trade dicts matching websocket shape.

        If `ccxt` is not available, returns simulated trades.
        """
        if HAVE_CCXT and self._exchange:
            try:
                # ccxt async returns awaitable
                # try a few common symbol formats
                candidates = [symbol, symbol.replace('-', '/'), symbol.replace('/', '')]
                raw = None
                for cand in candidates:
                    try:
                        raw = await self._exchange.fetch_trades(cand, since, limit)
                        if raw:
                            break
                    except Exception:
                        raw = None
                        continue
                if raw is None:
                    raise RuntimeError('no trades fetched for any symbol variant')
                out = []
                for r in raw:
                    out.append({
                        'trade_id': r.get('id'),
                        'price': float(r.get('price', 0)),
                        'qty': float(r.get('amount', 0)),
                        'is_buyer_maker': r.get('side') == 'sell',
                        'ts_ms': int(r.get('timestamp', int(time.time() * 1000)))
                    })
                try:
                    # close exchange resources per ccxt async guidance
                    await self._exchange.close()
                except Exception:
                    pass
                return out
            except Exception:
                # on error, fall through to simulated
                pass

        # fallback simulated data
        await asyncio.sleep(0.05)
        now_ms = int(time.time() * 1000)
        trades = []
        for i in range(10):
            trades.append({
                'trade_id': f'sim-rest-{now_ms}-{i}',
                'price': 40000 + i,
                'qty': 0.1 + (i % 3) * 0.05,
                'is_buyer_maker': (i % 2 == 0),
                'ts_ms': now_ms - i * 1000,
            })
        return trades


if __name__ == '__main__':
    import asyncio

    async def d():
        ws = BinanceWSClient()
        async for t in ws.trades('BTCUSDT'):
            print('WS', t)
            break
        rest = BinanceRESTClient()
        r = await rest.fetch_trades('BTCUSDT')
        print('REST count', len(r))

    asyncio.run(d())
