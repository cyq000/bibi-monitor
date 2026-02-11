from dataclasses import dataclass
import os
import json

try:
    # optional dependency
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class Settings:
    BINANCE_API_KEY: str | None = None
    BINANCE_API_SECRET: str | None = None
    FEISHU_WEBHOOK: str | None = None
    HTTP_PROXY: str | None = None
    HTTPS_PROXY: str | None = None
    DB_URL: str = "sqlite:///./monitor.db"
    LOG_LEVEL: str = "INFO"


def _load() -> Settings:
    return Settings(
        BINANCE_API_KEY=os.environ.get("BINANCE_API_KEY"),
        BINANCE_API_SECRET=os.environ.get("BINANCE_API_SECRET"),
        FEISHU_WEBHOOK=os.environ.get("FEISHU_WEBHOOK"),
        HTTP_PROXY=os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
        HTTPS_PROXY=os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
        DB_URL=os.environ.get("DB_URL", "sqlite:///./monitor.db"),
        LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),
    )


settings = _load()


def as_dict() -> dict:
    return json.loads(json.dumps(settings, default=lambda o: o.__dict__))


if __name__ == "__main__":
    # quick test
    print(json.dumps(as_dict(), indent=2, ensure_ascii=False))