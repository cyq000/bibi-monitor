"""Integration smoke test for US1: run ingest pipeline end-to-end with synthetic trades.

This script is runnable with `python tests/integration/test_end_to_end_us1.py`.
"""
import asyncio
import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db, get_engine
from src.processor.ingest_pipeline import IngestPipeline
from src import collector
from sqlalchemy.orm import sessionmaker
from src.models import Notification, WindowMetric, Symbol
from datetime import datetime


async def fake_fetch_trades(symbol: str, start_ts_ms: int = None, end_ts_ms: int = None):
    # Create trades to produce total_volume ~= 15000 so *1000 = 15,000,000 which is within threshold
    trades = []
    # produce 6 trades amount=2000 each -> 12000 total
    for i in range(6):
        trades.append({
            "trade_id": f"t{i}",
            "price": 100.0,
            "qty": 20.0,  # amount = 2000
            "is_buyer_maker": False,
            "ts_ms": int(datetime.utcnow().timestamp() * 1000) - i * 1000,
        })
    return trades


async def fake_simulate_trades(self, symbol: str, count: int = 6, interval: float = 0.001):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    # yield 3 trades amount=1000 each -> 3000 total
    for i in range(3):
        yield {
            "trade_id": f"sim-{i}",
            "price": 100.0,
            "qty": 10.0,  # amount = 1000
            "is_buyer_maker": False,
            "ts_ms": now_ms - i * 1000,
        }


def run_test():
    # prepare DB
    init_db()

    # monkeypatch the functions used by ingest_pipeline directly
    import src.processor.ingest_pipeline as ip_mod
    ip_mod.fetch_trades = fake_fetch_trades
    ip_mod.WebSocketClient.simulate_trades = fake_simulate_trades

    # run pipeline
    p = IngestPipeline()
    m = asyncio.run(p.run_cycle('INTEGTEST'))
    print('pipeline metric:', m)

    # verify DB entries
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        sym = session.query(Symbol).filter_by(symbol='INTEGTEST').one_or_none()
        assert sym is not None, 'Symbol record not found'
        wm = session.query(WindowMetric).filter_by(symbol_id=sym.id).order_by(WindowMetric.id.desc()).first()
        assert wm is not None, 'WindowMetric not found'
        notif = session.query(Notification).filter_by(symbol_id=sym.id).order_by(Notification.id.desc()).first()
        assert notif is not None, 'Notification not created'
        assert notif.status in ('pending', 'sent'), f'Unexpected status {notif.status}'
        print('Integration test passed: WindowMetric and Notification created, status=', notif.status)
    finally:
        session.close()


if __name__ == '__main__':
    run_test()
