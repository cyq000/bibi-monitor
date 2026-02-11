"""FastAPI 应用：提供通知查询和导出 API 端点"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import json
import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional, Literal, Dict, Any

from src.storage import storage
from src.db import get_engine
from src.config_manager import get_config_manager
from src.discovery import discover_symbols_for_monitoring, get_symbol_discovery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from src.models import Notification, WindowMetric, Symbol

# 初始化 FastAPI 应用
app = FastAPI(
    title="币安合约监控 API",
    description="查询、导出和配置管理的 RESTful API",
    version="0.1.0",
    tags_metadata=[
        {"name": "监控", "description": "系统健康检查"},
        {"name": "查询", "description": "查询通知记录"},
        {"name": "导出", "description": "导出数据为 JSON/CSV"},
        {"name": "统计", "description": "获取统计信息"},
        {"name": "配置", "description": "管理监控阈值和参数"},
        {"name": "币种发现", "description": "动态发现符合条件的币种"},
    ],
)

SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


@app.get("/health", tags=["监控"])
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/notifications", tags=["查询"])
async def list_notifications(
    days: int = Query(7, ge=1, le=90, description="查询最近 N 天的通知"),
    symbol: Optional[str] = Query(None, description="按币种过滤（如 BTCUSDT）"),
    status: Optional[str] = Query(None, description="按状态过滤（pending/sent/failed）"),
    limit: int = Query(100, ge=1, le=1000, description="返回数据条数上限"),
):
    """
    查询通知记录

    ### 参数
    - **days**: 查询最近 N 天（默认 7 天）
    - **symbol**: 按币种过滤，如 BTCUSDT
    - **status**: 按通知状态过滤
    - **limit**: 返回数据条数上限（最多 1000）

    ### 返回示例
    ```json
    {
      "records": [
        {
          "id": 1,
          "symbol": "BTCUSDT",
          "event_id": "BTCUSDT-2026-02-10T15:51:00-1h",
          "status": "sent",
          "attempts": 1,
          "sent_at": "2026-02-10T15:51:06Z",
          "window_metric": {
            "id": 18,
            "window_type": "1h",
            "score_a": 100.0,
            "buy_volume": 72000.0,
            "sell_volume": 0.0,
            "volume_24h": 30000000
          }
        }
      ],
      "total": 1,
      "query_date": "2026-02-10T15:51:00Z"
    }
    ```
    """
    session = SessionLocal()
    try:
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        # 构建查询条件
        query = session.query(Notification)

        # 按时间过滤
        query = query.filter(Notification.created_at >= start_time)

        # 按币种过滤
        if symbol:
            sym = session.query(Symbol).filter_by(symbol=symbol).first()
            if sym:
                query = query.filter(Notification.symbol_id == sym.id)
            else:
                return {"records": [], "total": 0, "query_date": datetime.utcnow().isoformat()}

        # 按状态过滤
        if status:
            query = query.filter(Notification.status == status)

        # 排序并限制
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

        # 构建响应数据
        records = []
        for notif in notifications:
            record = {
                "id": notif.id,
                "symbol": session.query(Symbol).filter_by(id=notif.symbol_id).first().symbol if notif.symbol_id else None,
                "event_id": notif.event_id,
                "status": notif.status,
                "attempts": notif.attempts,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
            }

            # 关联的 WindowMetric 数据
            if notif.window_metric_id:
                wm = session.query(WindowMetric).filter_by(id=notif.window_metric_id).first()
                if wm:
                    record["window_metric"] = {
                        "id": wm.id,
                        "window_type": wm.window_type,
                        "window_start": wm.window_start.isoformat(),
                        "window_end": wm.window_end.isoformat(),
                        "score_a": float(wm.score_a),
                        "buy_volume": float(wm.buy_taker_volume),
                        "sell_volume": float(wm.sell_taker_volume),
                        "volume_24h": float(wm.volume_24h_usdt) if wm.volume_24h_usdt else None,
                    }

            records.append(record)

        return {
            "records": records,
            "total": len(records),
            "query_days": days,
            "symbol_filter": symbol,
            "status_filter": status,
            "query_time": datetime.utcnow().isoformat(),
        }

    finally:
        session.close()


@app.get("/export", tags=["导出"])
async def export_notifications(
    days: int = Query(30, ge=1, le=90, description="导出最近 N 天的数据"),
    symbol: Optional[str] = Query(None, description="按币种过滤"),
    format: Literal["json", "csv"] = Query("json", description="导出格式"),
):
    """
    导出通知历史

    ### 参数
    - **days**: 导出最近 N 天（默认 30 天）
    - **symbol**: 按币种过滤（如 BTCUSDT）
    - **format**: 导出格式（json/csv）

    ### 返回
    - **json**: 返回 JSON 文件
    - **csv**: 返回 CSV 文件
    """
    session = SessionLocal()
    try:
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        # 构建查询条件
        query = session.query(Notification)
        query = query.filter(Notification.created_at >= start_time)

        # 按币种过滤
        if symbol:
            sym = session.query(Symbol).filter_by(symbol=symbol).first()
            if sym:
                query = query.filter(Notification.symbol_id == sym.id)
            else:
                query = query.filter(False)  # 返回空结果

        notifications = query.order_by(Notification.created_at).all()

        # 构建数据
        data = []
        for notif in notifications:
            sym_name = session.query(Symbol).filter_by(id=notif.symbol_id).first().symbol if notif.symbol_id else "N/A"
            row = {
                "id": notif.id,
                "symbol": sym_name,
                "event_id": notif.event_id,
                "status": notif.status,
                "attempts": notif.attempts,
                "created_at": notif.created_at.isoformat() if notif.created_at else "",
                "sent_at": notif.sent_at.isoformat() if notif.sent_at else "",
            }

            # 添加 WindowMetric 信息
            if notif.window_metric_id:
                wm = session.query(WindowMetric).filter_by(id=notif.window_metric_id).first()
                if wm:
                    row.update({
                        "window_type": wm.window_type,
                        "window_start": wm.window_start.isoformat(),
                        "window_end": wm.window_end.isoformat(),
                        "score_a": float(wm.score_a),
                        "buy_volume": float(wm.buy_taker_volume),
                        "sell_volume": float(wm.sell_taker_volume),
                        "volume_24h": float(wm.volume_24h_usdt) if wm.volume_24h_usdt else None,
                    })

            data.append(row)

        # 根据格式导出
        if format == "json":
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            return StreamingResponse(
                io.BytesIO(json_data.encode("utf-8")),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=notifications_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"},
            )

        elif format == "csv":
            # 构建 CSV
            output = io.StringIO()
            if data:
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            csv_content = output.getvalue()
            return StreamingResponse(
                io.BytesIO(csv_content.encode("utf-8")),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=notifications_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"},
            )

        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

    finally:
        session.close()


@app.get("/stats", tags=["统计"])
async def statistics(
    days: int = Query(30, ge=1, le=90, description="统计最近 N 天"),
):
    """
    获取通知统计信息

    ### 返回示例
    ```json
    {
      "period_days": 30,
      "total_notifications": 45,
      "sent_count": 43,
      "failed_count": 2,
      "success_rate": 0.956,
      "symbols": {
        "BTCUSDT": 15,
        "ETHUSDT": 12,
        "ADAUSDT": 18
      }
    }
    ```
    """
    session = SessionLocal()
    try:
        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        # 统计总数
        total = session.query(Notification).filter(
            Notification.created_at >= start_time
        ).count()

        # 按状态统计
        sent_count = session.query(Notification).filter(
            and_(Notification.created_at >= start_time, Notification.status == "sent")
        ).count()

        failed_count = session.query(Notification).filter(
            and_(Notification.created_at >= start_time, Notification.status == "failed")
        ).count()

        # 按币种统计
        notifications = session.query(Notification, Symbol).join(
            Symbol, Notification.symbol_id == Symbol.id
        ).filter(Notification.created_at >= start_time).all()

        symbol_counts = {}
        for notif, symbol in notifications:
            symbol_counts[symbol.symbol] = symbol_counts.get(symbol.symbol, 0) + 1

        success_rate = sent_count / total if total > 0 else 0

        return {
            "period_days": days,
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "total_notifications": total,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "pending_count": total - sent_count - failed_count,
            "success_rate": round(success_rate, 4),
            "symbols": symbol_counts,
        }

    finally:
        session.close()


@app.get("/config", tags=["配置"])
async def get_config():
    """
    查看当前配置

    ### 返回示例
    ```json
    {
      "score_threshold": 2.0,
      "volume_min": 10000000,
      "volume_max": 80000000,
      "per_symbol_thresholds": {}
    }
    ```
    """
    cfg = get_config_manager()
    return cfg.show()


@app.post("/config", tags=["配置"])
async def update_config(
    score_threshold: Optional[float] = Query(None, ge=0.1, le=100.0, description="买卖比率阈值"),
    volume_min: Optional[int] = Query(None, ge=100_000, description="最小 24h 体积"),
    volume_max: Optional[int] = Query(None, ge=1_000_000, description="最大 24h 体积"),
):
    """
    更新全局配置

    ### 参数
    - **score_threshold**: 买卖比率阈值（0.1-100.0）
    - **volume_min**: 最小 24h 体积 USDT
    - **volume_max**: 最大 24h 体积 USDT

    注意：volume_min 必须小于 volume_max
    """
    cfg = get_config_manager()
    
    try:
        if score_threshold is not None:
            cfg.set("score_threshold", score_threshold)
        
        if volume_min is not None:
            cfg.set("volume_min", volume_min)
        
        if volume_max is not None:
            cfg.set("volume_max", volume_max)
        
        cfg.save()
        return {"status": "success", "config": cfg.show()}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/config/symbol/{symbol}", tags=["配置"])
async def update_symbol_config(
    symbol: str,
    score_threshold: Optional[float] = Query(None, ge=0.1, le=100.0),
    volume_min: Optional[int] = Query(None, ge=100_000),
    volume_max: Optional[int] = Query(None, ge=1_000_000),
):
    """
    更新特定币种的配置

    ### 参数
    - **symbol**: 币种（如 BTCUSDT）
    - **score_threshold**: 该币种的买卖比率阈值
    - **volume_min**: 该币种的最小体积
    - **volume_max**: 该币种的最大体积
    """
    cfg = get_config_manager()
    
    kwargs = {}
    if score_threshold is not None:
        kwargs["score_threshold"] = score_threshold
    if volume_min is not None:
        kwargs["volume_min"] = volume_min
    if volume_max is not None:
        kwargs["volume_max"] = volume_max
    
    if kwargs:
        cfg.set_symbol_threshold(symbol, **kwargs)
        cfg.save()
    
    return {
        "status": "success",
        "symbol": symbol,
        "threshold": cfg.get_threshold_for_symbol(symbol).dict(),
    }


@app.get("/config/symbol/{symbol}", tags=["配置"])
async def get_symbol_config(symbol: str):
    """
    查看特定币种的阈值配置

    ### 返回
    该币种的阈值配置（如果未单独配置，返回全局默认值）
    """
    cfg = get_config_manager()
    threshold = cfg.get_threshold_for_symbol(symbol)
    
    return {
        "symbol": symbol,
        "threshold": threshold.dict(),
        "note": "使用全局默认值" if symbol not in cfg.get("per_symbol_thresholds", {}) else "使用币种专用配置",
    }


@app.get("/discovery/symbols", tags=["币种发现"])
async def discover_symbols(
    max_symbols: Optional[int] = Query(None, ge=1, le=1000, description="最多返回多少个币种"),
    use_cache: bool = Query(True, description="是否使用缓存的数据"),
):
    """
    发现符合条件的币种

    动态从币安获取所有币种，根据 24h 成交额范围过滤符合条件的币种。

    ### 参数
    - **max_symbols**: 最多返回多少个币种（默认不限制）
    - **use_cache**: 是否使用缓存的数据（缓存有效期 1 小时）

    ### 返回示例
    ```json
    {
      "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", ...],
      "count": 42,
      "cache_used": true,
      "cache_status": {
        "cached": true,
        "remaining_seconds": 3500
      }
    }
    ```
    """
    try:
        symbols = await discover_symbols_for_monitoring(
            max_symbols=max_symbols,
            use_cache=use_cache
        )
        
        discoverer = get_symbol_discovery()
        cache_status = discoverer.get_cache_status()
        
        return {
            "symbols": symbols,
            "count": len(symbols),
            "cache_used": use_cache and cache_status["cached"],
            "cache_status": cache_status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"币种发现失败：{str(e)}")


@app.post("/discovery/cache/clear", tags=["币种发现"])
async def clear_discovery_cache():
    """
    清除币种发现缓存

    下一次发现请求将从币安 API 重新获取数据。
    """
    discoverer = get_symbol_discovery()
    discoverer.clear_cache()
    
    return {
        "status": "success",
        "message": "币种发现缓存已清除",
    }


@app.get("/discovery/excluded", tags=["币种发现"])
async def get_excluded_symbols():
    """
    查看排除列表中的币种

    这些币种不会被自动发现，即使它们符合成交额范围。

    ### 返回示例
    ```json
    {
      "excluded_symbols": ["BTCUSDT", "ETHUSDT"],
      "count": 2
    }
    ```
    """
    cfg = get_config_manager()
    excluded = cfg.get("discovery_excluded_symbols", [])
    
    return {
        "excluded_symbols": excluded,
        "count": len(excluded),
    }


@app.post("/discovery/excluded", tags=["币种发现"])
async def update_excluded_symbols(
    symbols: List[str] = Query(..., description="要排除的币种列表，例如：BTCUSDT,ETHUSDT"),
):
    """
    更新排除列表

    更新后会自动清除发现缓存以应用新的排除规则。

    ### 参数
    - **symbols**: 逗号分隔的币种列表

    ### 示例
    ```
    POST /discovery/excluded?symbols=BTCUSDT&symbols=ETHUSDT
    ```
    """
    cfg = get_config_manager()
    discoverer = get_symbol_discovery()
    
    # 标准化币种名称
    normalized_symbols = [s.strip().upper() for s in symbols if s.strip()]
    
    discoverer.set_excluded_symbols(normalized_symbols)
    cfg.save()
    
    # 清除缓存以应用新的排除规则
    discoverer.clear_cache()
    
    return {
        "status": "success",
        "excluded_symbols": normalized_symbols,
        "count": len(normalized_symbols),
        "message": "排除列表已更新，发现缓存已清除",
    }


@app.get("/discovery/cache-status", tags=["币种发现"])
async def get_discovery_cache_status():
    """
    查看币种发现缓存的状态

    ### 返回示例
    ```json
    {
      "cached": true,
      "count": 42,
      "cached_at": "2026-02-11T10:30:45.123456",
      "ttl_seconds": 3600,
      "remaining_seconds": 2800
    }
    ```
    """
    discoverer = get_symbol_discovery()
    return discoverer.get_cache_status()


@app.post("/config/reset", tags=["配置"])
async def reset_config():
    """
    重置配置为默认值

    警告：此操作将清除所有自定义配置
    """
    cfg = get_config_manager()
    cfg.reset()
    
    return {
        "status": "success",
        "message": "配置已重置为默认值",
        "config": cfg.show(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
