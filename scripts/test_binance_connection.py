#!/usr/bin/env python3
"""Test script: use src.collector.binance_async.BinanceRESTClient to fetch trades.
This script reads API keys from environment variables and does NOT store them.
It prints only summary information (count and first 2 trades) without revealing keys.
"""
import os
import sys
import asyncio

# On Windows, use SelectorEventLoopPolicy to avoid aiodns/asyncio issues
if sys.platform.startswith('win'):
    try:
        import asyncio as _asyncio
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from src.collector.binance_async import BinanceRESTClient


async def main():
    key = os.getenv('BINANCE_API_KEY')
    secret = os.getenv('BINANCE_API_SECRET')
    if not key or not secret:
        print('No BINANCE_API_KEY/SECRET in environment; proceeding with public/fallback fetch (may succeed without keys).')

    client = BinanceRESTClient()
    try:
        trades = await client.fetch_trades('BTC/USDT')
        print('Fetched trades count:', len(trades))
        for t in trades[:2]:
            print({k: v for k, v in t.items() if k != 'trade_id' or True})
    except Exception as e:
        print('Error fetching trades:', str(e))


if __name__ == '__main__':
    asyncio.run(main())
