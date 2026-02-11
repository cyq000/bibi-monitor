#!/usr/bin/env python3
"""Run a quick async demo of the ingest pipeline."""
import asyncio
from src.processor.ingest_pipeline import IngestPipeline


async def main():
    p = IngestPipeline()
    result = await p.run_cycle('BTCUSDT')
    print('Demo result:', result)


if __name__ == '__main__':
    asyncio.run(main())
