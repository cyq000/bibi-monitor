#!/usr/bin/env python3
"""Test various ccxt exchange variants (spot/futures) with provided API keys.
Prints only summary info (no secrets).
"""
import os
import asyncio
import sys

# On Windows, use SelectorEventLoopPolicy to avoid aiodns/asyncio issues
if sys.platform.startswith('win'):
    try:
        import asyncio as _asyncio
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

async def try_exchange(exchange_cls_name: str, symbol_variants):
    import importlib
    try:
        mod = importlib.import_module('ccxt.async_support')
        Exchange = getattr(mod, exchange_cls_name)
    except Exception as e:
        return (exchange_cls_name, False, f'Import error: {e}')

    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    params = { 'enableRateLimit': True }
    if api_key and api_secret:
        params['apiKey'] = api_key
        params['secret'] = api_secret

    try:
        ex = Exchange(params)
    except Exception as e:
        return (exchange_cls_name, False, f'Construct error: {e}')

    out = []
    try:
        # try multiple symbol formats
        for sym in symbol_variants:
            try:
                # prefer fetch_trades, fallback to fetch_ohlcv
                if hasattr(ex, 'fetch_trades'):
                    trades = await ex.fetch_trades(sym)
                    out.append((sym, 'trades', len(trades)))
                else:
                    o = await ex.fetch_ohlcv(sym, '1m', limit=3)
                    out.append((sym, 'ohlcv', len(o)))
            except Exception as e:
                out.append((sym, 'error', str(e)))
        await ex.close()
        return (exchange_cls_name, True, out)
    except Exception as e:
        try:
            await ex.close()
        except Exception:
            pass
        return (exchange_cls_name, False, f'Runtime error: {e}')


async def main():
    # variants to try for Binance-like markets
    symbol_variants = ['BTC/USDT', 'BTC/USDT:USDT', 'BTCUSDT', 'BTC/USD']
    exchange_classes = ['binance', 'binanceusdm', 'binanceus', 'binancecoinm']

    results = []
    for ex_name in exchange_classes:
        res = await try_exchange(ex_name, symbol_variants)
        results.append(res)

    print('\nCCXT test summary (no secrets shown):')
    for r in results:
        name, ok, info = r
        if ok:
            print(f'- {name}: SUCCESS')
            for item in info:
                sym, tp, val = item
                print(f'    {sym} -> {tp} count/err: {val}')
        else:
            print(f'- {name}: FAIL -> {info}')


if __name__ == '__main__':
    asyncio.run(main())
