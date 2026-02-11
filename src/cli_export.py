#!/usr/bin/env python3
"""CLI 导出工具：从数据库导出通知记录为 JSON/CSV 格式"""

import argparse
import json
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from src.storage import storage
from src.db import get_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from src.models import Notification, WindowMetric, Symbol
from src.logging import get_logger

logger = get_logger(__name__)


class NotificationExporter:
    """通知导出器"""

    def __init__(self):
        self.engine = get_engine()
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def query_notifications(
        self,
        days: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """
        查询通知记录

        Args:
            days: 最近 N 天
            symbol: 按币种过滤
            status: 按状态过滤（pending/sent/failed）

        Returns:
            通知记录列表
        """
        session = self.SessionLocal()
        try:
            # 计算时间范围
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            # 构建查询
            query = session.query(Notification).filter(
                Notification.created_at >= start_time
            )

            # 按币种过滤
            if symbol:
                sym = session.query(Symbol).filter_by(symbol=symbol).first()
                if sym:
                    query = query.filter(Notification.symbol_id == sym.id)
                else:
                    logger.warning(f"币种 {symbol} 未找到")
                    return []

            # 按状态过滤
            if status:
                query = query.filter(Notification.status == status)

            # 排序
            notifications = query.order_by(Notification.created_at.desc()).all()

            # 构建结果
            records = []
            for notif in notifications:
                sym_name = session.query(Symbol).filter_by(id=notif.symbol_id).first().symbol if notif.symbol_id else "N/A"

                record = {
                    "id": notif.id,
                    "symbol": sym_name,
                    "event_id": notif.event_id,
                    "status": notif.status,
                    "attempts": notif.attempts,
                    "created_at": notif.created_at.isoformat() if notif.created_at else "",
                    "sent_at": notif.sent_at.isoformat() if notif.sent_at else "",
                }

                # 关联 WindowMetric
                if notif.window_metric_id:
                    wm = session.query(WindowMetric).filter_by(id=notif.window_metric_id).first()
                    if wm:
                        record.update({
                            "window_type": wm.window_type,
                            "window_start": wm.window_start.isoformat(),
                            "window_end": wm.window_end.isoformat(),
                            "score_a": float(wm.score_a),
                            "buy_volume": float(wm.buy_taker_volume),
                            "sell_volume": float(wm.sell_taker_volume),
                            "volume_24h_usdt": float(wm.volume_24h_usdt) if wm.volume_24h_usdt else None,
                        })

                records.append(record)

            logger.info(f"查询到 {len(records)} 条通知记录（最近 {days} 天）")
            return records

        finally:
            session.close()

    def export_json(
        self,
        output_file: str,
        days: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """导出为 JSON 格式"""
        records = self.query_notifications(days, symbol, status)

        export_data = {
            "metadata": {
                "export_time": datetime.utcnow().isoformat(),
                "period_days": days,
                "symbol_filter": symbol,
                "status_filter": status,
                "record_count": len(records),
            },
            "records": records,
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 已导出 {len(records)} 条记录到 {output_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")
            return False

    def export_csv(
        self,
        output_file: str,
        days: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """导出为 CSV 格式"""
        records = self.query_notifications(days, symbol, status)

        if not records:
            logger.warning("没有记录可导出")
            return False

        try:
            # 获取所有字段名
            fieldnames = list(records[0].keys())

            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)

            logger.info(f"✅ 已导出 {len(records)} 条记录到 {output_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 导出失败: {e}")
            return False

    def print_summary(self, days: int = 30) -> None:
        """打印摘要统计"""
        session = self.SessionLocal()
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            total = session.query(Notification).filter(
                Notification.created_at >= start_time
            ).count()

            sent = session.query(Notification).filter(
                and_(Notification.created_at >= start_time, Notification.status == "sent")
            ).count()

            failed = session.query(Notification).filter(
                and_(Notification.created_at >= start_time, Notification.status == "failed")
            ).count()

            pending = total - sent - failed

            print(f"\n{'='*50}")
            print(f"  通知统计（最近 {days} 天）")
            print(f"{'='*50}")
            print(f"总数:      {total}")
            print(f"已发送:    {sent} ({sent/total*100:.1f}%)" if total > 0 else "已发送:    0")
            print(f"待发送:    {pending}")
            print(f"失败:      {failed}")
            print(f"{'='*50}\n")

        finally:
            session.close()


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="币安监控通知导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：

  # 导出最近 30 天为 JSON
  python -m src.cli_export --days 30 --format json

  # 导出特定币种为 CSV
  python -m src.cli_export --symbol BTCUSDT --format csv --output btc_notifications.csv

  # 只导出已发送的通知
  python -m src.cli_export --status sent --format json

  # 查看统计信息
  python -m src.cli_export --stats --days 7
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="导出最近 N 天的数据（默认 30）",
    )

    parser.add_argument(
        "--symbol",
        help="按币种过滤（如 BTCUSDT）",
    )

    parser.add_argument(
        "--status",
        choices=["pending", "sent", "failed"],
        help="按状态过滤",
    )

    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="导出格式（默认 json）",
    )

    parser.add_argument(
        "--output",
        help="输出文件路径（默认自动生成）",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="只显示统计信息，不导出",
    )

    args = parser.parse_args()

    exporter = NotificationExporter()

    # 显示统计
    if args.stats:
        exporter.print_summary(args.days)
        return 0

    # 确定输出文件
    if not args.output:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        symbol_str = f"_{args.symbol}" if args.symbol else ""
        ext = "json" if args.format == "json" else "csv"
        args.output = f"notifications_{timestamp}{symbol_str}.{ext}"

    # 创建输出目录
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 导出
    if args.format == "json":
        success = exporter.export_json(args.output, args.days, args.symbol, args.status)
    else:  # csv
        success = exporter.export_csv(args.output, args.days, args.symbol, args.status)

    # 显示统计
    exporter.print_summary(args.days)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
