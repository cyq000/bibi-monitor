"""币种自动发现系统：动态发现符合条件的币种

此模块实现以下功能：
- 从币安获取所有币种的 24h 成交额
- 按照配置的体积范围自动过滤币种
- 支持缓存以减少 API 调用
- 支持排除列表（用于跳过特定币种）
"""
import asyncio
import time
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import json
from pathlib import Path

from src.logging import get_logger
from src.config_manager import get_config_manager

logger = get_logger(__name__)


class SymbolDiscovery:
    """币种发现器：动态发现符合条件的币种"""

    def __init__(self):
        """初始化币种发现器"""
        self.config = get_config_manager()
        self._cache: Dict = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 3600  # 1 小时缓存
        self._excluded_symbols: Set[str] = set()
        self._load_excluded_symbols()

    def _load_excluded_symbols(self) -> None:
        """从配置加载排除列表"""
        excluded = self.config.get("discovery_excluded_symbols", [])
        self._excluded_symbols = set(excluded)
        if self._excluded_symbols:
            logger.info(f"已加载排除列表：{self._excluded_symbols}")

    def _is_cache_valid(self) -> bool:
        """检查缓存是否仍有效"""
        if not self._cache_time:
            return False
        elapsed = (datetime.utcnow() - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl_seconds

    async def _fetch_binance_24h_ticker(self) -> List[Dict]:
        """从币安获取 24h 行情数据（含成交额）
        
        Returns:
            列表，每个元素为 {symbol, quoteAsset, volume24h}
        """
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp 未安装，使用模拟数据")
            return self._get_simulated_ticker_data()

        try:
            async with aiohttp.ClientSession() as session:
                # 币安现货行情接口
                url = "https://api.binance.com/api/v3/ticker/24hr"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"从币安获取 {len(data)} 个币对的 24h 行情数据")
                        return data
                    else:
                        logger.error(f"币安 API 返回错误：{resp.status}")
                        return self._get_simulated_ticker_data()
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"获取币安数据失败（{type(e).__name__}：{e}），使用模拟数据")
            return self._get_simulated_ticker_data()

    def _get_simulated_ticker_data(self) -> List[Dict]:
        """返回模拟的行情数据用于测试"""
        symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
            "DOGEUSDT", "MATICUSDT", "SOLUSDT", "DOTUSDT", "AVAXUSDT",
            "LTCUSDT", "LINKUSDT", "UNIUSDT", "XLMUSDT", "BCHUSDT",
            "THETAUSDT", "TRXUSDT", "FTMUSDT", "QTUMUSDT", "ATOMUSDT",
            "WLFIUSDT", "OPUSDT", "ARBUSDT", "GMXUSDT", "MAGICUSDT",
        ]
        
        import random
        random.seed(42)  # 固定随机数以保证一致性
        
        data = []
        for symbol in symbols:
            # 生成 1M - 100M 之间的随机成交额
            quoteAsset = "USDT"
            volume_usdt = random.randint(1_000_000, 100_000_000)
            
            data.append({
                "symbol": symbol,
                "quoteAsset": quoteAsset,
                "quoteAssetVolume": volume_usdt,  # 成交额（USDT）
                "volume": volume_usdt / 40000,  # 模拟成交量（假设平均价格 40000）
            })
        
        logger.info(f"使用模拟数据：{len(data)} 个币对")
        return data

    async def discover_symbols(self, use_cache: bool = True) -> List[str]:
        """发现符合条件的币种
        
        Args:
            use_cache: 是否使用缓存的数据
            
        Returns:
            符合条件的币种列表，例如 ["BTCUSDT", "ETHUSDT", ...]
        """
        # 检查缓存
        if use_cache and self._is_cache_valid():
            logger.info("使用缓存的币种列表")
            return self._filter_symbols(self._cache.get("tickers", []))

        # 获取最新数据
        logger.info("从币安获取最新币种数据...")
        tickers = await self._fetch_binance_24h_ticker()
        
        if not tickers:
            logger.warning("未能获取币种数据，返回空列表")
            return []

        # 更新缓存
        self._cache = {"tickers": tickers}
        self._cache_time = datetime.utcnow()

        # 过滤符合条件的币种
        result = self._filter_symbols(tickers)
        logger.info(f"发现 {len(result)} 个符合条件的币种：{result}")

        return result

    def _filter_symbols(self, tickers: List[Dict]) -> List[str]:
        """过滤符合条件的币种
        
        条件：
        1. 币对必须以 USDT 结尾（USDT 市场）
        2. 24h 成交额在 [volume_min, volume_max] 范围内
        3. 不在排除列表中
        """
        volume_min = self.config.get("volume_min", 10_000_000)
        volume_max = self.config.get("volume_max", 80_000_000)
        
        result = []
        
        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            
            # 检查是否是 USDT 币对
            if not symbol.endswith("USDT"):
                continue
            
            # 检查是否在排除列表中
            if symbol in self._excluded_symbols:
                logger.debug(f"跳过排除的币种：{symbol}")
                continue
            
            # 获取 24h 成交额（根据币安 API 的不同版本可能是不同的字段）
            volume_24h = ticker.get("quoteAssetVolume") or ticker.get("volume24h") or 0
            
            # 转换为整数
            try:
                volume_24h = float(volume_24h)
            except (ValueError, TypeError):
                logger.debug(f"无法解析 {symbol} 的成交额")
                continue
            
            # 检查成交额是否在范围内
            if volume_min <= volume_24h <= volume_max:
                result.append(symbol)
                logger.debug(f"发现符合条件的币种：{symbol} "
                           f"(24h volume: {volume_24h/1e6:.2f}M USDT)")
        
        return sorted(result)

    def set_excluded_symbols(self, symbols: List[str]) -> None:
        """设置排除列表"""
        self._excluded_symbols = set(symbols)
        # 保存到配置
        self.config.set("discovery_excluded_symbols", symbols)
        logger.info(f"已更新排除列表：{self._excluded_symbols}")

    def add_excluded_symbol(self, symbol: str) -> None:
        """添加到排除列表"""
        self._excluded_symbols.add(symbol)
        self.config.set("discovery_excluded_symbols", list(self._excluded_symbols))
        logger.info(f"已添加到排除列表：{symbol}")

    def remove_excluded_symbol(self, symbol: str) -> None:
        """从排除列表中移除"""
        self._excluded_symbols.discard(symbol)
        self.config.set("discovery_excluded_symbols", list(self._excluded_symbols))
        logger.info(f"已从排除列表中移除：{symbol}")

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache = {}
        self._cache_time = None
        logger.info("币种发现缓存已清除")

    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        if not self._cache_time:
            return {
                "cached": False,
                "count": 0,
                "cached_at": None,
                "ttl_seconds": self._cache_ttl_seconds,
            }
        
        elapsed = (datetime.utcnow() - self._cache_time).total_seconds()
        remaining = max(0, self._cache_ttl_seconds - elapsed)
        
        return {
            "cached": True,
            "count": len(self._cache.get("tickers", [])),
            "cached_at": self._cache_time.isoformat(),
            "ttl_seconds": self._cache_ttl_seconds,
            "remaining_seconds": remaining,
        }


# 全局发现器实例
_discovery_instance: Optional[SymbolDiscovery] = None


def get_symbol_discovery() -> SymbolDiscovery:
    """获取全局币种发现器实例"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = SymbolDiscovery()
    return _discovery_instance


async def discover_symbols_for_monitoring(
    max_symbols: Optional[int] = None,
    use_cache: bool = True,
) -> List[str]:
    """发现用于监控的币种

    Args:
        max_symbols: 最多返回多少个币种（None 表示不限制）
        use_cache: 是否使用缓存

    Returns:
        符合条件的币种列表
    """
    discoverer = get_symbol_discovery()
    symbols = await discoverer.discover_symbols(use_cache=use_cache)
    
    if max_symbols and len(symbols) > max_symbols:
        symbols = symbols[:max_symbols]
        logger.info(f"限制监控币种数为 {max_symbols}，返回：{symbols}")
    
    return symbols


if __name__ == "__main__":
    # 测试脚本
    async def test_discovery():
        """测试币种发现功能"""
        from src.config import settings
        
        print("=" * 60)
        print("币种发现器测试")
        print("=" * 60)
        
        discoverer = SymbolDiscovery()
        
        print("\n1. 第一次发现（从 API 获取）")
        print("-" * 40)
        symbols = await discoverer.discover_symbols(use_cache=False)
        print(f"发现 {len(symbols)} 个币种：")
        print(f"  {symbols[:20]}...")  # 显示前 20 个
        
        print("\n2. 缓存状态")
        print("-" * 40)
        cache_status = discoverer.get_cache_status()
        print(f"  已缓存：{cache_status['cached']}")
        print(f"  币种数：{cache_status['count']}")
        print(f"  缓存时间：{cache_status['cached_at']}")
        
        print("\n3. 第二次发现（使用缓存）")
        print("-" * 40)
        symbols2 = await discoverer.discover_symbols(use_cache=True)
        print(f"发现 {len(symbols2)} 个币种（来自缓存）")
        
        print("\n4. 排除列表测试")
        print("-" * 40)
        discoverer.set_excluded_symbols(["BTCUSDT", "ETHUSDT"])
        symbols3 = await discoverer.discover_symbols(use_cache=True)
        print(f"排除 BTCUSDT、ETHUSDT 后，发现 {len(symbols3)} 个币种")
        
        print("\n5. 清除缓存后重新发现")
        print("-" * 40)
        discoverer.clear_cache()
        symbols4 = await discoverer.discover_symbols(use_cache=False)
        print(f"清除排除列表后，发现 {len(symbols4)} 个币种")

    asyncio.run(test_discovery())
