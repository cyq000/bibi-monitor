# 币安合约主动买卖量监控系统 — 生产部署指南

## 目录

1. [系统架构](#系统架构)
2. [安装部署](#安装部署)
3. [配置管理](#配置管理)
4. [监控与告警](#监控与告警)
5. [性能优化](#性能优化)
6. [故障排查](#故障排查)
7. [安全加固](#安全加固)
8. [维护运维](#维护运维)

## 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    监控数据流                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  数据收集层                                                 │
│  ├─ WebSocket Client (实时交易数据)                         │
│  └─ REST Backfill (历史数据补全)                            │
│                      ↓                                      │
│  处理层                                                     │
│  ├─ Ingest Pipeline (协调)                                  │
│  ├─ Windowing (1h/4h/12h 聚合)                             │
│  └─ Score Calculation (评分)                               │
│                      ↓                                      │
│  存储层                                                     │
│  ├─ IngestionEvent (原始事件)                               │
│  ├─ WindowMetric (聚合指标)                                 │
│  └─ Notification (通知记录)                                 │
│                      ↓                                      │
│  告警层                                                     │
│  ├─ Feishu Webhook (飞书卡片)                               │
│  ├─ Alerting Service (失败告警)                             │
│  └─ Metrics Export (Prometheus)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 版本 | 说明 |
|-----|------|------|------|
| 运行时 | Python | 3.11+ | 异步优先 |
| 数据库 | PostgreSQL | 14+ | 推荐用于生产环境 |
| 缓存 | Redis | 7+ | 可选，用于优化 |
| API | FastAPI | 0.100+ | 高性能 Web框架 |
| 消息 | CCXT | 4.5+ | 交易所 API 库 |
| 容器 | Docker | 20+ | 20.10+ 推荐 |
| 监控 | Prometheus | 2.40+ | 可选 |

## 安装部署

### 方式 1: Docker Compose（推荐用于开发）

```bash
# 1. 克隆仓库
git clone <repo-url>
cd bibi

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 Feishu Webhook URL

# 3. 启动服务
docker-compose up -d

# 4. 验证
docker-compose logs -f app
curl http://localhost:8000/health
```

**docker-compose.yml 包含的服务：**

- **app**: 主应用（FastAPI）
- **db**: PostgreSQL 数据库
- **redis**: 缓存层（可选）
- **prometheus**: 指标收集（可选）
- **grafana**: 可视化仪表板（可选）

### 方式 2: Kubernetes（用于生产大规模部署）

创建 `k8s/deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: binance-monitor
  namespace: monitoring
spec:
  replicas: 3
  selector:
    matchLabels:
      app: binance-monitor
  template:
    metadata:
      labels:
        app: binance-monitor
    spec:
      containers:
      - name: app
        image: binance-monitor:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: postgresql-url
        - name: FEISHU_WEBHOOK
          valueFrom:
            secretKeyRef:
              name: feishu-webhook
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 方式 3: 虚拟机（传统服务器部署）

```bash
# 1. 环境准备
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql

# 2. 创建虚拟环境
python3.11 -m venv /opt/binance-monitor/venv
source /opt/binance-monitor/venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建 systemd 服务
sudo cp systemd/binance-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable binance-monitor
sudo systemctl start binance-monitor
```

## 配置管理

### 环境变量优先级

优先级从高到低：

1. **操作系统环境变量** (最优先)
2. **`.env` 文件** (仓库根目录)
3. **配置文件** (`monitor_config.json`)
4. **内置默认值** (最低)

### 必需配置

```bash
# Feishu 飞书
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/...

# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/binance_monitor

# 应用
LOG_LEVEL=INFO
SCORE_THRESHOLD=2.0
VOLUME_MIN=10000000
VOLUME_MAX=80000000
```

### 可选配置

```bash
# Redis 缓存
REDIS_URL=redis://localhost:6379/0

# Prometheus
PROMETHEUS_PORT=9090

# 监控
DAEMON_INTERVAL_SECONDS=60
RETENTION_DAYS_INGESTION=30
RETENTION_DAYS_METRICS=90
RETENTION_DAYS_NOTIFICATIONS=180
```

### 币种级别的阈值配置

在 `monitor_config.json` 中覆盖全局设置：

```json
{
  "score_threshold": 2.0,
  "volume_min": 10000000,
  "volume_max": 80000000,
  "per_symbol_thresholds": {
    "BTCUSDT": {
      "score_threshold": 2.5,
      "volume_min": 20000000
    },
    "ETHUSDT": {
      "score_threshold": 1.5,
      "volume_min": 5000000
    }
  }
}
```

## 监控与告警

### Prometheus 指标

系统自动导出以下指标：

```
# 通知相关
binance_notifications_total{symbol="BTCUSDT", status="sent"} 150
binance_notifications_total{symbol="BTCUSDT", status="failed"} 3

# 性能相关
binance_pipeline_duration_seconds 0.234
binance_db_query_duration_seconds 0.012

# 数据相关
binance_window_metrics_total{window_type="1h"} 5000
binance_ingestion_lag_seconds 1.2
```

### Grafana 仪表板

部署包含的 Grafana 仪表板显示：

1. **概览面板**
   - 24h 通知数
   - 失败率
   - 平均延迟
   - 活跃币种数

2. **性能面板**
   - 处理延迟分布
   - 数据库查询性能
   - API 响应时间

3. **数据质量面板**
   - 缺失数据率
   - 离群值检测
   - 数据新鲜度

### AlertManager 告警规则

```yaml
# prometheus/alerts.yaml
groups:
- name: binance-monitor
  rules:
  - alert: HighNotificationFailureRate
    expr: |
      rate(binance_notifications_total{status="failed"}[5m]) 
      / 
      rate(binance_notifications_total[5m]) > 0.1
    for: 5m
    annotations:
      summary: "通知失败率过高 ({{ $value | humanizePercentage }})"
      
  - alert: PipelineLatency
    expr: binance_pipeline_duration_seconds > 10
    for: 1m
    annotations:
      summary: "处理延迟过高"
      
  - alert: DatabaseConnectionFailed
    expr: binance_db_connection_errors_total > 0
    for: 1m
    annotations:
      summary: "无法连接数据库"
```

## 性能优化

### 数据库优化

```sql
-- 创建关键索引
CREATE INDEX idx_window_metric_symbol_time 
  ON window_metrics(symbol, window_end DESC);

CREATE INDEX idx_notification_created_at 
  ON notifications(created_at DESC);

CREATE INDEX idx_ingestion_event_symbol_time
  ON ingestion_events(symbol, created_at DESC);

-- 定期 VACUUM
VACUUM ANALYZE window_metrics;
VACUUM ANALYZE notifications;
```

### 缓存策略

使用 Redis 缓存热点数据：

```python
from src.cache import cache_manager

# 缓存配置
config = cache_manager.get_config(symbol="BTCUSDT")  # 1h TTL

# 缓存通知历史
notifications = cache_manager.get_recent_notifications(limit=100)  # 5m TTL
```

### 批量操作优化

```python
# ❌ 低效
for trade in trades:
    storage.create_ingestion_event(trade)

# ✅ 高效
storage.create_ingestion_events_batch(trades)  # 单次数据库写入
```

## 故障排查

### 常见问题

#### 1. 通知未发送

```bash
# 检查 Feishu webhook URL
curl -X POST https://open.feishu.cn/open-apis/bot/v2/hook/... \
  -H 'Content-Type: application/json' \
  -d '{"msg_type": "text", "content": {"text": "test"}}'

# 查看应用日志
docker-compose logs -f app | grep "feishu\|notif"

# 检查数据库中的通知记录
psql $DATABASE_URL -c "SELECT * FROM notifications WHERE status='pending';"
```

#### 2. 高延迟

```bash
# 检查处理时间
curl http://localhost:8000/stats?days=1 | jq '.processing_time_ms'

# 检查数据库性能
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT * FROM window_metrics LIMIT 1;"

# 增加并发度
export UVICORN_WORKERS=8
```

#### 3. 内存使用过高

```bash
# 检查连接泄漏
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# 清理过期数据
python -m src.maintenance.cleanup --days 30

# 重启应用
docker-compose restart app
```

### 调试模式

启用详细日志：

```bash
# 启动调试日志
export LOG_LEVEL=DEBUG
export SEND_REAL=0  # 使用模拟通知

# 运行测试脚本
python scripts/test_config_integration.py
```

## 安全加固

### 网络安全

```dockerfile
# Dockerfile - 使用非 root 用户
RUN useradd -m appuser
USER appuser

# 限制暴露的端口
EXPOSE 8000
RUN apt-get remove -y openssh-server
```

### 密钥管理

```bash
# ❌ 不要在代码中存储密钥
FEISHU_WEBHOOK="xxx"

# ✅ 使用密钥管理服务
# AWS Secrets Manager / HashiCorp Vault / Kubernetes Secrets
export FEISHU_WEBHOOK=$(aws secretsmanager get-secret-value --secret-id feishu-webhook)

# ✅ 环境变量 + .env（不提交到 Git）
# .gitignore
*.env
.env.local
secrets/
```

### API 安全

在生产环境添加认证：

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/config")
async def get_config(credentials: HTTPAuthCredentials = Depends(security)):
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid token")
    return ConfigManager().show()
```

### 审计日志

所有配置变更都应记录：

```python
@app.post("/config")
async def update_config(updates: dict):
    logger.info(
        f"CONFIG_CHANGE: {request.client.host} 修改配置",
        extra={
            "changes": updates,
            "timestamp": datetime.utcnow(),
            "user": get_current_user(),
        }
    )
    # ... 更新逻辑
```

## 维护运维

### 日常运维

```bash
# 每日检查健康状态
curl http://localhost:8000/health

# 每周检查数据库大小
psql $DATABASE_URL -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 每月清理过期数据
python -m src.maintenance.cleanup --days 30 --actual
```

### 定期维护任务

```yaml
# cron jobs
CLEANUP: "0 2 * * 0"    # 每周日 2:00 清理过期数据
BACKUP: "0 3 * * *"     # 每日 3:00 备份数据库
ANALYZE: "0 4 * * 0"    # 每周日 4:00 分析表
```

### 监控更新

保持依赖包最新：

```bash
# 检查更新
pip list --outdated

# 更新关键依赖
pip install --upgrade sqlalchemy=2.0.50
pip install --upgrade fastapi
pip install --upgrade pydantic

# 运行测试确保兼容性
pytest tests/ -v
```

### 灾难恢复

```bash
# 数据库备份
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
psql $DATABASE_URL < backup_20240210_150000.sql

# 验证数据完整性
python scripts/verify_data_integrity.py
```

## 性能基准

### 预期性能指标

| 指标 | 目标 | 说明 |
|-----|------|------|
| 端到端延迟 | < 5s | 从交易到通知 |
| 处理吞吐量 | > 10k trades/s | 单实例容量 |
| 通知成功率 | > 99% | 带重试机制 |
| API 响应时间 | < 200ms | P95 |
| 数据库查询 | < 50ms | P95 |
| 可用性 | > 99.5% | 月度 |

### 负载测试

```python
# scripts/load_test.py
import asyncio
from locust import HttpUser, task, between

class MonitorUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def query_notifications(self):
        self.client.get("/notifications?days=7")
    
    @task(1)
    def export_data(self):
        self.client.get("/export?format=csv&days=30")

# 运行
locust -f scripts/load_test.py --host=http://localhost:8000
```

---

## 获取支持

- 📖 [完整 API 文档](http://localhost:8000/docs)
- 🐛 [报告 Bug](https://github.com/xxx/issues)
- 💬 [讨论功能](https://github.com/xxx/discussions)
- 📧 [联系作者](mailto:support@example.com)

**最后更新**: 2026-02-10
**维护者**: DevOps Team
