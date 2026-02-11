# 币安合约主动买卖量监控系统 🚀

[![CI/CD](https://github.com/yourusername/binance-monitor/workflows/CI/badge.svg)](https://github.com/yourusername/binance-monitor/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 实时监控币安合约主动买卖活动，当检测到异常买卖比率时通过飞书通知告警

## ✨ 核心特性

### 🎯 US1: 监控线程发现并通知 (MVP - 已完成)
- **实时数据流**：通过 WebSocket 订阅币安合约交易流
- **历史回补**：通过 REST API 获取历史数据补全缺失窗口
- **窗口聚合**：支持 1h、4h、12h 时间窗口的交易数据聚合
- **动态评分**：计算买卖比率 (Score A) = 买方主动量 / 卖方主动量
- **智能告警**：满足阈值条件自动发送飞书通知卡片
- **幂等性保证**：使用 event_id 防止重复通知
- **重试机制**：指数退避重试策略，最多重试 3 次

### 📊 US2: 查看与导出监控日志 (开发中)
- 快速查看所有历史告警通知
- JSON/CSV 格式导出
- 支持按时间范围和币种过滤
- FastAPI HTTP 端点 + CLI 工具

### ⚙️ US3: 可配置监控阈值 (计划中)
- 动态修改买卖比率阈值
- 自定义 24h 体积范围
- 支持每币种独立配置
- 实时生效或重启后生效

## 📦 项目结构

```
.
├── src/
│   ├── __main__.py              # CLI 入口
│   ├── cli.py                   # CLI 命令
│   ├── config.py                # 配置加载器
│   ├── db.py                    # 数据库连接
│   ├── models.py                # SQLAlchemy 模型
│   ├── storage.py               # 数据持久化
│   ├── daemon.py                # 守护进程
│   ├── logging.py               # 日志系统
│   ├── metrics.py               # 性能指标
│   ├── notifier.py              # 飞书通知
│   ├── collector/               # 数据采集
│   │   ├── websocket_client.py  # WebSocket 客户端
│   │   └── rest_backfill.py     # REST 回补
│   ├── processor/               # 数据处理
│   │   ├── windowing.py         # 窗口聚合
│   │   └── ingest_pipeline.py   # 摄入管道
│   ├── api/                     # FastAPI 应用 (US2)
│   │   └── main.py              # API 端点
│   ├── admin/                   # 管理功能
│   │   └── config_endpoints.py  # 配置端点 (US3)
│   └── maintenance/             # 维护工具
│       └── cleanup.py           # 数据清理
├── tests/
│   ├── test_*.py                # 单元测试
│   └── integration/             # 集成测试
├── scripts/
│   ├── feishu_demo.py           # 飞书演示
│   └── feishu_demo_real.py      # 真实 Webhook 演示
├── specs/
│   └── 001-binance-monitor/
│       ├── spec.md              # 功能规范
│       ├── plan.md              # 技术方案
│       ├── data-model.md        # 数据模型
│       ├── requirements.txt     # 需求清单
│       └── contracts/           # API 合同
├── alembic/                     # 数据库迁移
├── docs/
│   └── FEISHU_SETUP.md          # 飞书配置指南
├── .github/
│   └── workflows/
│       └── ci.yml               # CI/CD 工作流
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml               # 项目配置
├── .env.example                 # 环境变量示例
└── README.md
```

## 🚀 快速开始

### 前置要求

- Python 3.11+
- pip 或 pip-tools
- Docker (可选，用于容器化部署)
- Binance API 密钥 (可选，用于真实数据)
- 飞书机器人 Webhook (用于告警通知)

### 本地开发

#### 1. 克隆与设置

```bash
git clone https://github.com/yourusername/binance-monitor.git
cd binance-monitor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

#### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env，填入您的飞书 Webhook URL
```

#### 3. 初始化数据库

```bash
python -c "from src.db import init_db; init_db()"
```

#### 4. 运行演示

```bash
# 模拟模式（无需真实 Webhook）
python scripts/feishu_demo.py

# 真实发送（需要配置 FEISHU_WEBHOOK）
python scripts/feishu_demo_real.py --webhook "https://open.feishu.cn/..."
```

#### 5. 启动守护进程

```bash
python -m src
```

### Docker 部署

#### 本地开发

```bash
docker-compose up --build
```

#### 生产部署

```bash
docker build -t binance-monitor:latest .
docker run -d \
  -e FEISHU_WEBHOOK="https://..." \
  -e DB_URL="postgresql://user:pass@db:5432/monitor" \
  binance-monitor:latest
```

## 📋 核心概念

### Score A (买卖比率)

$$\text{Score A} = \frac{\text{买方主动量}}{\text{卖方主动量}}$$

- **Score A ≥ 2.0**：表示买方主动性明显强于卖方
- **高分币种**：可能面临价格上升压力或被主动买入

### 监控阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Score 阈值 | ≥ 2.0 | 最小买卖比率 |
| 24h 体积下限 | 10M USDT | 流动性要求 |
| 24h 体积上限 | 80M USDT | 避免超大单 |

### 窗口类型

- **1h**: 每小时聚合一次
- **4h**: 每 4 小时聚合一次
- **12h**: 每 12 小时聚合一次

## 📡 API 接口 (US2)

### 查询通知记录

```bash
curl "http://localhost:8000/notifications?days=7&symbol=BTCUSDT"
```

响应示例：
```json
{
  "records": [
    {
      "id": 1,
      "symbol": "BTCUSDT",
      "window": "1h",
      "score": 3.45,
      "buy_volume": 50000000,
      "sell_volume": 14492754,
      "timestamp": "2026-02-10T15:51:00Z"
    }
  ],
  "total": 1
}
```

### 导出通知数据

```bash
# JSON 格式
curl "http://localhost:8000/export?days=30&format=json" > notifications.json

# CSV 格式
curl "http://localhost:8000/export?days=30&format=csv" > notifications.csv
```

## 🔧 CLI 工具

### 查看版本

```bash
binance-monitor --version
```

### 导出数据

```bash
# 查看最近 30 天数据
binance-monitor export --days 30

# 按币种导出
binance-monitor export --days 30 --symbol BTCUSDT --format csv

# 指定输出文件
binance-monitor export --days 30 --output data.json
```

### 配置管理 (US3)

```bash
# 查看当前配置
binance-monitor config show

# 修改阈值
binance-monitor config set --score-threshold 2.5 --volume-min 5000000

# 重置为默认值
binance-monitor config reset
```

## 🧪 测试

### 运行所有测试

```bash
pytest -v
```

### 运行特定类别

```bash
# 单元测试
pytest tests/ -v -m "not integration"

# 集成测试
pytest tests/integration/ -v

# 带覆盖率
pytest --cov=src tests/ -v
```

## 📊 监控指标

系统可选集成 Prometheus 监控：

```
# 发送的通知数
binance_notifications_total

# 发送错误数
binance_errors_total

# WebSocket 连接状态
binance_websocket_connected{symbol="BTCUSDT"}

# 数据库操作延迟（毫秒）
binance_db_operation_duration_ms
```

## 🔐 安全注意事项

### 敏感信息保护

- **不要在代码中硬编码 Webhook URL**
- 使用 `.env` 文件或环境变量管理密钥
- 将 `.env` 添加到 `.gitignore`
- 定期轮换 Webhook 密钥

### 数据库安全

- 使用强密码
- 启用 SSL/TLS 连接
- 定期备份数据库
- 限制数据库访问权限

### API 安全

- 启用 HTTPS
- 实现 API 认证
- 设置速率限制
- 记录所有 API 调用

## 🚨 故障排查

### 飞书消息收不到

检查清单：
1. ✅ Webhook URL 是否正确
2. ✅ `SEND_REAL=1` 是否已设置
3. ✅ 飞书群权限是否允许机器人
4. ✅ 检查日志输出

### 数据库连接失败

```bash
# 检查数据库状态
python -c "from src.db import get_engine; engine = get_engine(); print('Connected!' if engine else 'Failed')"
```

### WebSocket 连接断开

系统会自动重连，检查日志中的重试信息。

## 📈 性能优化

### 数据库优化

- 使用索引加速查询
- 定期清理旧数据
- 启用连接池

### 缓存策略

- 缓存热点币种的最近数据
- 使用 Redis（可选）增加效率

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 📧 联系方式

- 问题报告：[GitHub Issues](https://github.com/yourusername/binance-monitor/issues)
- 讨论区：[GitHub Discussions](https://github.com/yourusername/binance-monitor/discussions)
- 邮件：team@example.com

## 🙏 致谢

- [Binance](https://www.binance.com/) - 交易所和数据提供
- [飞书](https://www.feishu.cn/) - 消息通知服务
- [ccxt](https://github.com/ccxt/ccxt) - 加密交易库
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM 框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架

---

**⭐ 如果觉得有帮助，请给个 Star 支持！**
