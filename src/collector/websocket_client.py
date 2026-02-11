"""异步 WebSocket 客户端（模拟实现）。
真实实现应使用 `websockets` 或 `aiohttp` 连接币安合约交易流并产出 trade 事件。
此模块提供一个模拟器：`WebSocketClient.simulate_trades()`，用于演示与本地测试。
"""
import asyncio
import time
from typing import AsyncIterator, Dict


class WebSocketClient:
    def __init__(self, symbols=None):
        self.symbols = symbols or ["BTCUSDT"]
        self._running = False

    async def connect(self):
        """Async context manager stub for connection lifecycle."""
        self._running = True
        try:
            yield self
        finally:
            self._running = False

    async def simulate_trades(self, symbol: str, count: int = 10, interval: float = 0.01) -> AsyncIterator[Dict]:
        """Simulate an async stream of trade dicts for `symbol`.

        Each trade has: trade_id, price, qty, is_buyer_maker, ts_ms
        """
        now_ms = int(time.time() * 1000)
        for i in range(count):
            trade = {
                "trade_id": f"sim-{symbol}-{now_ms}-{i}",
                "price": 40000 + (i % 10),
                "qty": 0.1 + (i % 3) * 0.05,
                # alternate maker/buyer to produce buy/sell mix
                "is_buyer_maker": (i % 4 == 0),
                "ts_ms": now_ms - i * 1000,
            }
            await asyncio.sleep(interval)
            yield trade


async def demo():
    client = WebSocketClient()
    async for t in client.simulate_trades('BTCUSDT', count=5, interval=0.001):
        print('sim-trade', t)


if __name__ == '__main__':
    import asyncio
    asyncio.run(demo())
