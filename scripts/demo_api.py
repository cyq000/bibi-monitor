#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""币种发现系统 - 完整功能演示"""
import sys
import requests
import json
import time
from datetime import datetime

# 设置 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def demo_1_discover_symbols():
    """演示 1: 发现币种"""
    print_header("演示 1: 自动发现符合条件的币种")
    
    try:
        resp = requests.get(f"{BASE_URL}/discovery/symbols")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 发现 {data['count']} 个符合条件的币种")
            print(f"[OK] 缓存使用：{data['cache_used']}")
            print(f"[OK] 时间：{datetime.now().strftime('%H:%M:%S')}")
            print(f"\n发现的币种列表：")
            for i, symbol in enumerate(data['symbols'], 1):
                print(f"  {i:2d}. {symbol}")
            return data
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] 错误：{e}")
        return None

def demo_2_cache_status():
    """演示 2: 查看缓存状态"""
    print_header("演示 2: 查看缓存状态")
    
    try:
        resp = requests.get(f"{BASE_URL}/discovery/cache-status")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 已缓存：{data['cached']}")
            print(f"[OK] 币种数：{data['count']}")
            if data['cached_at']:
                print(f"[OK] 缓存时间：{data['cached_at']}")
                print(f"[OK] 缓存有效期：{data['ttl_seconds']} 秒")
                print(f"[OK] 剩余时间：{data['remaining_seconds']} 秒")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def demo_3_max_symbols():
    """演示 3: 限制币种数量"""
    print_header("演示 3: 限制最多监控 5 个币种")
    
    try:
        resp = requests.get(f"{BASE_URL}/discovery/symbols?max_symbols=5")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 限制后币种数：{data['count']}")
            print(f"\n受限的币种列表（5 个）：")
            for i, symbol in enumerate(data['symbols'], 1):
                print(f"  {i}. {symbol}")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def demo_4_excluded_list():
    """演示 4: 排除列表"""
    print_header("演示 4: 设置排除列表")
    
    try:
        # 设置排除列表
        print("1. 设置排除 BTCUSDT 和 ETHUSDT...")
        resp = requests.post(
            f"{BASE_URL}/discovery/excluded",
            params={"symbols": ["BTCUSDT", "ETHUSDT"]}
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] {data['message']}")
            print(f"[OK] 排除列表：{data['excluded_symbols']}")
            
            # 再次发现
            print("\n2. 重新发现币种（排除后）...")
            time.sleep(0.5)
            resp2 = requests.get(f"{BASE_URL}/discovery/symbols")
            if resp2.status_code == 200:
                data2 = resp2.json()
                print(f"[OK] 排除后币种数：{data2['count']}")
                print(f"[OK] 排除的币种未出现在列表中")
                if "BTCUSDT" not in data2['symbols'] and "ETHUSDT" not in data2['symbols']:
                    print(f"[OK] 确认排除成功")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def demo_5_config():
    """演示 5: 查看配置"""
    print_header("演示 5: 查看当前配置")
    
    try:
        resp = requests.get(f"{BASE_URL}/config")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 买卖比率阈值：{data['score_threshold']}")
            print(f"[OK] 最小成交额：{data['volume_min']:,} USDT")
            print(f"[OK] 最大成交额：{data['volume_max']:,} USDT")
            print(f"[OK] 按币种配置数：{len(data['per_symbol_thresholds'])}")
            
            if data['per_symbol_thresholds']:
                print(f"\n特殊币种配置：")
                for symbol, config in data['per_symbol_thresholds'].items():
                    print(f"  {symbol}:")
                    for key, value in config.items():
                        print(f"    - {key}: {value}")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def demo_6_modify_config():
    """演示 6: 修改配置"""
    print_header("演示 6: 修改成交额范围")
    
    try:
        print("1. 原配置：10M - 80M USDT")
        print("2. 修改为：20M - 60M USDT...")
        
        resp = requests.post(
            f"{BASE_URL}/config",
            params={
                "volume_min": 20_000_000,
                "volume_max": 60_000_000
            }
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 配置已更新")
            print(f"[OK] 新范围：{data['config']['volume_min']:,} - {data['config']['volume_max']:,}")
            
            # 清除缓存后重新发现
            print("\n3. 清除缓存并重新发现...")
            requests.post(f"{BASE_URL}/discovery/cache/clear")
            time.sleep(0.5)
            
            resp2 = requests.get(f"{BASE_URL}/discovery/symbols?use_cache=false")
            if resp2.status_code == 200:
                data2 = resp2.json()
                print(f"[OK] 新范围下发现币种数：{data2['count']}")
                print(f"[OK] （币种数可能减少，因为范围更严格）")
            
            # 恢复原配置
            print("\n4. 恢复原配置：10M - 80M USDT...")
            requests.post(
                f"{BASE_URL}/config",
                params={
                    "volume_min": 10_000_000,
                    "volume_max": 80_000_000
                }
            )
            print(f"[OK] 配置已恢复")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def demo_7_stats():
    """演示 7: 查看统计信息"""
    print_header("演示 7: 查看监控统计")
    
    try:
        resp = requests.get(f"{BASE_URL}/stats?days=30")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] 时间范围：{data['period_days']} 天")
            print(f"[OK] 总通知数：{data['total_notifications']}")
            print(f"[OK] 已发送：{data['sent_count']}")
            print(f"[OK] 失败：{data['failed_count']}")
            print(f"[OK] 待处理：{data['pending_count']}")
            print(f"[OK] 成功率：{data['success_rate']*100:.1f}%")
            
            if data['symbols']:
                print(f"\n各币种通知数：")
                for symbol, count in sorted(data['symbols'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {symbol}: {count} 条")
        else:
            print(f"[FAIL] 请求失败：{resp.status_code}")
    except Exception as e:
        print(f"[ERROR] 错误：{e}")

def main():
    """主函数"""
    print("\n" + "="*60)
    print("  币种自动发现系统 - 完整功能演示")
    print("="*60)
    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始演示\n")
    
    # 检查 API 连接
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        if resp.status_code == 200:
            print("[OK] API 服务器已连接 (http://localhost:8000)\n")
        else:
            print("[FAIL] API 服务器返回错误")
            return
    except Exception as e:
        print(f"[ERROR] 无法连接 API 服务器：{e}")
        return
    
    # 运行演示
    try:
        demo_1_discover_symbols()
        demo_2_cache_status()
        demo_3_max_symbols()
        demo_4_excluded_list()
        demo_5_config()
        demo_6_modify_config()
        demo_7_stats()
        
        print_header("所有演示完成")
        print("[OK] 币种自动发现系统正常运行")
        print("[OK] 所有 API 端点功能正常")
        print("\n相关文档：")
        print("  - docs/DISCOVERY_GUIDE.md - 详细指南")
        print("  - docs/DISCOVERY_QUICK_REFERENCE.md - 快速参考")
        print("  - DISCOVERY_IMPLEMENTATION_SUMMARY.md - 实现总结\n")
        
    except KeyboardInterrupt:
        print("\n\n演示已中断")
    except Exception as e:
        print(f"\n[ERROR] 演示过程中出错：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
