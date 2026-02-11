#!/usr/bin/env python3
"""示例运行脚本：读取环境变量，计算得分 A，并打印飞书卡片 JSON（模拟发送）。
无需外部依赖，直接使用 Python 标准库。
"""
import os
import json
import datetime

def get_env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return float(default)

SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
BUY = get_env_float('BUY_TAKER_USDT', '12345678')
SELL = get_env_float('SELL_TAKER_USDT', '3210000')
WINDOW = os.getenv('WINDOW', '1h')
WINDOW_START = os.getenv('WINDOW_START', datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0).isoformat() + 'Z')

def compute_score(buy, sell):
    denom = buy + sell + 1e-9
    return 100.0 * buy / denom

def build_feishu_card(symbol, window, window_start, buy, sell, score):
    return {
        "title": "币种异常监控通知示例",
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
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
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"得分A：{score:.2f} — 模拟发送（未向飞书推送）。"}]}]
        }
    }

def main():
    score = compute_score(BUY, SELL)
    payload = build_feishu_card(SYMBOL, WINDOW, WINDOW_START, BUY, SELL, score)

    print('--- Monitor Example Run ---')
    print(f'SYMBOL={SYMBOL} WINDOW={WINDOW} WINDOW_START={WINDOW_START}')
    print(f'BUY_TAKER_USDT={int(BUY)} SELL_TAKER_USDT={int(SELL)}')
    print(f'Computed score A: {score:.2f}\n')

    print('Feishu Card Payload (JSON):')
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
