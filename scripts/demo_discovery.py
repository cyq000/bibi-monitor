"""币种发现系统的演示脚本"""
import asyncio
import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.discovery import discover_symbols_for_monitoring, get_symbol_discovery
from src.config_manager import get_config_manager


async def demo_basic_discovery():
    """演示基本的币种发现功能"""
    print("\n" + "=" * 60)
    print("演示 1：基本币种发现")
    print("=" * 60)
    
    print("\n从币安获取符合条件的币种 (24h 成交额范围: 10M - 80M USDT)...")
    symbols = await discover_symbols_for_monitoring(use_cache=False)
    
    print(f"\n[OK] 发现 {len(symbols)} 个符合条件的币种：")
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i:2d}. {symbol}")


async def demo_cache_usage():
    """演示缓存功能"""
    print("\n" + "=" * 60)
    print("演示 2：缓存功能")
    print("=" * 60)
    
    discoverer = get_symbol_discovery()
    
    print("\n第 1 次发现（清除缓存，从 API 获取）...")
    discoverer.clear_cache()
    symbols1 = await discoverer.discover_symbols(use_cache=False)
    print(f"  [OK] 发现 {len(symbols1)} 个币种")
    
    print("\n缓存状态：")
    status = discoverer.get_cache_status()
    print(f"  已缓存：{status['cached']}")
    print(f"  币种数：{status['count']}")
    print(f"  缓存时间：{status['cached_at']}")
    
    print("\n第 2 次发现（使用缓存）...")
    symbols2 = await discoverer.discover_symbols(use_cache=True)
    print(f"  [OK] 发现 {len(symbols2)} 个币种（来自缓存）")
    print(f"  结果一致：{symbols1 == symbols2}")


async def demo_max_symbols():
    """演示限制币种数量"""
    print("\n" + "=" * 60)
    print("演示 3：限制币种数量")
    print("=" * 60)
    
    print("\n限制最多监控 10 个币种...")
    symbols = await discover_symbols_for_monitoring(max_symbols=10, use_cache=False)
    
    print(f"\n[OK] 限制后的币种列表 ({len(symbols)} 个)：")
    for i, symbol in enumerate(symbols, 1):
        print(f"  {i:2d}. {symbol}")


async def demo_exclusion():
    """演示排除列表"""
    print("\n" + "=" * 60)
    print("演示 4：排除列表")
    print("=" * 60)
    
    discoverer = get_symbol_discovery()
    discoverer.clear_cache()
    
    print("\n1. 获取完整的币种列表...")
    symbols_all = await discoverer.discover_symbols(use_cache=False)
    print(f"   共发现 {len(symbols_all)} 个币种")
    
    print("\n2. 添加排除列表：BTCUSDT, ETHUSDT, BNBUSDT...")
    discoverer.set_excluded_symbols(["BTCUSDT", "ETHUSDT", "BNBUSDT"])
    
    print("\n3. 获取排除后的币种列表...")
    discoverer.clear_cache()  # 清除缓存强制重新过滤
    symbols_filtered = await discoverer.discover_symbols(use_cache=False)
    print(f"   排除后发现 {len(symbols_filtered)} 个币种")
    
    print("\n排除的币种：")
    excluded = set(symbols_all) - set(symbols_filtered)
    for symbol in sorted(excluded):
        print(f"  [SKIP] {symbol}")


async def demo_config_integration():
    """演示与配置系统的集成"""
    print("\n" + "=" * 60)
    print("演示 5：配置系统集成")
    print("=" * 60)
    
    config = get_config_manager()
    
    print("\n当前配置：")
    show_config = config.show()
    print(f"  score_threshold: {show_config['score_threshold']}")
    print(f"  volume_min: {show_config['volume_min']:,} USDT")
    print(f"  volume_max: {show_config['volume_max']:,} USDT")
    
    discoverer = get_symbol_discovery()
    
    print("\n修改成交额范围：20M - 60M USDT...")
    config.set("volume_min", 20_000_000)
    config.set("volume_max", 60_000_000)
    
    discoverer.clear_cache()
    symbols = await discoverer.discover_symbols(use_cache=False)
    print(f"  [OK] 发现 {len(symbols)} 个符合新范围的币种")
    
    print("\n恢复原始配置...")
    config.set("volume_min", 10_000_000)
    config.set("volume_max", 80_000_000)


async def demo_quick_start():
    """快速开始演示"""
    print("\n" + "=" * 60)
    print("快速开始：如何在实际应用中使用")
    print("=" * 60)
    
    print("\n方法 1：在 daemon 中启用自动发现")
    print("""
    # 设置环境变量
    export ENABLE_DISCOVERY=true
    export DISCOVERY_INTERVAL=86400  # 每 24 小时发现一次
    
    # 启动守护进程
    python -m src.daemon
    
    # 守护进程会自动：
    # 1. 从币安获取所有币种的 24h 成交额
    # 2. 过滤出符合条件的币种 (10M - 80M USDT)
    # 3. 对这些币种进行监控
    # 4. 每 24 小时重新发现一次
    """)
    
    print("\n方法 2：手动发现币种")
    print("""
    from src.discovery import discover_symbols_for_monitoring
    
    # 异步发现
    symbols = await discover_symbols_for_monitoring()
    print(f"发现的币种：{symbols}")
    """)
    
    print("\n方法 3：自定义发现配置")
    print("""
    from src.config_manager import get_config_manager
    
    config = get_config_manager()
    
    # 修改发现范围
    config.set("volume_min", 20_000_000)  # 20M USDT
    config.set("volume_max", 60_000_000)  # 60M USDT
    
    # 添加排除列表
    config.set("discovery_excluded_symbols", ["BTCUSDT", "ETHUSDT"])
    
    # 保存配置
    config.save()
    """)


async def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("币种自动发现系统 - 演示程序")
    print("=" * 60)
    
    try:
        await demo_basic_discovery()
        await demo_cache_usage()
        await demo_max_symbols()
        await demo_exclusion()
        await demo_config_integration()
        await demo_quick_start()
        
        print("\n" + "=" * 60)
        print("[OK] 所有演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] 演示过程中出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
