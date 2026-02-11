# 🚀 API 服务器启动脚本快速参考

## 📌 概况

这个脚本 (`manage_api.sh`) 可以方便地管理 API 服务器的启动、停止、重启和日志查看。

## ⚡ 快速命令

| 命令 | 说明 | 用途 |
|------|------|------|
| `./manage_api.sh start` | 启动服务器 | 后台启动 API 服务（第一次使用） |
| `./manage_api.sh stop` | 停止服务器 | 停止已运行的 API 服务 |
| `./manage_api.sh restart` | 重启服务器 | 停止后重新启动 API 服务 |
| `./manage_api.sh status` | 查看状态 | 检查 API 服务是否在运行 |
| `./manage_api.sh logs` | 查看日志 | 实时监控 API 运行日志 |

## 📖 使用示例

### 1️⃣ 首次启动

```bash
# 初始化数据库（仅需一次）
python scripts/init_db.py

# 启动 API 服务器（后台）
./manage_api.sh start

# 验证启动成功
./manage_api.sh status
```

**输出示例：**
```
🚀 启动 API 服务器...
✅ API 服务器已启动 (PID: 12345)
📍 日志位置: logs/api.log
💡 查看日志: tail -f logs/api.log
```

### 2️⃣ 查看实时日志

```bash
./manage_api.sh logs
```

**输出示例：**
```
📋 实时日志 (logs/api.log)，按 Ctrl+C 退出
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 3️⃣ 检查运行状态

```bash
./manage_api.sh status
```

**输出示例（运行中）：**
```
✅ API 服务器正在运行

    PID USER        VSZ   RSS COMMAND
  12345 ubuntu   245216 85320 python
```

**输出示例（未运行）：**
```
❌ API 服务器未运行
```

### 4️⃣ 停止服务

```bash
./manage_api.sh stop
```

**输出示例：**
```
✅ API 服务器已停止 (PID: 12345)
```

### 5️⃣ 重启服务

```bash
./manage_api.sh restart
```

## 🛠️ 故障排除

### 问题 1: "权限被拒绝"

```bash
# 解决方法：给脚本添加执行权限
chmod +x manage_api.sh
```

### 问题 2: 启动失败

```bash
# 查看详细日志
./manage_api.sh logs

# 或者查看上次的日志
cat logs/api.log | tail -50
```

### 问题 3: 端口被占用

```bash
# 查看占用 8000 端口的进程
lsof -i :8000

# 强制停止进程
kill -9 <PID>

# 再试试启动
./manage_api.sh start
```

### 问题 4: 无法找到虚拟环境

脚本会自动查找当前目录下的 `.venv` 虚拟环境。确保：
1. 虚拟环境存在于项目根目录
2. 虚拟环境已正确初始化
3. 依赖已安装：`pip install -r requirements.txt`

## 📋 日志位置

- **日志文件**: `logs/api.log`
- **PID 文件**: `logs/api.pid`（记录进程ID）

### 查看日志的方式

```bash
# 方式 1: 使用脚本（推荐）
./manage_api.sh logs

# 方式 2: 直接查看文件
cat logs/api.log

# 方式 3: 查看最后 100 行
tail -100 logs/api.log

# 方式 4: 按关键字搜索
grep "ERROR" logs/api.log

# 方式 5: 查看文件大小
ls -lah logs/api.log
```

## 🌐 API 访问

启动后，API 服务器在以下地址可用：

```
http://127.0.0.1:8000
```

### 常用 API 端点

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 查询币种
curl http://127.0.0.1:8000/discovery/symbols

# 查看缓存状态
curl http://127.0.0.1:8000/discovery/cache-status

# 运行演示
python scripts/demo_api.py
```

## 📚 更多信息

详情请参考：[RUN_GUIDE.md](RUN_GUIDE.md#🎯-启动脚本管理)

## ✅ 检查清单

在使用脚本之前，确认以下事项：

- [ ] 项目根目录有 `manage_api.sh` 脚本
- [ ] 虚拟环境已创建：`.venv` 目录存在
- [ ] 依赖已安装：`pip install -r requirements.txt`
- [ ] 数据库已初始化：`python scripts/init_db.py`
- [ ] 8000 端口未被占用

---

**问题？** 查看完整的 [RUN_GUIDE.md](RUN_GUIDE.md) 获取更多帮助！
