# Research: 币安合约主动买卖量监控（Phase 0）

## 决策汇总

- Decision: 数据采集采用 **WebSocket 实时流 + REST 回补**。
  - Rationale: WebSocket 提供低延迟事件流用于及时统计，REST 用于丢包/回溯和初始全量拉取；混合能确保完整性与可用性。
  - Alternatives considered: 仅 REST（延迟高，API 受限）；仅 WebSocket（需复杂回补与重连策略）。

- Decision: 使用 Python 3.11、`aiohttp`/`websockets`（或 `websocket-client`）做异步客户端，`ccxt` 用于必要的 REST 辅助；持久化首选 `SQLite`（兼容 `SQLAlchemy`），生产建议 `Postgres`。
  - Rationale: Python 生态成熟，`ccxt` 提供统一 REST 接口；`aiohttp` 便于异步 HTTP/WebSocket；`SQLite` 便捷、无运维成本，满足早期需求。

- Decision: secrets 与 Webhook 通过环境变量或本地 `.env`（加入 `.gitignore`）管理；示例使用 `python-dotenv` 或直接从环境中读取。
  - Rationale: 遵循宪章最小权限与不可提交原则；便于 CI/CD 与容器化部署。替代：使用 Vault/Kubernetes Secret（生产）。

- Decision: 通知采用 Feishu Webhook（单一），实现异步发送并带有指数退避重试与幂等去重（请求 ID 与短期缓存）。
  - Rationale: Webhook 简洁，Feishu 支持卡片展示；需控制重试避免重复通知。


## 数据模型与窗口化策略要点（研究摘要）

- 窗口：滑动/对齐窗口 1h、4h、12h（按 UTC 对齐或以服务启动时间对齐均可，但建议对齐到自然时间窗口，例如整点/整 4 小时）。
- 指标：在每个窗口内计算主动 taker 买量与主动 taker 卖量（按成交方向与 `isBuyerMaker` 逻辑判定），得分 A = f(buy_taker, sell_taker)（建议 A = 100 * buy_taker / (buy_taker + sell_taker + ε)）。
- 过滤：仅考虑过去 24h 成交额在 10M–80M USDT 的合约（使用 REST 查询 24h 统计或累积 WebSocket 成交额）。
-  去重/幂等：对每轮检测生成事件 ID（例如：`symbol-window-timestamp`）并在短期缓存（Redis 或 SQLite 表索引）检查以避免重复通知。


## 数据完整性与故障处理

- 重连策略：WebSocket 采用带退避的自动重连（初始 1s，倍增到 32s），并在重连后用 REST 回补丢失区间。
- 速率限制：REST 请求遵守币安 API 限速；批量请求需使用分页与延迟队列（限流器）。
- 时序问题：所有事件使用交易所时间戳（serverTime）进行归档与窗口切分，避免本地时钟偏移导致的窗口错配。
- 数据回放：实现“回放”模块，可用历史采样文件或 REST 拉取的 Kline/Trades 进行本地回放测试。


## 监控与可观测性

- 指标：采集成功率、消息延迟（从交易时间到处理完毕）、重连次数、通知发送成功率、每窗口处理时间分布。
- 日志：结构化日志（JSON），错误带上下文（symbol、window、trace-id）。
- 报警：通知失败率或重连频繁时触发运维告警（可通过 Prometheus + Alertmanager）。


## 安全与合规

- 不在仓库中存储任何具有下单权限的 API keys；生产使用最小权限的只读 keys 或仅使用公共市场数据接口。
- Webhook URL 与 keys 必须通过环境变量/秘密管理器注入；在 `README` 和 `quickstart.md` 中明确配置示例与 `.gitignore` 建议。


## 测试策略

- 单元测试：对窗口化、得分计算与过滤逻辑进行纯函数测试（pytest）。
- 集成测试：使用本地回放数据（保存为 fixtures）对 collector+processor+notifier 流水线进行端到端测试（无真实 webhook 或替换为回显端点）。
- 合规测试：对速率限制与重连策略进行压力测试，验证回补在断连后能恢复数据完整性。


## 备选项与风险评估

- 备选：若希望降低运维复杂度，可使用第三方流平台（如 Kafka + ksql）做窗口聚合，但增加部署复杂度与成本。
- 风险：WebSocket 长连接不稳定可能导致短时间内数据缺失，需可靠回补与恰当的审计记录；通知误报需通过阈值与熔断策略降低。


## 下一步产物（Phase 1 前准备）

- 输出 `data-model.md`：实体（Symbol、WindowMetric、Notification、IngestionEvent）、字段与索引设计。
- 输出 `/contracts/`：HTTP 管理端点（查看历史、重发、健康检查）、通知格式样例（Feishu 卡片 JSON 模板）。

---
Generated on 2026-02-08
