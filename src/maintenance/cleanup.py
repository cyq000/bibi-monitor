"""T025 - 数据保留和清理：定期清理过期的事件和指标"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import delete
from src.models import IngestionEvent, WindowMetric, Notification
from src.storage import storage as storage_adapter

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """数据保留策略"""

    def __init__(
        self,
        ingestion_event_days: int = 30,
        window_metric_days: int = 90,
        notification_days: int = 180,
    ):
        """初始化保留策略

        Args:
            ingestion_event_days: IngestionEvent 保留天数
            window_metric_days: WindowMetric 保留天数
            notification_days: Notification 保留天数
        """
        self.ingestion_event_days = ingestion_event_days
        self.window_metric_days = window_metric_days
        self.notification_days = notification_days

        logger.info(
            f"保留策略: IngestionEvent {ingestion_event_days}天, "
            f"WindowMetric {window_metric_days}天, Notification {notification_days}天"
        )


class CleanupJob:
    """清理作业"""

    def __init__(self, storage=None, policy: Optional[RetentionPolicy] = None):
        self.storage = storage or storage_adapter
        self.policy = policy or RetentionPolicy()
        self.stats = {
            "ingestion_events_deleted": 0,
            "window_metrics_deleted": 0,
            "notifications_deleted": 0,
            "last_run": None,
            "run_count": 0,
        }

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """运行清理作业

        Args:
            dry_run: 如果为 True，仅计算要删除的数据，不实际删除

        Returns:
            清理统计
        """
        logger.info("="*70)
        logger.info(f"开始数据清理作业 ({'模拟模式' if dry_run else '实际执行'})")
        logger.info("="*70)

        now = datetime.utcnow()
        stats = {
            "ingestion_events": self._cleanup_ingestion_events(now, dry_run),
            "window_metrics": self._cleanup_window_metrics(now, dry_run),
            "notifications": self._cleanup_notifications(now, dry_run),
            "run_at": now.isoformat(),
            "dry_run": dry_run,
        }

        # 更新全局统计
        self.stats["ingestion_events_deleted"] += stats["ingestion_events"]["deleted"]
        self.stats["window_metrics_deleted"] += stats["window_metrics"]["deleted"]
        self.stats["notifications_deleted"] += stats["notifications"]["deleted"]
        self.stats["last_run"] = now
        self.stats["run_count"] += 1

        logger.info("="*70)
        logger.info("清理作业完成")
        logger.info("="*70)

        return stats

    def _cleanup_ingestion_events(self, now: datetime, dry_run: bool) -> Dict[str, Any]:
        """清理过期的摄入事件"""
        logger.info("\n[1] 清理 IngestionEvent")

        cutoff_date = now - timedelta(days=self.policy.ingestion_event_days)
        logger.info(f"    删除 {cutoff_date.isoformat()} 之前的事件")

        try:
            session = self.storage.session_factory()
            
            # 查询要删除的事件
            query = session.query(IngestionEvent).filter(
                IngestionEvent.created_at < cutoff_date
            )
            count = query.count()
            
            if count == 0:
                logger.info(f"    没有过期事件需要删除")
                session.close()
                return {
                    "count": 0,
                    "deleted": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                }

            logger.info(f"    找到 {count} 条过期事件")

            if not dry_run:
                # 实际删除
                query.delete(synchronize_session=False)
                session.commit()
                logger.info(f"    ✓ 已删除 {count} 条事件")
            else:
                logger.info(f"    [模拟] 将删除 {count} 条事件")
                session.rollback()

            session.close()
            
            return {
                "count": count,
                "deleted": count if not dry_run else 0,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"    ✗ 清理 IngestionEvent 失败: {e}")
            return {
                "count": 0,
                "deleted": 0,
                "error": str(e),
            }

    def _cleanup_window_metrics(self, now: datetime, dry_run: bool) -> Dict[str, Any]:
        """清理过期的窗口指标"""
        logger.info("\n[2] 清理 WindowMetric")

        cutoff_date = now - timedelta(days=self.policy.window_metric_days)
        logger.info(f"    删除 {cutoff_date.isoformat()} 之前的指标")

        try:
            session = self.storage.session_factory()
            
            # 查询要删除的指标
            query = session.query(WindowMetric).filter(
                WindowMetric.window_end < cutoff_date
            )
            count = query.count()
            
            if count == 0:
                logger.info(f"    没有过期指标需要删除")
                session.close()
                return {
                    "count": 0,
                    "deleted": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                }

            logger.info(f"    找到 {count} 条过期指标")

            if not dry_run:
                # 实际删除
                query.delete(synchronize_session=False)
                session.commit()
                logger.info(f"    ✓ 已删除 {count} 条指标")
            else:
                logger.info(f"    [模拟] 将删除 {count} 条指标")
                session.rollback()

            session.close()
            
            return {
                "count": count,
                "deleted": count if not dry_run else 0,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"    ✗ 清理 WindowMetric 失败: {e}")
            return {
                "count": 0,
                "deleted": 0,
                "error": str(e),
            }

    def _cleanup_notifications(self, now: datetime, dry_run: bool) -> Dict[str, Any]:
        """清理过期的通知"""
        logger.info("\n[3] 清理 Notification")

        cutoff_date = now - timedelta(days=self.policy.notification_days)
        logger.info(f"    删除 {cutoff_date.isoformat()} 之前的通知")

        try:
            session = self.storage.session_factory()
            
            # 查询要删除的通知
            query = session.query(Notification).filter(
                Notification.created_at < cutoff_date
            )
            count = query.count()
            
            if count == 0:
                logger.info(f"    没有过期通知需要删除")
                session.close()
                return {
                    "count": 0,
                    "deleted": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                }

            logger.info(f"    找到 {count} 条过期通知")

            if not dry_run:
                # 实际删除
                query.delete(synchronize_session=False)
                session.commit()
                logger.info(f"    ✓ 已删除 {count} 条通知")
            else:
                logger.info(f"    [模拟] 将删除 {count} 条通知")
                session.rollback()

            session.close()
            
            return {
                "count": count,
                "deleted": count if not dry_run else 0,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"    ✗ 清理 Notification 失败: {e}")
            return {
                "count": 0,
                "deleted": 0,
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取清理统计"""
        return {
            "total_deleted": (
                self.stats["ingestion_events_deleted"] +
                self.stats["window_metrics_deleted"] +
                self.stats["notifications_deleted"]
            ),
            "by_table": {
                "ingestion_events": self.stats["ingestion_events_deleted"],
                "window_metrics": self.stats["window_metrics_deleted"],
                "notifications": self.stats["notifications_deleted"],
            },
            "run_count": self.stats["run_count"],
            "last_run": self.stats["last_run"],
        }

    def get_data_sizes(self) -> Dict[str, Any]:
        """获取数据库表的大小"""
        logger.info("\n获取数据库表的大小...")
        
        try:
            session = self.storage.session_factory()
            
            sizes = {
                "ingestion_events": session.query(IngestionEvent).count(),
                "window_metrics": session.query(WindowMetric).count(),
                "notifications": session.query(Notification).count(),
            }
            
            session.close()
            
            return sizes

        except Exception as e:
            logger.error(f"获取表大小失败: {e}")
            return {}


if __name__ == "__main__":
    # Demo
    import logging.config

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 70)
    print("T025 - 数据保留和清理演示")
    print("=" * 70)

    # 创建清理作业
    policy = RetentionPolicy(
        ingestion_event_days=30,
        window_metric_days=90,
        notification_days=180,
    )
    
    job = CleanupJob(policy=policy)

    # 先进行模拟运行
    print("\n[1] 模拟清理运行")
    stats = job.run(dry_run=True)
    print(f"\n模拟清理结果:")
    print(f"  IngestionEvent: {stats['ingestion_events']['count']} 条")
    print(f"  WindowMetric: {stats['window_metrics']['count']} 条")
    print(f"  Notification: {stats['notifications']['count']} 条")

    # 显示统计
    print("\n[2] 清理统计")
    cleanup_stats = job.get_stats()
    print(f"  总清理数: {cleanup_stats['total_deleted']}")
    print(f"  运行次数: {cleanup_stats['run_count']}")
    print(f"  最后运行: {cleanup_stats['last_run']}")

    print("\n" + "=" * 70)
