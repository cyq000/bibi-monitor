import asyncio
import os
from typing import List, Optional
from src.processor import IngestPipeline
from src.db import init_db
from src.logging import get_logger
from src.config import settings
from src.discovery import discover_symbols_for_monitoring, get_symbol_discovery
from src.config_manager import get_config_manager


logger = get_logger("daemon", settings.LOG_LEVEL)


async def run_symbol_cycle(pipeline: IngestPipeline, symbol: str):
    try:
        metric = await pipeline.run_cycle(symbol)
        logger.info("completed cycle", extra={"symbol": symbol, "metric": metric})
    except Exception as e:
        logger.error(f"cycle failed for {symbol}: {e}")


async def discover_and_run_daemon(
    interval_seconds: int = 3600,
    discovery_interval_seconds: int = 86400,
    max_symbols: Optional[int] = None,
):
    """运行守护进程，支持自动币种发现
    
    Args:
        interval_seconds: 监控周期（秒），默认 3600s（1小时）
        discovery_interval_seconds: 币种发现周期（秒），默认 86400s（24小时）
        max_symbols: 最多监控多少个币种（None 表示不限制）
    """
    init_db()
    p = IngestPipeline()
    config = get_config_manager()
    
    # 是否启用自动发现
    enable_discovery = os.getenv('ENABLE_DISCOVERY', 'true').lower() in ('true', '1', 'yes')
    
    if enable_discovery:
        logger.info(f"自动币种发现已启用，发现周期：{discovery_interval_seconds}s")
    else:
        logger.info("自动币种发现已禁用")
    
    symbols: List[str] = []
    last_discovery_time = 0
    
    while True:
        current_time = asyncio.get_event_loop().time()
        
        # 检查是否需要进行币种发现
        if enable_discovery and (current_time - last_discovery_time) >= discovery_interval_seconds:
            logger.info("执行币种自动发现...")
            try:
                symbols = await discover_symbols_for_monitoring(
                    max_symbols=max_symbols,
                    use_cache=False  # 强制从 API 重新获取
                )
                last_discovery_time = current_time
                
                if symbols:
                    logger.info(f"发现 {len(symbols)} 个符合条件的币种")
                else:
                    logger.warning("未发现符合条件的币种，使用默认币种")
                    symbols = ["BTCUSDT", "ETHUSDT"]
            except Exception as e:
                logger.error(f"币种发现失败：{e}，继续使用已有币种列表")
                if not symbols:
                    symbols = ["BTCUSDT", "ETHUSDT"]
        
        # 如果没有币种列表，执行一次初始发现
        if not symbols:
            logger.info("初始化币种列表...")
            try:
                symbols = await discover_symbols_for_monitoring(
                    max_symbols=max_symbols,
                    use_cache=False
                )
                last_discovery_time = current_time
            except Exception as e:
                logger.error(f"初始币种发现失败：{e}，使用默认币种")
                symbols = ["BTCUSDT", "ETHUSDT"]
        
        # 运行监控周期
        logger.info(f"开始监控周期，监控币种：{symbols} (共 {len(symbols)} 个)")
        tasks = [run_symbol_cycle(p, s) for s in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"监控周期完成，等待 {interval_seconds}s 后开始下一周期")
        await asyncio.sleep(interval_seconds)


async def run_daemon(symbols: List[str], interval_seconds: int = 3600):
    """运行守护进程，使用显式指定的币种列表（向后兼容）"""
    init_db()
    p = IngestPipeline()
    logger.info("daemon started", extra={"symbols": symbols, "interval": interval_seconds})
    while True:
        tasks = [run_symbol_cycle(p, s) for s in symbols]
        await asyncio.gather(*tasks)
        logger.info("cycle complete; sleeping", extra={"seconds": interval_seconds})
        await asyncio.sleep(interval_seconds)


if __name__ == '__main__':
    # 环境变量说明：
    # SYMBOLS: 逗号分隔的币种列表（如 "BTCUSDT,ETHUSDT,BNBUSDT"），为空时启用自动发现
    # ENABLE_DISCOVERY: 是否启用自动发现（true/false），默认 true
    # DISCOVERY_INTERVAL: 币种发现周期（秒），默认 86400（24小时）
    # INTERVAL: 监控周期（秒），默认 3600（1小时）
    # MAX_SYMBOLS: 最多监控多少个币种，默认不限制
    
    symbols_env = os.getenv('SYMBOLS', '').strip()
    interval = int(os.getenv('INTERVAL', '3600'))
    discovery_interval = int(os.getenv('DISCOVERY_INTERVAL', '86400'))
    max_symbols = os.getenv('MAX_SYMBOLS')
    max_symbols = int(max_symbols) if max_symbols else None
    
    try:
        if symbols_env:
            # 使用显式指定的币种列表
            syms = [s.strip().upper() for s in symbols_env.split(',') if s.strip()]
            logger.info(f"使用用户指定的币种列表：{syms}")
            asyncio.run(run_daemon(syms, interval))
        else:
            # 使用自动发现
            logger.info("使用自动币种发现模式")
            asyncio.run(discover_and_run_daemon(
                interval_seconds=interval,
                discovery_interval_seconds=discovery_interval,
                max_symbols=max_symbols,
            ))
    except KeyboardInterrupt:
        logger.info('daemon stopped by user')
