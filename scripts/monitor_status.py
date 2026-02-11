#!/usr/bin/env python3
"""实时监控 Daemon 运行状态和数据收集情况"""
import os
import sys
import time
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db, get_engine
from src.models import Notification, WindowMetric, IngestionEvent
from src.logging import get_logger
from sqlalchemy import func, desc

logger = get_logger(__name__)


def get_stats():
    """Get current daemon statistics"""
    try:
        init_db()
        engine = get_engine()
        
        # 使用 ORM 查询
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            # 最新的窗口指标
            recent_metrics = session.query(WindowMetric).order_by(
                desc(WindowMetric.id)
            ).limit(10).all()
            
            # 最新的通知
            recent_notifications = session.query(Notification).order_by(
                desc(Notification.id)
            ).limit(10).all()
            
            # 最新的采集事件
            recent_events = session.query(IngestionEvent).order_by(
                desc(IngestionEvent.id)
            ).limit(10).all()
            
            # 统计信息
            total_events = session.query(func.count(IngestionEvent.id)).scalar()
            total_metrics = session.query(func.count(WindowMetric.id)).scalar()
            total_notifications = session.query(func.count(Notification.id)).scalar()
            
            print("\n" + "="*70)
            print(f"  Daemon 监控状态 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*70)
            
            print(f"\n📊 数据统计:")
            print(f"   采集事件总数: {total_events}")
            print(f"   窗口指标总数: {total_metrics}")
            print(f"   通知记录总数: {total_notifications}")
            
            if recent_metrics:
                print(f"\n📈 最新窗口指标 (共 {len(recent_metrics)} 条):")
                for metric in recent_metrics[:5]:
                    print(f"   • {metric.symbol} | 窗口: {metric.window_type} | 评分: {metric.score_a:.2f} | 时间: {metric.created_at}")
            
            if recent_notifications:
                print(f"\n🔔 最新通知 (共 {len(recent_notifications)} 条):")
                for notif in recent_notifications[:5]:
                    status_icon = "✅" if notif.status == "sent" else "⏳" if notif.status == "pending" else "❌"
                    print(f"   {status_icon} {notif.event_id} | 状态: {notif.status} | 时间: {notif.created_at}")
            
            if recent_events:
                print(f"\n📥 最新采集事件 (共 {len(recent_events)} 条):")
                for event in recent_events[:5]:
                    print(f"   • {event.symbol} | 交易数: {event.trade_count} | 采集时间: {event.timestamp}")
            
            print(f"\n💡 Daemon 工作流程:")
            print(f"   1️⃣  从币安 WebSocket 采集实时交易数据")
            print(f"   2️⃣  存储采集事件到数据库")
            print(f"   3️⃣  每 11 分钟计算一次窗口指标（1h, 4h, 12h）")
            print(f"   4️⃣  评估买卖比评分和体积条件")
            print(f"   5️⃣  触发条件时构建飞书卡片并发送通知")
            print(f"   6️⃣  记录通知状态和重试机制")
            
            print(f"\n🎯 当前监控目标:")
            print(f"   币种: BTCUSDT, ETHUSDT")
            print(f"   评分阈值: >= 2.0")
            print(f"   体积范围: 10M - 80M USDT")
            print(f"   飞书 Webhook: 已配置")
            
            print("\n" + "="*70)
            print("✨ Daemon 正在后台运行，持续采集真实数据...")
            print("="*70 + "\n")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 持续监控
    interval = 30  # 每 30 秒刷新一次
    
    try:
        while True:
            get_stats()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
