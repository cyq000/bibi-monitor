"""简单运行器：示例管线，使用 collector->processor->storage->notifier 完成一次计算并可能发送通知。
"""
import os
import datetime
from src.collector import sample_trades
# load aggregate_window from src/processor.py (file) to avoid package/module name collision
from src.processor import aggregate_window
from src.storage import storage as storage_adapter
from src.notifier import build_payload, send
from src.logging import get_logger
from src.config import settings

logger = get_logger("cli", settings.LOG_LEVEL)


def run_once(symbol: str = 'BTCUSDT', window_type: str = '1h'):
    trades = sample_trades(symbol)
    metric = aggregate_window(trades)

    # 这里我们使用 total_volume 作为近 24h 成交额的占位符（示例）
    volume_24h = metric['total_volume'] * 1000  # 放大以满足阈值示例

    storage = storage_adapter
    window_end = datetime.datetime.utcnow()
    window_start = window_end.replace(minute=0, second=0, microsecond=0)
    wm = storage.store_window_metric(
        symbol=symbol,
        window_type=window_type,
        window_start=window_start,
        window_end=window_end,
        buy_taker_volume=metric['buy_taker_volume'],
        sell_taker_volume=metric['sell_taker_volume'],
        total_volume=metric['total_volume'],
        score_a=metric['score_a'],
        volume_24h_usdt=metric['total_volume'] * 1000,
    )

    # 阈值：24h 成交额在 10M ~ 80M USDT
    if 10_000_000 <= volume_24h <= 80_000_000:
        score = metric['score_a']
        # 示例阈值：score_a > 50
        if score > 50:
            event_id = f"{symbol}-{window_start}-{window_type}"
            payload = build_payload(symbol, window_type, metric['buy_taker_volume'], metric['sell_taker_volume'], score)
            # 幂等：create notification record; storage.create_notification 返回 None 表示已存在
            created = storage.create_notification(symbol, wm.id if wm is not None else None, event_id, payload)
            if created:
                ok = send(payload, event_id)
                if ok:
                    storage.mark_notification_sent(event_id)
                    logger.info('Notification sent and recorded.', extra={"event_id": event_id, "symbol": symbol})
                else:
                    print('Notification failed to send; will retry per retry policy (not implemented in demo).')
            else:
                print('Notification already exists (idempotent).')
        else:
            print(f'Score {score:.2f} below alert threshold; no notification.')
    else:
        print(f'Volume {volume_24h:.0f} outside [10M,80M]; skipping notification.')


def main():
    sym = os.getenv('SYMBOL', 'BTCUSDT')
    run_once(sym, os.getenv('WINDOW', '1h'))


if __name__ == '__main__':
    main()
