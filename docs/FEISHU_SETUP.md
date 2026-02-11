# 飞书通知配置指南

## 快速开始

您已经成功测试了飞书通知！以下是如何配置和使用的详细说明。

### 方式 1：环境变量（推荐）

#### PowerShell

```powershell
# 设置环境变量并运行演示
$env:FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"
$env:SEND_REAL="1"
python scripts/feishu_demo.py
```

#### Bash

```bash
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"
export SEND_REAL="1"
python scripts/feishu_demo.py
```

#### Python 脚本方式

```bash
python scripts/feishu_demo_real.py --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"
```

### 方式 2：.env 文件配置

1. 复制 `.env.example` 为 `.env`:
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入您的 Webhook：
   ```
   FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id
   SEND_REAL=1
   ```

3. 修改 `src/config.py` 添加 `.env` 加载逻辑（可选）：
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

## 获取飞书 Webhook

### 步骤 1：创建飞书机器人

1. 打开飞书群组
2. 点击群管理 → 群机器人 → 添加机器人
3. 选择"自定义机器人"
4. 填入机器人名称和描述
5. 创建后会获得 Webhook URL

### 步骤 2：测试 Webhook

使用提供的脚本测试：

```bash
# 模拟发送（不需要真实 Webhook）
python scripts/feishu_demo.py

# 真实发送
python scripts/feishu_demo_real.py --webhook "https://..."
```

## 通知卡片格式

系统会发送如下格式的飞书卡片：

```
┌─────────────────────────────────┐
│   币安合约监控告警              │
├─────────────────────────────────┤
│ 币种: BTCUSDT     窗口: 1h       │
│                                 │
│ 买方主动量: 1,234,567 USDT      │
│ 卖方主动量: 456,789 USDT        │
│ ─────────────────────────────   │
│ 得分 A: 2.70 — 满足阈值        │
└─────────────────────────────────┘
```

## 监控阈值配置

### 默认阈值

- **买卖比率 (Score A)**: >= 2.0
- **24小时体积范围**: 10M ~ 80M USDT

### 修改阈值

编辑 `src/processor/ingest_pipeline.py` 的触发判断逻辑：

```python
# 当前配置
if 10_000_000 <= volume_24h <= 80_000_000 and metric['score_a'] >= 2:
    # 触发通知
```

## 重试机制

通知发送支持指数退避重试：

- 最大重试次数: 3 次
- 基础退避时间: 1 秒
- 重试间隔: 1s, 2s, 4s, 8s

实际发送时，如果 Webhook 响应失败，系统会自动重试。

## 幂等性保证

系统通过 `event_id` 确保通知幂等性：

- 每个通知有唯一的 `event_id`: `{symbol}-{timestamp}-{window}`
- 同一 `event_id` 只会发送一次，重复调用会立即返回成功
- 数据库中会记录通知状态：`pending` → `sent`

## 日志示例

成功的通知会产生如下日志：

```
✅ Notifier real send succeeded (event_id=BTCUSDT-2026-02-10T15:51:05.163676-1h, attempt=0)
✅ WindowMetric 已保存 (ID: 18)
✅ 通知已标记为已发送
```

## 常见问题

### Q: 收不到飞书消息？

A: 检查以下几点：
1. Webhook URL 是否正确
2. `SEND_REAL=1` 是否已设置
3. 飞书群权限是否允许机器人发送
4. 查看日志输出是否有错误信息

### Q: 想停止接收通知？

A: 只需删除或禁用飞书群中的机器人即可。

### Q: 想修改通知内容？

A: 编辑 `src/notifier.py` 中的 `build_payload()` 函数：

```python
def build_payload(symbol: str, window: str, buy: float, sell: float, score: float) -> Dict:
    # 修改这里以自定义卡片内容
    return {
        "title": "自定义标题",
        "msg_type": "interactive",
        "card": {
            # 自定义卡片结构...
        }
    }
```

## 生产环境配置

### 安全建议

1. **不要在代码中硬编码 Webhook**
   - 使用环境变量或密钥管理系统

2. **保护 .env 文件**
   - 添加到 `.gitignore`
   - 不要提交到版本控制

3. **监控 Webhook 健康状况**
   - 记录发送成功率
   - 设置告警阈值

4. **速率限制**
   - 飞书 Webhook 有速率限制（约 10 请求/秒）
   - 生产环境应实现消息队列以避免限流

### 示例 .gitignore 配置

```
.env
.env.local
.env.*.local
*.db
*.log
__pycache__/
.venv/
```

## 下一步

- ✅ 已完成：飞书通知的完整实现和演示
- ⏳ 待实现：HTTP API 导出接口 (US2)
- ⏳ 待实现：可配置阈值 (US3)
- ⏳ 待实现：持久化清理和告警 (Polish)

