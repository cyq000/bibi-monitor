#!/usr/bin/env python3
"""
演示脚本: US1 飞书通知完整流程

执行步骤：
1. 初始化数据库
2. 注入合成交易数据
3. 执行窗口聚合计算得分
4. 创建通知记录
5. 构建飞书卡片
6. 发送通知（模拟模式展示，支持实际发送）

运行方式：
  python -m scripts.feishu_demo
  或
  SEND_REAL=1 FEISHU_WEBHOOK=<your_webhook_url> python -m scripts.feishu_demo
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

# Add repo to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db
from src.storage import storage
from src.processor.windowing import aggregate_trades
from src.notifier import build_payload, send
from src.logging import get_logger

logger = get_logger(__name__)


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_success(msg):
    """Print success message"""
    print(f"✅ {msg}")


def print_info(msg):
    """Print info message"""
    print(f"ℹ️  {msg}")


def print_data(label, data):
    """Print formatted data"""
    print(f"\n{label}:")
    if isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)


async def demo_feishu_notification():
    """Demonstrate complete Feishu notification flow"""

    print_section("币安合约监控 - 飞书通知演示")

    # Step 1: Initialize DB
    print_section("Step 1: 初始化数据库")
    init_db()
    print_success("数据库初始化完成")

    # Step 2: Create synthetic trade data
    print_section("Step 2: 注入合成交易数据")
    symbol = "BTCUSDT"
    
    # High buy volume scenario - generate data that creates 30M USDT volume
    synthetic_trades = [
        # Buy trades (high volume)
        {"symbol": symbol, "side": "buy", "qty": 0.5, "price": 45000, "time": 1000},  # 22.5k
        {"symbol": symbol, "side": "buy", "qty": 0.4, "price": 45000, "time": 2000},  # 18k
        {"symbol": symbol, "side": "buy", "qty": 0.35, "price": 45000, "time": 3000},  # 15.75k
        # Sell trades (lower volume)
        {"symbol": symbol, "side": "sell", "qty": 0.2, "price": 45000, "time": 4000},  # 9k
        {"symbol": symbol, "side": "sell", "qty": 0.15, "price": 45000, "time": 5000},  # 6.75k
    ]

    total_buy = sum(t["qty"] * t["price"] for t in synthetic_trades if t["side"] == "buy")
    total_sell = sum(t["qty"] * t["price"] for t in synthetic_trades if t["side"] == "sell")
    
    print_info(f"币种: {symbol}")
    print_info(f"交易笔数: {len(synthetic_trades)}")
    print(f"\n买方交易总额(USDT): {total_buy:,.0f}")
    print(f"卖方交易总额(USDT): {total_sell:,.0f}")
    print_success("合成交易数据准备完成")

    # Step 3: Aggregate trades
    print_section("Step 3: 聚合交易数据（窗口计算）")
    metric = aggregate_trades(synthetic_trades)
    
    print_data("聚合结果", {
        "buy_taker_volume": metric['buy_taker_volume'],
        "sell_taker_volume": metric['sell_taker_volume'],
        "买卖比率 (score_a)": f"{metric['score_a']:.2f}" if metric['score_a'] != float('inf') else "inf",
        "总体积": metric['total_volume'],
    })
    score_display = f"{metric['score_a']:.2f}" if metric['score_a'] != float('inf') else "inf"
    print_success(f"得分 A = {score_display}")

    # Step 4: Persist WindowMetric
    print_section("Step 4: 持久化窗口指标到数据库")
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=1)
    
    # Calculate more realistic 24h volume (around 30M USDT)
    volume_24h_usdt = 30_000_000  # 30M USDT within [10M, 80M] range
    
    wm = storage.store_window_metric(
        symbol=symbol,
        window_type='1h',
        window_start=window_start,
        window_end=window_end,
        buy_taker_volume=metric['buy_taker_volume'],
        sell_taker_volume=metric['sell_taker_volume'],
        total_volume=metric['total_volume'],
        score_a=metric['score_a'],
        volume_24h_usdt=volume_24h_usdt,
    )
    
    print_data("数据库记录", {
        "ID": wm.id,
        "币种": symbol,  # Use symbol directly instead of lazy loading
        "窗口类型": wm.window_type,
        "得分": float(wm.score_a),
        "创建时间": wm.computed_at.isoformat(),
    })
    print_success(f"WindowMetric 已保存 (ID: {wm.id})")

    # Step 5: Check threshold
    print_section("Step 5: 评估触发阈值")
    volume_24h = volume_24h_usdt  # Use the USDT volume directly
    score_threshold = 2.0
    volume_min = 10_000_000
    volume_max = 80_000_000
    
    print_info(f"阈值条件:")
    print_info(f"  • 得分 >= {score_threshold}: {metric['score_a']:.2f} >= {score_threshold} → {'✓' if metric['score_a'] >= score_threshold else '✗'}")
    print_info(f"  • 体积范围 [{volume_min/1e6:.0f}M, {volume_max/1e6:.0f}M]: {volume_24h/1e6:.1f}M → {'✓' if volume_min <= volume_24h <= volume_max else '✗'}")
    
    should_notify = metric['score_a'] >= score_threshold and volume_min <= volume_24h <= volume_max
    print_success(f"通知判定: {'触发 ✓' if should_notify else '不触发 ✗'}")

    if not should_notify:
        print("\n⚠️  阈值未满足，跳过通知进程")
        return

    # Step 6: Create notification record
    print_section("Step 6: 创建通知记录（幂等性）")
    event_id = f"{symbol}-{window_start.isoformat()}-1h"
    
    notif = storage.create_notification(
        symbol=symbol,
        window_metric_id=wm.id,
        event_id=event_id,
        payload={}  # Will be built next
    )
    
    if notif:
        print_data("通知记录", {
            "ID": notif.id,
            "Event ID": event_id,
            "状态": notif.status,
            "尝试次数": notif.attempts,
        })
        print_success(f"通知记录已创建 (ID: {notif.id})")
    else:
        print("⚠️  通知已存在（幂等性保护）")
        return

    # Step 7: Build Feishu payload
    print_section("Step 7: 构建飞书卡片")
    # Handle infinite score for display
    display_score = min(metric['score_a'], 999.99) if metric['score_a'] != float('inf') else 999.99
    payload = build_payload(
        symbol=symbol,
        window='1h',
        buy=metric['buy_taker_volume'],
        sell=metric['sell_taker_volume'],
        score=display_score
    )
    
    print_data("飞书卡片 JSON", payload)
    print_success("飞书卡片已构建")

    # Step 8: Send notification
    print_section("Step 8: 发送通知")
    
    send_real = os.getenv('SEND_REAL', '0') == '1'
    webhook = os.getenv('FEISHU_WEBHOOK')
    
    if send_real and webhook:
        print_info(f"🚀 实际发送模式已启用")
        print_info(f"   Webhook: {webhook[:50]}...")
    else:
        print_info(f"📋 模拟发送模式（要启用实际发送，设置 SEND_REAL=1 和 FEISHU_WEBHOOK）")
    
    result = send(payload, event_id=event_id, max_retries=3, base_backoff=1.0)
    
    if result:
        print_success("通知已发送")
        
        # Verify notification status
        session = storage.get_session()
        from src.models import Notification
        notif_check = session.query(Notification).filter_by(event_id=event_id).one_or_none()
        session.close()
        
        print_data("通知最终状态", {
            "状态": notif_check.status,
            "尝试次数": notif_check.attempts,
            "发送时间": notif_check.sent_at.isoformat() if notif_check.sent_at else "N/A",
        })
        print_success("通知已标记为已发送")
    else:
        print("❌ 通知发送失败")

    # Step 9: Summary
    print_section("演示完成 - 总结")
    print_success("✅ 所有步骤执行完成")
    print_info("\n执行流程:")
    print_info("  1. 初始化数据库")
    print_info("  2. 注入合成交易数据（高买卖比率场景）")
    print_info("  3. 聚合计算并得到 score_a")
    print_info("  4. 持久化到数据库")
    print_info("  5. 评估阈值（得分 >= 2.0 且体积 10M-80M USDT）")
    print_info("  6. 创建通知记录（支持幂等性）")
    print_info("  7. 构建飞书卡片JSON")
    print_info("  8. 发送通知（支持模拟和实际两种模式）")
    print_info("  9. 标记为已发送并保存")

    print("\n" + "="*70)
    print("  ✨ 飞书通知演示成功！")
    print("="*70 + "\n")


async def demo_multiple_scenarios():
    """Demonstrate multiple alert scenarios"""
    print_section("多场景演示")
    
    scenarios = [
        {
            "name": "低买卖比率 - 不触发",
            "symbol": "ETHUSDT",
            "buy": 10_000_000,
            "sell": 8_000_000,
            "score": 1.25,
            "volume_24h": 50_000_000,
        },
        {
            "name": "高买卖比率 - 触发",
            "symbol": "ADAUSDT",
            "buy": 30_000_000,
            "sell": 5_000_000,
            "score": 6.0,
            "volume_24h": 45_000_000,
        },
        {
            "name": "体积超出范围 - 不触发",
            "symbol": "DOGEUSDT",
            "buy": 40_000_000,
            "sell": 5_000_000,
            "score": 8.0,
            "volume_24h": 500_000_000,  # 超过 80M 上限
        },
    ]
    
    for scenario in scenarios:
        print(f"\n场景: {scenario['name']}")
        should_notify = (
            scenario['score'] >= 2.0 and
            10_000_000 <= scenario['volume_24h'] <= 80_000_000
        )
        status = "✅ 触发" if should_notify else "❌ 不触发"
        print(f"  {status}: score={scenario['score']:.1f}, volume={scenario['volume_24h']/1e6:.0f}M")


if __name__ == '__main__':
    print("\n")
    print(f"开始时间: {datetime.utcnow().isoformat()}")
    
    # Run main demo
    asyncio.run(demo_feishu_notification())
    
    # Run scenarios
    asyncio.run(demo_multiple_scenarios())
    
    print(f"结束时间: {datetime.utcnow().isoformat()}\n")
