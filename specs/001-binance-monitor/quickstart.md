# 快速开始指南

本指南帮助您在 5 分钟内启动币安合约监控系统。

## 📋 前置要求

- **Python 3.11+** 或 **Docker**
- **飞书机器人 Webhook** (获取方式见下文)
- 可选：Binance API 密钥（用于真实数据）

## 🚀 快速启动

### 方式 1：本地 Python (推荐开发)

#### Step 1: 克隆与设置

```bash
git clone https://github.com/yourusername/binance-monitor.git
cd binance-monitor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

#### Step 2: 配置环境

```bash
cp .env.example .env
```

编辑 `.env` 填入飞书 Webhook（可选）：

```bash
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id
SEND_REAL=1
```

#### Step 3: 初始化数据库

```bash
python -c "from src.db import init_db; init_db()"
```

#### Step 4: 运行演示

```bash
# 模拟模式（推荐先试）
python scripts/feishu_demo.py

# 真实发送到飞书
python scripts/feishu_demo_real.py --webhook "https://..."
```

### 方式 2：Docker Compose (生产推荐)

```bash
docker-compose up
```

### 方式 3：Docker 单镜像

```bash
docker build -t binance-monitor:latest .
docker run -d -e FEISHU_WEBHOOK="https://..." -e SEND_REAL="1" -p 8000:8000 binance-monitor:latest
```

## 🔑 获取飞书 Webhook

1. 打开飞书群组 → 群信息 → 机器人 → 添加机器人
2. 选择"自定义机器人"
3. 填入机器人名称和描述
4. 点击"创建"，获得 Webhook URL

## ✅ 验证安装

```bash
# 检查 Python 版本
python --version  # 应该是 3.11+

# 检查依赖
python -c "import sqlalchemy, pydantic; print('✓ 依赖正常')"

# 测试飞书通知
python scripts/feishu_demo.py
```

## 🎯 常见任务

### 运行单元测试

```bash
pytest tests/ -v
```

### 查看数据库数据

```bash
sqlite3 binance_monitor.db ".tables"
SELECT * FROM window_metric LIMIT 10;
```

### 修改监控参数

编辑 `.env` 文件：

```bash
SCORE_THRESHOLD=2.5
VOLUME_MIN=5000000
VOLUME_MAX=100000000
DAEMON_INTERVAL_SECONDS=1800
```

## 🐛 故障排查

### Python 依赖冲突

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 飞书消息收不到

检查清单：
1. ✅ Webhook URL 是否正确
2. ✅ SEND_REAL=1 是否已设置
3. ✅ 群组是否允许机器人发送消息

## 📚 更多信息

- [完整文档](../../README.md)
- [飞书配置指南](../../docs/FEISHU_SETUP.md)
- [数据模型](./data-model.md)
- [技术方案](./plan.md)

祝您监控顺利！🎉
