import asyncio
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db, get_engine
from sqlalchemy.orm import sessionmaker
from src.models import Notification, WindowMetric, Symbol
# IngestPipeline will be imported inside test to ensure modules are reloaded after fixture
from datetime import datetime


async def fake_fetch_trades(symbol: str, start_ts_ms: int = None, end_ts_ms: int = None):
    trades = []
    for i in range(6):
        trades.append({
            "trade_id": f"t{i}",
            "price": 100.0,
            "qty": 20.0,
            "is_buyer_maker": False,
            "ts_ms": int(datetime.utcnow().timestamp() * 1000) - i * 1000,
        })
    return trades


async def fake_simulate_trades(self, symbol: str, count: int = 6, interval: float = 0.001):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    for i in range(3):
        yield {
            "trade_id": f"sim-{i}",
            "price": 100.0,
            "qty": 10.0,
            "is_buyer_maker": False,
            "ts_ms": now_ms - i * 1000,
        }


@pytest.fixture(autouse=True)
def prepare_db(tmp_path):
    # set DB to a temporary sqlite file to avoid affecting local DB
    db_file = tmp_path / "test_monitor.db"
    os.environ['DB_URL'] = f"sqlite:///{db_file}"
    # reload config and db modules so they pick up the new DB_URL
    import importlib
    import src.config as cfg
    import src.db as dbmod
    import src.models as modelsmod
    import src.storage as storagemod
    importlib.reload(cfg)
    importlib.reload(dbmod)
    importlib.reload(modelsmod)
    importlib.reload(storagemod)
    dbmod.init_db()
    yield


def test_end_to_end_creates_notification():
    # monkeypatch collector modules used by ingest_pipeline
    import src.collector.rest_backfill as rest_mod
    import src.collector.websocket_client as ws_mod

    rest_mod.fetch_trades = fake_fetch_trades
    ws_mod.WebSocketClient.simulate_trades = fake_simulate_trades

    import importlib
    ip_mod = importlib.import_module('src.processor.ingest_pipeline')
    importlib.reload(ip_mod)
    p = ip_mod.IngestPipeline()
    metric = asyncio.run(p.run_cycle('PYTESTUSDT'))

    assert metric['total_volume'] > 0

    # verify DB entries
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        sym = session.query(Symbol).filter_by(symbol='PYTESTUSDT').one_or_none()
        assert sym is not None, 'Symbol record not found'
        wm = session.query(WindowMetric).filter_by(symbol_id=sym.id).order_by(WindowMetric.id.desc()).first()
        assert wm is not None, 'WindowMetric not found'
        notifs = session.query(Notification).filter_by(symbol_id=sym.id).order_by(Notification.id.desc()).all()
        # debug output if no notifications
        if not notifs:
            print('DEBUG: No notifications found for symbol', sym.symbol)
            alln = session.query(Notification).all()
            print('DEBUG: All notifications in DB:', [ (n.id, n.event_id, n.status) for n in alln ])
        notif = notifs[0] if notifs else None
        assert notif is not None, 'Notification not created'
        assert notif.status in ('pending', 'sent')
    finally:
        session.close()
