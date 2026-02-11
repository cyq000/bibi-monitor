# 币种自动发现系统

## 概述

币种自动发现系统是一个动态币种管理功能，它允许系统自动从币安获取所有币种，根据 24h **成交额范围** 自动过滤符合条件的币种，并用于实时监控。

**核心优势**：
- ✅ **自动化**：无需手动配置币种列表
- ✅ **动态性**：支持定期发现新币种
- ✅ **灵活性**：支持排除列表和自定义范围
- ✅ **高效**：智能缓存机制减少 API 调用

---

## 快速开始

### 方式 1：启用守护进程自动发现（推荐）

```bash
# 启用自动发现，每 24 小时发现一次
export ENABLE_DISCOVERY=true
export DISCOVERY_INTERVAL=86400

# 启动守护进程
python -m src.daemon
```

**日志输出示例**：
```
[INFO] 自动币种发现已启用，发现周期：86400s
[INFO] 开始监控周期，监控币种：['BTCUSDT', 'ETHUSDT', 'BNBUSDT', ...] (共 42 个)
[INFO] 监控周期完成，等待 3600s 后开始下一周期
```

### 方式 2：使用手动发现接口

```bash
# 立即发现符合条件的币种
curl "http://localhost:8000/discovery/symbols"

# 限制最多 20 个币种
curl "http://localhost:8000/discovery/symbols?max_symbols=20"

# 不使用缓存，强制从币安 API 重新获取
curl "http://localhost:8000/discovery/symbols?use_cache=false"
```

**响应示例**：
```json
{
  "symbols": [
    "BTCUSDT",
    "ETHUSDT", 
    "BNBUSDT",
    "WLFIUSDT",
    ...
  ],
  "count": 42,
  "cache_used": true,
  "cache_status": {
    "cached": true,
    "count": 42,
    "cached_at": "2026-02-11T10:30:45.123456",
    "ttl_seconds": 3600,
    "remaining_seconds": 2800
  }
}
```

### 方式 3：编程使用

```python
import asyncio
from src.discovery import discover_symbols_for_monitoring

async def main():
    # 发现符合条件的币种
    symbols = await discover_symbols_for_monitoring()
    print(f"发现的币种：{symbols}")
    
    # 限制数量
    top_20 = await discover_symbols_for_monitoring(max_symbols=20)
    print(f"前 20 个币种：{top_20}")

asyncio.run(main())
```

---

## 工作原理

### 币种过滤条件

系统有 3 个过滤条件：

| 条件 | 默认值 | 含义 |
|------|--------|------|
| **volume_min** | 10,000,000 | 最小 24h 成交额（USDT）|
| **volume_max** | 80,000,000 | 最大 24h 成交额（USDT）|
| **市场类型** | USDT | 仅监控 USDT 币对 |

**示例**：
- ✅ `WLFIUSDT`: 24h 成交额 = 35M USDT → **符合条件**
- ✅ `ETHUSDT`: 24h 成交额 = 45M USDT → **符合条件**
- ❌ `BTCUSDT`: 24h 成交额 = 200M USDT → **超出上限**
- ❌ `SHITCOINUSDT`: 24h 成交额 = 2M USDT → **低于下限**

### 缓存机制

为了减少对币安 API 的调用，系统使用 **1 小时的缓存**：

```
首次发现（t=0s）→ API 获取 → 缓存数据 ✓
二次发现（t=30s）→ 使用缓存 ✓（10 ms）
三次发现（t=3600s+）→ 缓存过期 → API 重新获取
```

### 排除列表

可以将某些币种从发现结果中排除：

```python
from src.discovery import get_symbol_discovery

discoverer = get_symbol_discovery()
discoverer.set_excluded_symbols(["BTCUSDT", "ETHUSDT"])

# 或通过 API
```

---

## 配置参数

### 环境变量

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `ENABLE_DISCOVERY` | bool | `true` | 是否启用自动发现 |
| `DISCOVERY_INTERVAL` | int | `86400` | 发现周期（秒），默认 24 小时 |
| `VOLUME_MIN` | int | `10000000` | 最小成交额（USDT）|
| `VOLUME_MAX` | int | `80000000` | 最大成交额（USDT）|
| `MAX_SYMBOLS` | int | - | 最多监控多少个币种（无限制） |
| `SYMBOLS` | str | - | 逗号分隔的币种列表（指定则禁用发现）|

### 配置文件 (`monitor_config.json`)

```json
{
  "volume_min": 10000000,
  "volume_max": 80000000,
  "enable_discovery": true,
  "discovery_interval_seconds": 86400,
  "discovery_excluded_symbols": ["BTCUSDT"],
  "discovery_max_symbols": null
}
```

---

## API 端点

### 1. 发现币种

**请求**：
```bash
GET /discovery/symbols?max_symbols=50&use_cache=true
```

**参数**：
- `max_symbols` (int, optional): 最多返回多少个币种
- `use_cache` (bool): 是否使用缓存

**响应**：
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", ...],
  "count": 42,
  "cache_used": true,
  "cache_status": {...}
}
```

### 2. 清除缓存

**请求**：
```bash
POST /discovery/cache/clear
```

**响应**：
```json
{
  "status": "success",
  "message": "币种发现缓存已清除"
}
```

### 3. 获取排除列表

**请求**：
```bash
GET /discovery/excluded
```

**响应**：
```json
{
  "excluded_symbols": ["BTCUSDT", "ETHUSDT"],
  "count": 2
}
```

### 4. 更新排除列表

**请求**：
```bash
POST /discovery/excluded?symbols=BTCUSDT&symbols=ETHUSDT
```

**响应**：
```json
{
  "status": "success",
  "excluded_symbols": ["BTCUSDT", "ETHUSDT"],
  "count": 2,
  "message": "排除列表已更新，发现缓存已清除"
}
```

### 5. 查看缓存状态

**请求**：
```bash
GET /discovery/cache-status
```

**响应**：
```json
{
  "cached": true,
  "count": 42,
  "cached_at": "2026-02-11T10:30:45.123456",
  "ttl_seconds": 3600,
  "remaining_seconds": 2800
}
```

### 6. 修改成交额范围

**请求**：
```bash
POST /config?volume_min=20000000&volume_max=60000000
```

修改后会影响下一次发现的结果。

---

## 部署建议

### 生产环境配置

```bash
# 启用自动发现，24 小时发现一次
docker run -e ENABLE_DISCOVERY=true \
           -e DISCOVERY_INTERVAL=86400 \
           -e VOLUME_MIN=10000000 \
           -e VOLUME_MAX=80000000 \
           bibi:latest python -m src.daemon
```

### 分阶段部署

**阶段 1**：使用固定币种列表（保持现状）
```bash
export SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
python -m src.daemon
```

**阶段 2**：启用自动发现，每 24 小时发现一次
```bash
export ENABLE_DISCOVERY=true
export DISCOVERY_INTERVAL=86400
python -m src.daemon
```

**阶段 3**：实时自动发现（高级）
```bash
export ENABLE_DISCOVERY=true
export DISCOVERY_INTERVAL=3600  # 每小时发现一次
export MAX_SYMBOLS=100
python -m src.daemon
```

---

## 脚本示例

### 演示脚本

```bash
# 运行完整演示
python scripts/demo_discovery.py
```

演示内容包括：
- ✓ 基本币种发现
- ✓ 缓存功能
- ✓ 限制币种数量
- ✓ 排除列表
- ✓ 配置系统集成

### 测试脚本

```bash
# 运行单元测试
pytest tests/test_discovery.py -v

# 运行测试覆盖率分析
pytest tests/test_discovery.py --cov=src.discovery --cov-report=html
```

---

## 常见问题

### Q1: 如何修改成交额范围？

**方法 1**：环境变量
```bash
export VOLUME_MIN=20000000
export VOLUME_MAX=60000000
```

**方法 2**：API
```bash
curl -X POST "http://localhost:8000/config?volume_min=20000000&volume_max=60000000"
```

**方法 3**：配置文件
```json
{
  "volume_min": 20000000,
  "volume_max": 60000000
}
```

### Q2: 发现的币种为什么没有变化？

检查缓存：
```bash
# 查看缓存状态
curl "http://localhost:8000/discovery/cache-status"

# 清除缓存后重新发现
curl -X POST "http://localhost:8000/discovery/cache/clear"
curl "http://localhost:8000/discovery/symbols?use_cache=false"
```

### Q3: 如何排除某个币种？

```bash
# 通过 API 排除
curl -X POST "http://localhost:8000/discovery/excluded?symbols=BTCUSDT&symbols=ETHUSDT"

# 或在配置文件中
{
  "discovery_excluded_symbols": ["BTCUSDT", "ETHUSDT"]
}
```

### Q4: 发现过程需要多长时间？

- **首次发现**：2-5 秒（调用币安 API）
- **缓存命中**：< 100 毫秒
- **缓存过期后**：2-5 秒（重新调用 API）

### Q5: 支持哪些交易市场？

目前仅支持 **USDT 永续合约**（币对以 `USDT` 结尾），例如：
- ✓ `BTCUSDT`, `ETHUSDT`, `BNBUSDT`
- ❌ `BTCBUSD`, `BTCUSDC`, `BTCETH`

---

## 技术实现

### 核心模块

**`src/discovery.py`** - 币种发现器
- `SymbolDiscovery` 类：主要的发现逻辑
- `discover_symbols_for_monitoring()` 函数：异步发现接口
- `get_symbol_discovery()` 函数：全局实例获取

### 集成点

1. **守护进程** (`src/daemon.py`)
   - `discover_and_run_daemon()` - 支持自动发现的守护进程
   
2. **API 层** (`src/api/main.py`)
   - 5 个币种发现相关的 REST 端点
   
3. **配置系统** (`src/config_manager.py`)
   - 发现相关的配置参数管理

---

## 性能指标

| 操作 | 耗时 | 备注 |
|------|------|------|
| 币安 API 请求 | 2-5s | 首次或缓存失效 |
| 缓存命中 | < 100ms | 内存查询 |
| 币种过滤 | < 50ms | 纯内存操作 |
| 总体发现时间 | 2-5s | 取决于缓存状态 |

---

## 故障排查

### 症状：发现结果为空

**排查步骤**：
1. 检查配置范围是否过于严格
   ```bash
   curl "http://localhost:8000/config" | grep -E "volume_min|volume_max"
   ```

2. 检查排除列表
   ```bash
   curl "http://localhost:8000/discovery/excluded"
   ```

3. 强制重新发现
   ```bash
   curl -X POST "http://localhost:8000/discovery/cache/clear"
   curl "http://localhost:8000/discovery/symbols?use_cache=false"
   ```

### 症状：API 调用超时

**原因**：币安 API 响应缓慢
**解决**：
1. 检查网络连接
2. 使用缓存数据
3. 增加超时时间

---

## 更新历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.2.0 | 2026-02-11 | 新增币种自动发现系统 |
| 0.1.0 | 2026-02-10 | 初始版本 |
