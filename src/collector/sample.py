"""Collector sample utilities (sample trades) moved into package."""
from typing import List, Dict
import time


def sample_trades(symbol: str) -> List[Dict]:
    """返回示例 trades 列表（每项包含 trade_id, price, qty, is_buyer_maker, ts_ms）。"""
    now_ms = int(time.time() * 1000)
    return [
        {"trade_id": f"t{i}", "price": 40000 + i, "qty": 0.3 + 0.1 * i, "is_buyer_maker": False, "ts_ms": now_ms - i * 1000}
        for i in range(1, 6)
    ] + [
        {"trade_id": f"s{i}", "price": 40010 + i, "qty": 0.2 + 0.05 * i, "is_buyer_maker": True, "ts_ms": now_ms - (i + 6) * 1000}
        for i in range(1, 4)
    ]


if __name__ == '__main__':
    import json
    print(json.dumps(sample_trades('BTCUSDT'), indent=2))
