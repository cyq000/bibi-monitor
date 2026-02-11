# 币种自动发现系统 - 快速参考

## 🚀 启动方式

### 启用自动发现
```bash
export ENABLE_DISCOVERY=true
python -m src.daemon
```

### 禁用自动发现（显式币种）
```bash
export SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
python -m src.daemon
```

---

## 🔍 API 查询命令

### 发现币种
```bash
# 发现所有符合条件的币种
curl "http://localhost:8000/discovery/symbols"

# 限制数量
curl "http://localhost:8000/discovery/symbols?max_symbols=20"

# 不使用缓存
curl "http://localhost:8000/discovery/symbols?use_cache=false"
```

### 查看缓存状态
```bash
curl "http://localhost:8000/discovery/cache-status"
```

### 清除缓存
```bash
curl -X POST "http://localhost:8000/discovery/cache/clear"
```

### 查看排除列表
```bash
curl "http://localhost:8000/discovery/excluded"
```

### 更新排除列表
```bash
curl -X POST "http://localhost:8000/discovery/excluded?symbols=BTCUSDT&symbols=ETHUSDT"
```

---

## ⚙️ 配置修改

### 修改成交额范围
```bash
# 改为 20M - 60M USDT
curl -X POST "http://localhost:8000/config?volume_min=20000000&volume_max=60000000"
```

### 重置为默认配置
```bash
curl -X POST "http://localhost:8000/config/reset"
```

---

## 🧪 测试运行

### 运行演示脚本
```bash
python scripts/demo_discovery.py
```

### 运行单元测试
```bash
pytest tests/test_discovery.py -v
```

### 跳过币种发现单元测试
```bash
pytest tests/test_discovery.py::TestSymbolDiscovery::test_filter_symbols_with_volume_range -v
```

---

## 📊 环境变量配置

```bash
# 启用自动发现
export ENABLE_DISCOVERY=true

# 发现周期（秒）- 默认 86400（24 小时）
export DISCOVERY_INTERVAL=86400

# 成交额范围（USDT）
export VOLUME_MIN=10000000
export VOLUME_MAX=80000000

# 最多监控币种数
export MAX_SYMBOLS=100

# 监控周期（秒）- 默认 3600（1 小时）
export INTERVAL=3600

# 或者直接指定币种列表（禁用自动发现）
export SYMBOLS="BTCUSDT,ETHUSDT"
```

---

## 📝 配置文件示例

编辑 `monitor_config.json`：

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

## 📖 文档

- **详细指南**：`docs/DISCOVERY_GUIDE.md`
- **实现总结**：`DISCOVERY_IMPLEMENTATION_SUMMARY.md`
- **代码**：`src/discovery.py`

---

## ❓ 常见问题

### Q：如何查看发现了多少个币种？
```bash
curl "http://localhost:8000/discovery/symbols" | jq '.count'
```

### Q：如何强制重新发现（跳过缓存）？
```bash
curl -X POST "http://localhost:8000/discovery/cache/clear"
curl "http://localhost:8000/discovery/symbols?use_cache=false"
```

### Q：如何排除某个币种？
```bash
curl -X POST "http://localhost:8000/discovery/excluded?symbols=BTCUSDT"
```

### Q：如何修改成交额范围？
```bash
# 改为 20M - 60M
curl -X POST "http://localhost:8000/config?volume_min=20000000&volume_max=60000000"
```

### Q：如何查看当前配置？
```bash
curl "http://localhost:8000/config" | jq .
```

---

## 🎯 完整示例

```bash
# 1. 启动 API 服务
python -m uvicorn src.api.main:app --reload &

# 2. 发现币种
curl "http://localhost:8000/discovery/symbols"

# 3. 排除前 5 个
curl -X POST "http://localhost:8000/discovery/excluded?symbols=BTCUSDT&symbols=ETHUSDT&symbols=BNBUSDT&symbols=XRPUSDT&symbols=ADAUSDT"

# 4. 查看排除结果
curl "http://localhost:8000/discovery/symbols" | jq '.count'

# 5. 启动监控守护进程
export ENABLE_DISCOVERY=true
python -m src.daemon
```

---

**更新时间**：2026-02-11
