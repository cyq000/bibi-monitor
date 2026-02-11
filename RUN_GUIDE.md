# 币种自动发现系统 - 运行指南

**快速版本:** 如果你只想快速跑起来，请看 [快速开始](#快速开始)  
**详细版本:** 如果你想了解所有选项，请看 [完整运行指南](#完整运行指南)

---

## 🚀 快速开始

### 方式 1: 只启动 API 服务器（推荐新手）

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

然后打开另一个终端，测试：
```bash
# 发现币种
curl http://127.0.0.1:8000/discovery/symbols

# 查看缓存状态
curl http://127.0.0.1:8000/discovery/cache-status

# 查看排除列表
curl http://127.0.0.1:8000/discovery/excluded
```

或者用 Python 运行演示：
```bash
python scripts/demo_api.py
```

**效果:** 
- ✓ API 服务器在 8000 端口运行
- ✓ 可以查询自动发现的币种
- ✓ 缓存工作正常

---

### 方式 2: 启动完整系统（推荐生产）

```bash
# 终端 1: 启动 API 服务器
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 终端 2: 启动自动发现守护进程
python -m src --daemon --discover
```

**效果:**
- ✓ API 服务器在 8000 端口运行（其他应用可访问）
- ✓ 后台守护进程每 24 小时自动发现一次币种
- ✓ 自自动收集和存储数据

---

## 📋 完整运行指南

### 前置条件

确保你已有：
1. Python 3.11+ （检查: `python --version`）
2. 项目依赖已安装 （检查: 项目能导入 `requests`, `fastapi`, `sqlalchemy` 等）
3. 数据库已初始化

### 初始化（首次运行）

```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 检查配置
python scripts/check_config.py
```

### 运行模式

#### 📍 模式 1: 仅 API 服务器

适用于：开发、测试、API 查询

```bash
# 基础启动
python -m uvicorn src.api.main:app --port 8000

# 带实时重载（开发）
python -m uvicorn src.api.main:app --port 8000 --reload

# 生产级别（多进程）
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 自定义日志级别
python -m uvicorn src.api.main:app --port 8000 --log-level warning
```

**测试 API:**
```bash
# 发现币种
curl http://localhost:8000/discovery/symbols

# 查看缓存
curl http://localhost:8000/discovery/cache-status

# 运行演示
python scripts/demo_api.py
```

---

#### 📍 模式 2: 自动发现守护进程

适用于：全自动监控、24/7 运行

```bash
# 基础启动
python -m src --daemon --discover

# 指定配置文件
python -m src --daemon --discover --config monitor_config.json

# 调试模式（输出详细日志）
python -m src --daemon --discover --log-level DEBUG
```

**工作原理:**
- 首次启动：立即执行一次币种发现
- 之后：每 24 小时自动发现一次（可在 `discovery_interval_seconds` 中配置）
- 发现的币种自动添加到监控列表
- 与 IngestPipeline 同步，持续收集数据

---

#### 📍 模式 3: API + Daemon 完整系统（推荐）

适用于：生产环境

**启动脚本方案：**

创建 `start.sh` (Linux/Mac) 或 `start.bat` (Windows)

Linux/Mac:
```bash
#!/bin/bash

# 启动 API 服务器（后台）
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# 启动守护进程（前台）
python -m src --daemon --discover

# 如果守护进程退出，关闭 API
kill $API_PID
```

Windows PowerShell:
```powershell
# 启动 API 服务器（后台）
Start-Process python -ArgumentList "-m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

# 启动守护进程（前台）
python -m src --daemon --discover
```

**运行：**
```bash
# Linux/Mac
chmod +x start.sh
./start.sh

# Windows
.\start.bat
```

---

#### 📍 模式 4: 手动发现单次

适用于：测试、手动触发发现

```bash
# 直接调用发现模块
python << 'EOF'
import asyncio
from src.discovery import SymbolDiscovery

async def main():
    discovery = SymbolDiscovery()
    symbols = await discovery.discover_symbols(use_cache=False)
    print(f"发现 {len(symbols)} 个币种:")
    for symbol in symbols[:10]:
        print(f"  - {symbol}")

asyncio.run(main())
EOF
```

---

### 🔧 常用操作

#### 清除缓存

```bash
# 方式 1: 通过 API
curl -X POST http://localhost:8000/discovery/cache/clear

# 方式 2: 通过命令行
python << 'EOF'
from src.discovery import get_symbol_discovery
discovery = get_symbol_discovery()
discovery.clear_cache()
print("缓存已清除")
EOF
```

#### 查看排除列表

```bash
curl http://localhost:8000/discovery/excluded
```

#### 添加排除项

```bash
# 排除 BTCUSDT 和 ETHUSDT
curl -X POST http://localhost:8000/discovery/excluded \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["BTCUSDT", "ETHUSDT"]}'
```

#### 修改配置

```bash
# 方式 1: 编辑 monitor_config.json
# vi monitor_config.json

# 方式 2: 通过环境变量
export ENABLE_DISCOVERY=true
export DISCOVERY_INTERVAL_SECONDS=3600  # 改为 1 小时
export DISCOVERY_MAX_SYMBOLS=50

# 方式 3: 通过 API POST 请求
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"volume_min": 15000000, "volume_max": 75000000}'
```

---

### 📊 监控和管理

#### 查看系统日志

```bash
# API 服务器日志通常直接输出到终端

# 如果后台运行，查看日志：
tail -f logs/api.log      # API 日志
tail -f logs/daemon.log   # Daemon 日志
```

#### 检查健康状态

```bash
# API 服务器健康检查
curl http://localhost:8000/health

# 发现系统状态
curl http://localhost:8000/discovery/cache-status

# 统计信息
curl http://localhost:8000/stats?days=7
```

#### 性能监控

```bash
# 使用 demo 脚本测试性能
python scripts/demo_api.py

# 观察响应时间（应该在 5ms 以内）
```

---

### ⚙️ 环境变量配置

```bash
# 发现系统相关
export ENABLE_DISCOVERY=true                    # 启用自动发现
export DISCOVERY_INTERVAL_SECONDS=86400        # 发现周期（秒，默认 24小时）
export DISCOVERY_MAX_SYMBOLS=100               # 最多发现币种数
export DISCOVERY_EXCLUDED_SYMBOLS=BTCUSDT,ETHUSDT  # 排除列表

# API 服务器相关
export API_HOST=0.0.0.0                        # 监听地址
export API_PORT=8000                           # 监听端口
export API_WORKERS=4                           # 工作进程数

# 日志级别
export LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR

# 数据库
export DATABASE_URL=sqlite:///bibi.db           # 数据库连接串
```

---

## 🧪 测试

### 运行单元测试

```bash
# 所有测试
pytest tests/ -v

# 仅发现相关测试
pytest tests/test_discovery.py -v

# 单个测试
pytest tests/test_discovery.py::test_filter_volume_range -v
```

### 运行集成测试

```bash
# 完整的端到端测试
pytest tests/integration/ -v
```

### 性能测试

```bash
python << 'EOF'
import time
import requests

BASE = "http://127.0.0.1:8000"
times = []

for i in range(100):
    start = time.time()
    requests.get(f"{BASE}/discovery/symbols")
    times.append((time.time() - start) * 1000)

print(f"平均: {sum(times)/len(times):.2f}ms")
print(f"最快: {min(times):.2f}ms")
print(f"最慢: {max(times):.2f}ms")
EOF
```

---

## 📝 故障排除

### 问题: 端口 8000 已被占用

```bash
# 找出占用端口的进程
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# 改用其他端口
python -m uvicorn src.api.main:app --port 8001
```

### 问题: Binance API 超时

```
WARNING: 获取币安数据失败，使用模拟数据
```

这是正常的! 系统有灰度降级机制：
- 无法访问 Binance API → 使用模拟数据
- 演示仍能正常运行
- 下次发现周期会自动重试

### 问题: 缓存中币种太少或太多

编辑 `monitor_config.json`:
```json
{
  "volume_min": 10000000,      // 降低最小值发现更多币种
  "volume_max": 80000000,      // 提高最大值发现更多币种
  "discovery_max_symbols": 50  // 限制结果数量
}
```

### 问题: 依赖缺失

```bash
# 重新安装依赖
pip install -r requirements.txt

# 或具体安装
pip install fastapi uvicorn sqlalchemy aiohttp requests
```

---

## 📚 相关文档

| 文档 | 用途 |
|------|------|
| [docs/DISCOVERY_GUIDE.md](docs/DISCOVERY_GUIDE.md) | 详细功能说明 |
| [docs/DISCOVERY_QUICK_REFERENCE.md](docs/DISCOVERY_QUICK_REFERENCE.md) | API 快速参考 |
| [FINAL_PROJECT_SUMMARY.md](FINAL_PROJECT_SUMMARY.md) | 项目完成总结 |
| [REAL_RUNTIME_DEMO_RESULTS.md](REAL_RUNTIME_DEMO_RESULTS.md) | 真实运行结果 |

---

## 🎯 推荐流程

### 首次运行

```bash
# 1. 初始化数据库
python scripts/init_db.py

# 2. 启动 API 服务器
python -m uvicorn src.api.main:app --port 8000

# 3. 在另一个终端运行演示
python scripts/demo_api.py

# 4. 查看效果
```

### 生产部署

```bash
# 1. 初始化数据库（如未初始化）
python scripts/init_db.py

# 2. 启动 API 服务器（后台）
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4 &

# 3. 启动守护进程
python -m src --daemon --discover

# 4. 监控日志
tail -f logs/*.log
```

### 开发调试

```bash
# 1. 启动开发 API 服务器（支持热重载）
python -m uvicorn src.api.main:app --port 8000 --reload

# 2. 在另一个终端调试
python -c "..."

# 3. 修改代码，服务器自动重启
```

---

## ✅ 检查清单

运行前确认：
- [ ] Python 3.11+ 已安装
- [ ] 项目依赖已安装 (`pip install -r requirements.txt`)
- [ ] 配置文件 `monitor_config.json` 存在
- [ ] 数据库已初始化（至少需要运行一次 `init_db.py`）
- [ ] 8000 端口未被占用（或使用 `--port` 指定其他端口）

运行后验证：
- [ ] API 服务器成功启动（看到 `Application startup complete`)
- [ ] 能成功调用 `/discovery/symbols` 端点
- [ ] 能查看缓存状态 `/discovery/cache-status`
- [ ] 演示脚本能成功运行 `python scripts/demo_api.py`

---

**准备好了？选择上面适合你的运行方式，开始吧！** 🚀
