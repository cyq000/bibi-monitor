#!/usr/bin/env python3
"""
便捷脚本：运行真实飞书通知演示

使用方法:
  python scripts/feishu_demo_real.py --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
  
  或设置环境变量后直接运行:
  python scripts/feishu_demo_real.py
"""
import os
import sys
import argparse
from pathlib import Path

# Add repo to path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description="运行真实飞书通知演示")
    parser.add_argument(
        "--webhook",
        help="飞书 Webhook URL",
        default=os.getenv("FEISHU_WEBHOOK"),
    )
    parser.add_argument(
        "--symbol",
        help="监控币种",
        default="BTCUSDT",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟发送（不实际调用 Webhook）",
    )

    args = parser.parse_args()

    if not args.webhook and not args.dry_run:
        print("❌ 错误：未提供 Webhook URL")
        print("\n使用方法:")
        print("  python scripts/feishu_demo_real.py --webhook 'https://...'")
        print("  或设置环境变量: FEISHU_WEBHOOK='https://...'")
        sys.exit(1)

    # 设置环境变量
    if args.webhook:
        os.environ["FEISHU_WEBHOOK"] = args.webhook
    
    if not args.dry_run:
        os.environ["SEND_REAL"] = "1"
    else:
        os.environ["SEND_REAL"] = "0"

    # 动态导入并运行演示
    from scripts.feishu_demo import demo_feishu_notification
    import asyncio

    print(f"\n{'='*70}")
    print(f"  飞书通知演示 - {args.symbol}")
    print(f"  模式: {'模拟' if args.dry_run else '真实发送'}")
    print(f"{'='*70}\n")

    asyncio.run(demo_feishu_notification())


if __name__ == "__main__":
    main()
