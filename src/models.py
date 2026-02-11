from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db import Base


class Symbol(Base):
    __tablename__ = "symbol"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(64), unique=True, nullable=False, index=True)
    base_asset = Column(String(32), nullable=True)
    quote_asset = Column(String(32), nullable=True)
    contract_type = Column(String(32), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ingestion_events = relationship("IngestionEvent", back_populates="symbol_obj")
    window_metrics = relationship("WindowMetric", back_populates="symbol_obj")


class IngestionEvent(Base):
    __tablename__ = "ingestion_event"
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbol.id"), index=True)
    trade_id = Column(String(128), nullable=True)
    price = Column(Numeric(28, 12), nullable=True)
    quantity = Column(Numeric(28, 12), nullable=True)
    amount_usdt = Column(Numeric(28, 6), nullable=True)
    is_buyer_maker = Column(Boolean, nullable=True)
    source = Column(String(32), nullable=True)
    exchange_ts = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow)

    symbol_obj = relationship("Symbol", back_populates="ingestion_events")


class WindowMetric(Base):
    __tablename__ = "window_metric"
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbol.id"), index=True)
    window_type = Column(String(16), nullable=False)
    window_start = Column(DateTime, nullable=False, index=True)
    window_end = Column(DateTime, nullable=False)
    buy_taker_volume = Column(Numeric(28, 6), nullable=False, default=0)
    sell_taker_volume = Column(Numeric(28, 6), nullable=False, default=0)
    total_volume = Column(Numeric(28, 6), nullable=False, default=0)
    score_a = Column(Numeric(5, 2), nullable=False, default=0)
    volume_24h_usdt = Column(Numeric(28, 6), nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)

    symbol_obj = relationship("Symbol", back_populates="window_metrics")


class Notification(Base):
    __tablename__ = "notification"
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbol.id"), nullable=True)
    window_metric_id = Column(Integer, ForeignKey("window_metric.id"), nullable=True)
    event_id = Column(String(192), unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=True)
    status = Column(String(32), default="pending")
    attempts = Column(Integer, default=0)
    last_attempted_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    symbol_obj = relationship("Symbol")
