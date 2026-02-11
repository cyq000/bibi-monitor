"""处理器：窗口聚合与得分计算（示例实现）。
"""
from typing import List, Dict, Tuple
import datetime


def aggregate_window(trades: List[Dict]) -> Dict:
    """按给定 trades 列表计算 buy_taker_volume (USDT)、sell_taker_volume (USDT)、total_volume 与 score A."""
    buy_usdt = 0.0
    sell_usdt = 0.0
    total = 0.0

    for t in trades:
        amount = float(t["price"]) * float(t["qty"])  # USDT 等价
        total += amount
        if t.get("is_buyer_maker"):
            # is_buyer_maker True: maker is buyer → taker is seller (主动卖)
            sell_usdt += amount
        else:
            # taker is buyer (主动买)
            buy_usdt += amount

    denom = buy_usdt + sell_usdt + 1e-9
    score_a = 100.0 * buy_usdt / denom if denom else 0.0

    return {
        "buy_taker_volume": buy_usdt,
        "sell_taker_volume": sell_usdt,
        "total_volume": total,
        "score_a": score_a,
        "computed_at": datetime.datetime.utcnow().isoformat() + 'Z'
    }


if __name__ == '__main__':
    from collector import sample_trades
    print(aggregate_window(sample_trades('BTCUSDT')))
