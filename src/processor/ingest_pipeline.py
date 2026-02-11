"""Ingest pipeline：协调 websocket 模拟、REST 回补、窗口聚合、持久化与通知（最小实现）。
"""
import asyncio
from typing import List
from src.collector.websocket_client import WebSocketClient
from src.collector.rest_backfill import fetch_trades
from src.processor.windowing import aggregate_trades
from src.storage import storage as storage_adapter
from datetime import datetime, timedelta
from src.notifier import build_payload, send
from src.config_manager import ConfigManager


class IngestPipeline:
    def __init__(self, storage=None, config_manager=None):
        self.storage = storage or storage_adapter
        self.ws = WebSocketClient()
        self.config = config_manager or ConfigManager()

    async def run_cycle(self, symbol: str):
        """Run one ingest cycle: backfill + consume a short websocket simulation, aggregate and persist."""
        # 1) Backfill: fetch historical trades (simulated)
        rest_trades = await fetch_trades(symbol)

        # 2) Simulate a short live stream and collect
        live_trades = []
        async for t in self.ws.simulate_trades(symbol, count=6, interval=0.001):
            live_trades.append(t)

        # merge trades for aggregation
        combined = rest_trades + live_trades

        # 3) aggregate
        metric = aggregate_trades(combined)

        # 4) persist WindowMetric using SQLAlchemy-backed storage
        window_end = datetime.utcnow()
        window_start = window_end - timedelta(hours=1)
        wm = self.storage.store_window_metric(
            symbol=symbol,
            window_type='1h',
            window_start=window_start,
            window_end=window_end,
            buy_taker_volume=metric.get('buy_taker_volume'),
            sell_taker_volume=metric.get('sell_taker_volume'),
            total_volume=metric.get('total_volume'),
            score_a=metric.get('score_a'),
            volume_24h_usdt=metric.get('total_volume') * 1000,
        )

        # 5) decide notify: use configurable thresholds
        volume_24h = metric['total_volume'] * 1000
        threshold = self.config.get_threshold_for_symbol(symbol)
        
        if (threshold.volume_min <= volume_24h <= threshold.volume_max 
            and metric['score_a'] >= threshold.score_threshold):
            event_id = f"{symbol}-{window_start.isoformat()}-1h"
            payload = build_payload(symbol, '1h', metric['buy_taker_volume'], metric['sell_taker_volume'], metric['score_a'])
            created = self.storage.create_notification(symbol, wm.id if wm is not None else None, event_id, payload)
            if created:
                ok = send(payload, event_id)
                if ok:
                    self.storage.mark_notification_sent(event_id)

        return metric


async def demo():
    p = IngestPipeline()
    m = await p.run_cycle('BTCUSDT')
    print('INGEST RESULT:', m)


if __name__ == '__main__':
    asyncio.run(demo())
