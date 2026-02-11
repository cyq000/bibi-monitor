#!/usr/bin/env python3
"""Direct ccxt test: construct binance exchange with provided env vars (proxies, keys)
and attempt a set of calls (fetch_trades, fetch_ohlcv, fetch_ticker) for common symbols.
Prints only summary info and small samples.
"""
import os
import asyncio
import sys

if sys.platform.startswith('win'):
    try:
        import asyncio as _asyncio
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

async def main():
    import importlib
    ccxt = importlib.import_module('ccxt.async_support')

    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    proxy = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')

    params = {'enableRateLimit': True}
    if api_key and api_secret:
        params.update({'apiKey': api_key, 'secret': api_secret})
    if proxy:
        p = proxy if proxy.startswith('http') else 'http://' + proxy
        params['proxies'] = {'http': p, 'https': p}
    # prefer futures
    params['options'] = {'defaultType': 'future'}

    print('Constructing ccxt.binance with params keys-set:', bool(api_key), ' proxy:', bool(proxy))
    ex = ccxt.binance(params)

    symbols = ['BTC/USDT', 'BTCUSDT', 'BTC/USDT:USDT']
    results = []
    try:
        for s in symbols:
            try:
                print(f'Attempt fetch_trades({s})')
                trades = await ex.fetch_trades(s)
                results.append((s, 'trades', len(trades)))
                print(f'  OK trades count {len(trades)}')
                continue
            except Exception as e:
                print('  fetch_trades failed:', str(e))
            try:
                print(f'Attempt fetch_ohlcv({s})')
                o = await ex.fetch_ohlcv(s, '1m', limit=3)
                results.append((s, 'ohlcv', len(o)))
                print(f'  OK ohlcv count {len(o)}')
                continue
            except Exception as e:
                print('  fetch_ohlcv failed:', str(e))
            try:
                print(f'Attempt fetch_ticker({s})')
                t = await ex.fetch_ticker(s)
                results.append((s, 'ticker', t.get('last')))
                print('  OK ticker last', t.get('last'))
                continue
            except Exception as e:
                print('  fetch_ticker failed:', str(e))

    finally:
        try:
            await ex.close()
        except Exception:
            pass

    print('\nSummary:')
    for r in results:
        print(' ', r)

if __name__ == '__main__':
    asyncio.run(main())
