"""通知器：构建推送负载并发送到飞书（支持重试与回写存储）。

设计：
- 在发送前，调用方应已在 `Notification` 表创建记录（含 `event_id`），以便实现幂等；
- 本模块执行实际 HTTP 发送（可模拟），并在成功后调用 `storage.mark_notification_sent(event_id)`；
- 支持指数退避重试和幂等性检查：若 event_id 已标记为 sent，则跳过重复发送。
"""
from typing import Dict, Optional
import os
import time
import json
from datetime import datetime, timedelta

from src.logging import get_logger
from src.metrics import inc_notifications, inc_errors
from src.storage import storage as storage_adapter

logger = get_logger("notifier")


def build_payload(symbol: str, window: str, buy: float, sell: float, score: float) -> Dict:
    return {
        "title": "币种异常监控通知示例",
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "币安合约监控告警"}},
            "elements": [
                {"tag": "div", "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**币种**：{symbol}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**窗口**：{window}"}}
                ]},
                {"tag": "div", "fields": [
                    {"text": {"tag": "lark_md", "content": f"**买方主动量(USDT)**：{int(buy)}"}},
                    {"text": {"tag": "lark_md", "content": f"**卖方主动量(USDT)**：{int(sell)}"}}
                ]},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"得分A：{score:.2f}。"}]}]
        }
    }


def _do_post(webhook: str, payload: Dict, timeout: int = 8) -> bool:
    try:
        import requests
    except Exception:
        logger.warning("requests not installed; falling back to simulated send")
        return False

    try:
        resp = requests.post(webhook, json=payload, timeout=timeout)
        logger.info("feishu: sent", extra={"status": resp.status_code})
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"feishu send error: {e}")
        return False


def send(payload: Dict, event_id: Optional[str] = None, max_retries: int = 3, base_backoff: float = 1.0) -> bool:
    """Send payload to Feishu with retries and mark notification status on success.

    Idempotency: If event_id is provided and already marked as 'sent', returns True immediately.
    Retries: Uses exponential backoff with optional jitter.
    
    Returns True if send succeeded (or simulated), False otherwise.
    """
    # 幂等性检查：如果已发送过则直接返回成功
    if event_id:
        try:
            session = storage_adapter.get_session()
            from src.models import Notification
            notif = session.query(Notification).filter_by(event_id=event_id).one_or_none()
            session.close()
            if notif and notif.status == "sent":
                logger.info('Notification already sent (idempotent)', extra={"event_id": event_id})
                return True
        except Exception as e:
            logger.warning(f"idempotency check failed: {e}")
    
    send_real = os.getenv('SEND_REAL', '0') == '1'
    webhook = os.getenv('FEISHU_WEBHOOK')

    # If not real sending, just simulate and mark as sent
    if not send_real or not webhook:
        logger.info('Notifier simulated send', extra={"event_id": event_id, "payload_keys": list(payload.keys())})
        if event_id:
            try:
                storage_adapter.mark_notification_sent(event_id)
                inc_notifications(1)
            except Exception as e:
                logger.error(f"failed to mark notification as sent: {e}")
        return True

    # Real send with exponential backoff
    attempt = 0
    while attempt <= max_retries:
        ok = _do_post(webhook, payload)
        if ok:
            logger.info('Notifier real send succeeded', extra={"event_id": event_id, "attempt": attempt})
            inc_notifications(1)
            if event_id:
                try:
                    storage_adapter.mark_notification_sent(event_id)
                except Exception as e:
                    logger.error(f"failed to mark notification as sent: {e}")
            return True

        attempt += 1
        inc_errors(1)
        sleep_for = base_backoff * (2 ** (attempt - 1))
        logger.warning(f"send attempt {attempt} failed, backing off {sleep_for:.1f}s", extra={"event_id": event_id})
        time.sleep(sleep_for)

    logger.error('Notifier failed all attempts', extra={"event_id": event_id, "max_retries": max_retries})
    return False


if __name__ == '__main__':
    p = build_payload('BTCUSDT', '1h', 12345678, 3210000, 79.36)
    send(p, event_id='demo-1')
