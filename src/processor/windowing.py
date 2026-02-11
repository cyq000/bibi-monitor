"""窗口聚合和得分计算（异步/同步皆可）。
提供 `aggregate_trades` 与 `compute_score_a` 两个函数用于管线调用。
"""
from typing import List, Dict


def compute_score_a(buy_usdt: float, sell_usdt: float) -> float:
    denom = buy_usdt + sell_usdt + 1e-9
    return 100.0 * buy_usdt / denom if denom else 0.0


def aggregate_trades(trades: List[Dict]) -> Dict:
    """Aggregate trades into buy/sell volumes (USDT) and compute score.

    trades expected to have keys: price, qty, is_buyer_maker
    """
    buy = 0.0
    sell = 0.0
    total = 0.0
    for t in trades:
        amount = float(t.get('price', 0.0)) * float(t.get('qty', 0.0))
        total += amount
        if t.get('is_buyer_maker'):
            # maker is buyer -> taker is seller -> active sell
            sell += amount
        else:
            buy += amount

    score = compute_score_a(buy, sell)
    return {
        'buy_taker_volume': buy,
        'sell_taker_volume': sell,
        'total_volume': total,
        'score_a': score,
    }


if __name__ == '__main__':
    from src.collector.rest_backfill import fetch_trades
    import asyncio

    async def demo():
        t = await fetch_trades('BTCUSDT')
        print(aggregate_trades(t))

    asyncio.run(demo())
