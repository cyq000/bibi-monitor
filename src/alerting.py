"""T024 - 重试和告警系统：监控持久化失败并发送告警"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from src.storage import storage as storage_adapter

logger = logging.getLogger(__name__)


class FailureEvent:
    """失败事件，用于追踪"""

    def __init__(self, event_id: str, component: str, error: str, timestamp: Optional[datetime] = None):
        self.event_id = event_id
        self.component = component  # e.g., "notifier", "storage", "collector"
        self.error = error
        self.timestamp = timestamp or datetime.utcnow()
        self.retry_count = 0
        self.last_retry_time = None


class RetryPolicy:
    """重试策略：指数退避"""

    def __init__(self, max_retries: int = 5, base_delay: int = 1, max_delay: int = 300):
        self.max_retries = max_retries
        self.base_delay = base_delay  # 秒
        self.max_delay = max_delay

    def get_retry_delay(self, retry_count: int) -> int:
        """获取重试延迟（秒）"""
        delay = self.base_delay * (2 ** retry_count)
        return min(delay, self.max_delay)

    def should_retry(self, retry_count: int) -> bool:
        """判断是否应该重试"""
        return retry_count < self.max_retries


class AlertingService:
    """告警服务：监控失败并发送告警"""

    def __init__(self, failure_log_path: Optional[Path] = None):
        self.failure_log_path = failure_log_path or Path("./data/failures.json")
        self.failures: Dict[str, FailureEvent] = {}
        self.retry_policy = RetryPolicy()
        self.alert_thresholds = {
            "consecutive_failures": 3,  # 连续失败 3 次触发告警
            "failure_rate": 0.5,  # 失败率 > 50% 触发告警
            "time_window": 300,  # 5 分钟时间窗口
        }
        self._load_failures()

    def _load_failures(self):
        """从文件加载失败记录"""
        if self.failure_log_path.exists():
            try:
                with open(self.failure_log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for event_id, event_data in data.get('failures', {}).items():
                        fe = FailureEvent(
                            event_id=event_id,
                            component=event_data.get('component'),
                            error=event_data.get('error'),
                            timestamp=datetime.fromisoformat(event_data.get('timestamp')),
                        )
                        fe.retry_count = event_data.get('retry_count', 0)
                        self.failures[event_id] = fe
                logger.info(f"加载了 {len(self.failures)} 条失败记录")
            except Exception as e:
                logger.error(f"加载失败记录出错: {e}")

    def _save_failures(self):
        """保存失败记录到文件"""
        try:
            self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "failures": {},
                "saved_at": datetime.utcnow().isoformat(),
            }
            for event_id, fe in self.failures.items():
                data["failures"][event_id] = {
                    "component": fe.component,
                    "error": fe.error,
                    "timestamp": fe.timestamp.isoformat(),
                    "retry_count": fe.retry_count,
                }
            with open(self.failure_log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存失败记录出错: {e}")

    def record_failure(self, event_id: str, component: str, error: str) -> bool:
        """记录失败事件

        Args:
            event_id: 事件 ID
            component: 组件名称
            error: 错误信息

        Returns:
            是否应该重试
        """
        if event_id not in self.failures:
            fe = FailureEvent(event_id, component, error)
            self.failures[event_id] = fe
            logger.warning(f"✗ 记录失败 {event_id}: {component} - {error}")
        else:
            fe = self.failures[event_id]
            fe.retry_count += 1
            fe.last_retry_time = datetime.utcnow()

        self._save_failures()

        # 检查是否应该重试
        should_retry = self.retry_policy.should_retry(fe.retry_count)
        
        if not should_retry:
            logger.error(f"✗ 事件 {event_id} 已超过最大重试次数，放弃")
            self._trigger_alert(event_id, fe)
        
        return should_retry

    def get_retry_delay(self, event_id: str) -> int:
        """获取重试延迟（秒）"""
        if event_id not in self.failures:
            return 0
        fe = self.failures[event_id]
        return self.retry_policy.get_retry_delay(fe.retry_count)

    def mark_success(self, event_id: str) -> bool:
        """标记成功，移除失败记录"""
        if event_id in self.failures:
            logger.info(f"✓ 事件 {event_id} 重试成功")
            del self.failures[event_id]
            self._save_failures()
            return True
        return False

    def get_failure_stats(self) -> Dict[str, Any]:
        """获取失败统计"""
        now = datetime.utcnow()
        recent_failures = [
            fe for fe in self.failures.values()
            if (now - fe.timestamp).total_seconds() < self.alert_thresholds["time_window"]
        ]

        stats = {
            "total_failures": len(self.failures),
            "recent_failures": len(recent_failures),
            "failures_by_component": {},
            "avg_retry_count": 0,
        }

        for fe in self.failures.values():
            component = fe.component
            if component not in stats["failures_by_component"]:
                stats["failures_by_component"][component] = 0
            stats["failures_by_component"][component] += 1

        if self.failures:
            stats["avg_retry_count"] = sum(fe.retry_count for fe in self.failures.values()) / len(self.failures)

        return stats

    def _trigger_alert(self, event_id: str, failure: FailureEvent):
        """触发告警"""
        alert_message = f"""
        ❌ ALERT: 事件持久化失败
        事件 ID: {event_id}
        组件: {failure.component}
        错误: {failure.error}
        重试次数: {failure.retry_count}
        首次失败: {failure.timestamp.isoformat()}
        
        建议操作:
        1. 检查存储后端连接状态
        2. 查看日志文件获取更多详细信息
        3. 手动重试或联系管理员
        """

        logger.error(alert_message)
        
        # TODO: 集成实际的告警系统
        # - 邮件告警
        # - Slack/钉钉/飞书通知
        # - Prometheus AlertManager
        # - 数据库告警记录表

    def check_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        stats = self.get_failure_stats()
        
        health = {
            "status": "healthy",
            "stats": stats,
            "alerts": [],
        }

        # 连续失败告警
        for component, count in stats["failures_by_component"].items():
            if count >= self.alert_thresholds["consecutive_failures"]:
                health["status"] = "degraded"
                health["alerts"].append(f"组件 {component} 连续失败 {count} 次")

        # 失败率告警
        recent_total = stats["total_failures"]
        if recent_total > 5:  # 至少 5 个失败事件
            health["status"] = "degraded"
            health["alerts"].append(f"最近共有 {recent_total} 个失败事件")

        return health


# 全局实例
alerting = AlertingService()


def handle_failure_with_retry(
    event_id: str,
    component: str,
    error: str,
    retry_fn=None
) -> bool:
    """处理失败并重试的辅助函数

    Args:
        event_id: 事件 ID
        component: 组件名称
        error: 错误信息
        retry_fn: 重试函数（可选）

    Returns:
        是否应该重试
    """
    should_retry = alerting.record_failure(event_id, component, error)
    
    if should_retry:
        delay = alerting.get_retry_delay(event_id)
        logger.info(f"  将在 {delay} 秒后重试")
        
        if retry_fn:
            # 这里可以集成实际的重试逻辑
            # 例如将任务排队到后台任务队列（Celery/RQ）
            logger.info(f"  记录重试任务到队列")
    
    return should_retry


if __name__ == "__main__":
    # Demo
    print("=== 告警系统演示 ===\n")
    
    # 记录一些失败
    print("1. 记录失败事件")
    alerting.record_failure("evt_001", "notifier", "Feishu webhook timeout")
    alerting.record_failure("evt_002", "storage", "Database connection refused")
    alerting.record_failure("evt_001", "notifier", "Feishu webhook timeout")  # 重试
    
    # 获取统计
    print("\n2. 失败统计")
    stats = alerting.get_failure_stats()
    print(f"   总失败数: {stats['total_failures']}")
    print(f"   按组件: {stats['failures_by_component']}")
    
    # 检查健康状态
    print("\n3. 系统健康状态")
    health = alerting.check_health()
    print(f"   状态: {health['status']}")
    if health['alerts']:
        for alert in health['alerts']:
            print(f"   告警: {alert}")
    
    # 标记成功
    print("\n4. 标记事件成功")
    alerting.mark_success("evt_001")
    print(f"   剩余失败数: {len(alerting.failures)}")
