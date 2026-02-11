"""简单采集器（示例）：生成或返回示例交易数据列表。
真实实现应使用 WebSocket + REST 回补，这里提供可运行的本地示例数据。
"""
from typing import List, Dict
import time


def sample_trades(symbol: str) -> List[Dict]:
    """返回示例 trades 列表（每项包含 trade_id, price, qty, is_buyer_maker, ts_ms）。"""
    now_ms = int(time.time() * 1000)
    # 构造一些示例成交：部分为主动买（is_buyer_maker=False），部分为主动卖
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
