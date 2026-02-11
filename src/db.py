from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import Engine
from typing import Generator
from src.config import settings


DATABASE_URL = settings.DB_URL


def get_engine() -> Engine:
    return create_engine(DATABASE_URL, echo=False, future=True)


EngineLocal = None


def get_session() -> Generator:
    global EngineLocal
    if EngineLocal is None:
        EngineLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    db = EngineLocal()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()


def init_db() -> None:
    """Create database tables for all registered models (noop if none)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print(f"Initializing DB at {DATABASE_URL}")
    init_db()
