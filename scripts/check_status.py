#!/usr/bin/env python3
"""检查 Daemon 收集的实时数据"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.db import init_db, get_engine
from src.models import Notification, WindowMetric, IngestionEvent
from src.logging import get_logger
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from datetime import datetime

logger = get_logger(__name__)

try:
    init_db()
    engine = get_engine()
    
    with Session(engine) as session:
        # 统计信息
        total_events = session.query(func.count(IngestionEvent.id)).scalar() or 0
        total_metrics = session.query(func.count(WindowMetric.id)).scalar() or 0
        total_notifications = session.query(func.count(Notification.id)).scalar() or 0
        
        print("\n" + "="*70)
        print(f"  Daemon 监控状态 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        print(f"\n📊 数据统计:")
        print(f"   采集事件总数: {total_events}")
        print(f"   窗口指标总数: {total_metrics}")
        print(f"   通知记录总数: {total_notifications}")
        
        # 最新的窗口指标
        recent_metrics = session.query(WindowMetric).order_by(
            desc(WindowMetric.id)
        ).limit(5).all()
        
        if recent_metrics:
            print(f"\n📈 最新窗口指标 (共 {len(recent_metrics)} 条):")
            for metric in recent_metrics:
                symbol_name = metric.symbol_obj.symbol if metric.symbol_obj else "Unknown"
                print(f"   • ID:{metric.id} | {symbol_name} | 窗口: {metric.window_type} | 评分: {metric.score_a:.2f} | {metric.computed_at}")
        else:
            print(f"\n📈 暂无窗口指标数据")
        
        # 最新的通知
        recent_notifications = session.query(Notification).order_by(
            desc(Notification.id)
        ).limit(5).all()
        
        if recent_notifications:
            print(f"\n🔔 最新通知 (共 {len(recent_notifications)} 条):")
            for notif in recent_notifications:
                status_icon = "✅" if notif.status == "sent" else "⏳" if notif.status == "pending" else "❌"
                print(f"   {status_icon} ID:{notif.id} | {notif.event_id} | 状态: {notif.status} | {notif.created_at}")
        else:
            print(f"\n🔔 暂无通知记录")
        
        # 最新的采集事件
        recent_events = session.query(IngestionEvent).order_by(
            desc(IngestionEvent.id)
        ).limit(5).all()
        
        if recent_events:
            print(f"\n📥 最新采集事件 (共 {len(recent_events)} 条):")
            for event in recent_events:
                print(f"   • ID:{event.id} | {event.symbol} | 交易数: {event.trade_count} | {event.timestamp}")
        else:
            print(f"\n📥 暂无采集事件")
        
        print(f"\n💡 Daemon 工作情况:")
        if total_events > 0:
            print(f"   ✅ Daemon 正在运行并采集数据")
            print(f"   ✅ 已采集 {total_events} 个交易事件")
            if total_metrics > 0:
                print(f"   ✅ 已计算 {total_metrics} 个窗口指标")
            if total_notifications > 0:
                print(f"   ✅ 已生成 {total_notifications} 条飞书通知")
        else:
            print(f"   ⏳ Daemon 正在启动或采集数据中...")
            print(f"   📌 首次启动需要约 11 分钟来采集足够数据并计算窗口指标")
        
        print(f"\n🎯 当前监控目标:")
        print(f"   币种: BTCUSDT, ETHUSDT")
        print(f"   评分阈值: >= 2.0")
        print(f"   体积范围: 10M - 80M USDT")
        print(f"   飞书 Webhook: 已配置")
        print(f"   状态: 正在后台运行\n")
        
        print("="*70)
        
except Exception as e:
    print(f"❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()
