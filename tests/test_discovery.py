"""币种发现系统的单元和集成测试"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from src.discovery import SymbolDiscovery, discover_symbols_for_monitoring, get_symbol_discovery


class TestSymbolDiscovery:
    """测试币种发现器"""

    def test_init(self):
        """测试初始化"""
        discovery = SymbolDiscovery()
        assert discovery.config is not None
        assert discovery._cache == {}
        assert discovery._cache_time is None

    def test_filter_symbols_with_volume_range(self):
        """测试成交额范围过滤"""
        discovery = SymbolDiscovery()
        
        # 模拟币安数据
        tickers = [
            {"symbol": "BTCUSDT", "quoteAssetVolume": 50_000_000},  # 符合条件
            {"symbol": "ETHUSDT", "quoteAssetVolume": 30_000_000},  # 符合条件
            {"symbol": "BNBUSDT", "quoteAssetVolume": 5_000_000},   # 太低
            {"symbol": "XRPUSDT", "quoteAssetVolume": 100_000_000}, # 太高
            {"symbol": "ADAUSDT", "quoteAssetVolume": 20_000_000},  # 符合条件
        ]
        
        # 范围：[10M, 80M]
        result = discovery._filter_symbols(tickers)
        
        assert "BTCUSDT" in result
        assert "ETHUSDT" in result
        assert "ADAUSDT" in result
        assert "BNBUSDT" not in result
        assert "XRPUSDT" not in result

    def test_filter_symbols_exclude_non_usdt(self):
        """测试排除非 USDT 币对"""
        discovery = SymbolDiscovery()
        
        tickers = [
            {"symbol": "BTCUSDT", "quoteAssetVolume": 50_000_000},
            {"symbol": "ETHUSDT", "quoteAssetVolume": 30_000_000},
            {"symbol": "BTCETH", "quoteAssetVolume": 50_000_000},  # 不是 USDT
            {"symbol": "ETHBUSD", "quoteAssetVolume": 30_000_000},  # 不是 USDT
        ]
        
        result = discovery._filter_symbols(tickers)
        
        assert "BTCUSDT" in result
        assert "ETHUSDT" in result
        assert "BTCETH" not in result
        assert "ETHBUSD" not in result

    def test_excluded_symbols(self):
        """测试排除列表"""
        discovery = SymbolDiscovery()
        discovery.set_excluded_symbols(["BTCUSDT", "ETHUSDT"])
        
        tickers = [
            {"symbol": "BTCUSDT", "quoteAssetVolume": 50_000_000},
            {"symbol": "ETHUSDT", "quoteAssetVolume": 30_000_000},
            {"symbol": "ADAUSDT", "quoteAssetVolume": 20_000_000},
        ]
        
        result = discovery._filter_symbols(tickers)
        
        assert "BTCUSDT" not in result
        assert "ETHUSDT" not in result
        assert "ADAUSDT" in result

    def test_add_excluded_symbol(self):
        """测试添加排除列表项"""
        discovery = SymbolDiscovery()
        discovery.add_excluded_symbol("BTCUSDT")
        
        assert "BTCUSDT" in discovery._excluded_symbols

    def test_remove_excluded_symbol(self):
        """测试移除排除列表项"""
        discovery = SymbolDiscovery()
        discovery.set_excluded_symbols(["BTCUSDT", "ETHUSDT"])
        discovery.remove_excluded_symbol("BTCUSDT")
        
        assert "BTCUSDT" not in discovery._excluded_symbols
        assert "ETHUSDT" in discovery._excluded_symbols

    def test_cache_validity(self):
        """测试缓存有效性检查"""
        discovery = SymbolDiscovery()
        
        # 初始时缓存无效
        assert not discovery._is_cache_valid()
        
        # 设置缓存内容和时间
        from datetime import datetime
        discovery._cache = {"tickers": []}
        discovery._cache_time = datetime.utcnow()
        
        # 现在缓存应该有效
        assert discovery._is_cache_valid()

    def test_clear_cache(self):
        """测试清除缓存"""
        discovery = SymbolDiscovery()
        discovery._cache = {"tickers": []}
        from datetime import datetime
        discovery._cache_time = datetime.utcnow()
        
        discovery.clear_cache()
        
        assert discovery._cache == {}
        assert discovery._cache_time is None

    def test_get_cache_status_empty(self):
        """测试获取缓存状态（无缓存）"""
        discovery = SymbolDiscovery()
        status = discovery.get_cache_status()
        
        assert not status["cached"]
        assert status["count"] == 0
        assert status["cached_at"] is None

    def test_get_cache_status_with_cache(self):
        """测试获取缓存状态（有缓存）"""
        discovery = SymbolDiscovery()
        discovery._cache = {"tickers": [{"symbol": "BTCUSDT"}]}
        from datetime import datetime
        discovery._cache_time = datetime.utcnow()
        
        status = discovery.get_cache_status()
        
        assert status["cached"]
        assert status["count"] == 1
        assert status["cached_at"] is not None


class TestDiscoverSymbols:
    """测试异步发现函数"""

    @pytest.mark.asyncio
    async def test_discover_symbols_with_simulated_data(self):
        """测试使用模拟数据的发现"""
        discovery = SymbolDiscovery()
        symbols = await discovery.discover_symbols(use_cache=False)
        
        # 应该返回至少几个符合条件的币种
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert all(isinstance(s, str) for s in symbols)
        assert all(s.endswith("USDT") for s in symbols)

    @pytest.mark.asyncio
    async def test_discover_symbols_cache_usage(self):
        """测试缓存功能"""
        discovery = SymbolDiscovery()
        
        # 第一次发现，不使用缓存
        symbols1 = await discovery.discover_symbols(use_cache=False)
        
        # 第二次发现，使用缓存（应该返回相同结果）
        symbols2 = await discovery.discover_symbols(use_cache=True)
        
        assert symbols1 == symbols2

    @pytest.mark.asyncio
    async def test_discover_symbols_for_monitoring_max_symbols(self):
        """测试最大币种限制"""
        symbols = await discover_symbols_for_monitoring(max_symbols=5, use_cache=False)
        
        assert len(symbols) <= 5

    @pytest.mark.asyncio
    async def test_get_symbol_discovery_singleton(self):
        """测试全局实例单例"""
        discovery1 = get_symbol_discovery()
        discovery2 = get_symbol_discovery()
        
        assert discovery1 is discovery2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
