"""异步 REST 回补模块（模拟）。
真实实现可使用 `ccxt` 或 `aiohttp` 请求币安 REST 接口拉取历史 trades/kline 数据。
此处提供 `fetch_trades()` 的 async stub，返回与 websocket 相同格式的 trade dict 列表。
"""
import asyncio
import time
from typing import List, Dict


async def fetch_trades(symbol: str, start_ts_ms: int = None, end_ts_ms: int = None) -> List[Dict]:
    """模拟异步从 REST 拉取交易数据（按时间范围）。

    Returns a list of trade dicts.
    """
    # In real impl, respect rate limits and paginate
    await asyncio.sleep(0.05)
    now_ms = int(time.time() * 1000)
    trades = []
    for i in range(8):
        trades.append({
            "trade_id": f"rest-{symbol}-{now_ms}-{i}",
            "price": 40050 + i,
            "qty": 0.2 + (i % 2) * 0.1,
            "is_buyer_maker": (i % 3 == 0),
            "ts_ms": now_ms - i * 1000,
        })
    return trades


if __name__ == '__main__':
    import asyncio
    async def d():
        x = await fetch_trades('BTCUSDT')
        print(x)
    asyncio.run(d())
