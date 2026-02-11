#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
VENV="$PROJECT_DIR/.venv"
PID_FILE="$LOG_DIR/api.pid"
PORT=8000

# 创建日志目录
mkdir -p "$LOG_DIR"

case "$1" in
  start)
    # 检查进程是否已运行
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "❌ API 服务器已在运行 (PID: $OLD_PID)"
            exit 1
        fi
    fi
    
    echo "🚀 启动 API 服务器..."
    nohup "$VENV/bin/python" -m uvicorn src.api.main:app \
        --host 127.0.0.1 \
        --port $PORT \
        > "$LOG_DIR/api.log" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    
    sleep 1
    
    # 验证启动成功
    if ps -p $NEW_PID > /dev/null 2>&1; then
        echo "✅ API 服务器已启动 (PID: $NEW_PID)"
        echo "📍 日志位置: $LOG_DIR/api.log"
        echo "💡 查看日志: tail -f $LOG_DIR/api.log"
        echo "🌐 访问 API: http://127.0.0.1:8000"
    else
        echo "❌ API 启动失败，请查看日志："
        tail -20 "$LOG_DIR/api.log"
    fi
    ;;
    
  stop)
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
      kill $PID 2>/dev/null && sleep 1
      rm -f "$PID_FILE"
      echo "✅ API 服务器已停止 (PID: $PID)"
    else
      echo "❌ API 服务器未运行"
    fi
    ;;
    
  restart)
    $0 stop
    sleep 2
    $0 start
    ;;
    
  status)
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
      echo "✅ API 服务器正在运行"
      echo ""
      ps -p $PID -o pid,user,vsz,rss,comm
    else
      echo "❌ API 服务器未运行"
    fi
    ;;
    
  logs)
    if [ -f "$LOG_DIR/api.log" ]; then
      echo "📋 实时日志 ($LOG_DIR/api.log)，按 Ctrl+C 退出"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      tail -f "$LOG_DIR/api.log"
    else
      echo "❌ 日志文件不存在: $LOG_DIR/api.log"
      echo "💡 请先运行: ./manage_api.sh start"
    fi
    ;;
    
  *)
    echo "🐍 币安监控系统 - API 服务器管理工具"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "命令说明："
    echo "  start    - 启动 API 服务器（后台运行）"
    echo "  stop     - 停止 API 服务器"
    echo "  restart  - 重启 API 服务器（停止后启动）"
    echo "  status   - 查看服务器运行状态"
    echo "  logs     - 实时查看服务器日志"
    echo ""
    echo "示例："
    echo "  ./manage_api.sh start      # 启动服务器"
    echo "  ./manage_api.sh logs       # 查看日志"
    echo "  ./manage_api.sh status     # 查看状态"
    echo "  ./manage_api.sh stop       # 停止服务器"
    ;;
esac
