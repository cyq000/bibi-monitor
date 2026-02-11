# Data Model: 币安合约主动买卖量监控

## 概览
描述核心实体、字段、关系与索引，便于实现持久化（SQLite/SQLAlchemy / Postgres 兼容）。

## 实体

- Symbol
  - `id` (UUID / integer PK)
  - `symbol` (string, e.g. BTCUSDT, unique)
  - `base_asset` (string)
  - `quote_asset` (string)
  - `contract_type` (enum, e.g. PERPETUAL)
  - `active` (bool)
  - `created_at` (datetime)

- IngestionEvent
  - `id` (UUID / integer PK)
  - `symbol_id` (FK -> Symbol.id)
  - `trade_id` (string) — 交易所在的 trade id
  - `price` (decimal)
  - `quantity` (decimal)
  - `amount_usdt` (decimal) — quantity * price 归一到 USDT
  - `is_buyer_maker` (bool) — 用于判定主动方向
  - `source` (enum: websocket|rest)
  - `exchange_ts` (datetime) — 交易所时间戳
  - `received_at` (datetime) — 本地接收时间
  - Indexes: (`symbol_id`, `exchange_ts`)；按 `exchange_ts` 筛选区间时高效

- WindowMetric
  - `id` (UUID / integer PK)
  - `symbol_id` (FK -> Symbol.id)
  - `window_type` (enum: 1h,4h,12h)
  - `window_start` (datetime)
  - `window_end` (datetime)
  - `buy_taker_volume` (decimal) — 主动买量（数量或金额，建议金额 USDT）
  - `sell_taker_volume` (decimal) — 主动卖量
  - `total_volume` (decimal)
  - `score_a` (decimal) — 归一化得分（0-100）
  - `volume_24h_usdt` (decimal)
  - `computed_at` (datetime)
  - Unique/index: (`symbol_id`,`window_type`,`window_start`) 确保同一窗口仅计算一次

- Notification
  - `id` (UUID / integer PK)
  - `symbol_id` (FK -> Symbol.id)
  - `window_metric_id` (FK -> WindowMetric.id)
  - `event_id` (string) — 例如 `symbol-windowStart-windowType`，用于幂等
  - `payload` (json) — 发送到 Feishu 的卡片/消息体
  - `status` (enum: pending,sent,failed)
  - `attempts` (int)
  - `last_attempted_at` (datetime)
  - `sent_at` (datetime nullable)
  - Indexes: `event_id` 唯一约束，`status` 用于查询待发送/重试


## 关系

- `Symbol` 1 - N `IngestionEvent`
- `Symbol` 1 - N `WindowMetric`
- `WindowMetric` 1 - 1 `Notification`（可为 0..N，根据重试策略）


## 验证与约束

- `buy_taker_volume`, `sell_taker_volume`, `total_volume` >= 0
- `window_end` > `window_start`
- `score_a` 在 0..100 范围内
- `volume_24h_usdt` 用于筛选阈值（>=10,000,000 且 <=80,000,000）


## 保留策略

- `IngestionEvent` 与 `WindowMetric` 保留 90 天（定期清理任务）
- `Notification` 可保留 180 天以便审计


## 索引与查询模式

- 常见查询：
  - 按时间区间获取某符号的交易列表：索引 (`symbol_id`,`exchange_ts`)
  - 获取最新窗口：索引 (`symbol_id`,`window_type`,`window_start`)
  - 幂等检测：在 `Notification.event_id` 上建立唯一索引


## 实现注意事项

- 在 SQLite 下使用 `INTEGER` PK 或 `UUID` 文本均可；在 Postgres 中推荐 `UUID`。
- 聚合：建议在处理管线中使用批量聚合（例如按 symbol 分片），并在计算完成后以事务写入 `WindowMetric` 与创建 `Notification` 记录。

---
Generated on 2026-02-08
