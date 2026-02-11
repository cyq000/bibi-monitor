"""Project entry point. Usage:

  python -m src run-once         # run a single CLI run_once using env SYMBOL
  python -m src demo            # run ingest pipeline demo
  python -m src daemon          # run daemon (SYMBOLS, INTERVAL env supported)
"""
import sys
import asyncio
import argparse
from src.logging import get_logger
from src.config import settings


logger = get_logger("entry", settings.LOG_LEVEL)


def run_once_cmd():
    from src.cli import run_once
    sym = os_env = __import__('os').environ.get('SYMBOL', 'BTCUSDT')
    run_once(sym)


def demo_cmd():
    from src.processor.ingest_pipeline import demo
    asyncio.run(demo())


def daemon_cmd():
    from src.daemon import run_daemon
    import os
    syms = os.environ.get('SYMBOLS', 'BTCUSDT').split(',')
    interval = int(os.environ.get('INTERVAL', '3600'))
    try:
        asyncio.run(run_daemon(syms, interval))
    except KeyboardInterrupt:
        logger.info('daemon stopped')


def main():
    parser = argparse.ArgumentParser(prog='bibi-monitor')
    parser.add_argument('cmd', choices=['run-once', 'demo', 'daemon'], nargs='?', default='run-once')
    args = parser.parse_args()
    if args.cmd == 'run-once':
        run_once_cmd()
    elif args.cmd == 'demo':
        demo_cmd()
    elif args.cmd == 'daemon':
        daemon_cmd()


if __name__ == '__main__':
    main()
