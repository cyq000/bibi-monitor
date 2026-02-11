"""Storage adapter using SQLAlchemy models defined in `src.models`.
"""
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.db import get_engine
from src.models import Symbol, WindowMetric, Notification
from typing import Optional
import json


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Storage:
    def __init__(self):
        self.engine = engine

    def get_session(self):
        return SessionLocal()

    def get_or_create_symbol(self, symbol: str, base_asset: Optional[str] = None, quote_asset: Optional[str] = None, contract_type: Optional[str] = None):
        session = self.get_session()
        try:
            obj = session.query(Symbol).filter_by(symbol=symbol).one_or_none()
            if obj:
                return obj
            obj = Symbol(symbol=symbol, base_asset=base_asset, quote_asset=quote_asset, contract_type=contract_type)
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj
        finally:
            session.close()

    def store_window_metric(self, symbol: str, window_type: str, window_start: datetime, window_end: datetime, buy_taker_volume, sell_taker_volume, total_volume, score_a, volume_24h_usdt=None):
        session = self.get_session()
        try:
            sym = self.get_or_create_symbol(symbol)
            wm = WindowMetric(
                symbol_id=sym.id,
                window_type=window_type,
                window_start=window_start,
                window_end=window_end,
                buy_taker_volume=buy_taker_volume,
                sell_taker_volume=sell_taker_volume,
                total_volume=total_volume,
                score_a=score_a,
                volume_24h_usdt=volume_24h_usdt,
                computed_at=datetime.utcnow(),
            )
            session.add(wm)
            session.commit()
            session.refresh(wm)
            return wm
        finally:
            session.close()

    def create_notification(self, symbol: str, window_metric_id: int, event_id: str, payload: dict):
        session = self.get_session()
        try:
            sym = self.get_or_create_symbol(symbol)
            n = Notification(
                symbol_id=sym.id,
                window_metric_id=window_metric_id,
                event_id=event_id,
                payload=json.dumps(payload, ensure_ascii=False),
                status="pending",
                attempts=0,
            )
            session.add(n)
            session.commit()
            session.refresh(n)
            return n
        except IntegrityError:
            session.rollback()
            return None
        finally:
            session.close()

    def mark_notification_sent(self, event_id: str):
        session = self.get_session()
        try:
            n = session.query(Notification).filter_by(event_id=event_id).one_or_none()
            if not n:
                return False
            n.status = "sent"
            n.attempts = (n.attempts or 0) + 1
            n.last_attempted_at = datetime.utcnow()
            n.sent_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            session.close()


storage = Storage()


if __name__ == "__main__":
    print("Storage module loaded. Run scripts/init_db.py before using.")
