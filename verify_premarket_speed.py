import asyncio
import time

import pandas as pd

from premarket_filter import PremarketFilter, REQUIRED_DAYS


class FakeDhan:
    async def get_historical_data_async(self, symbol: str, exchange_segment="NSE_EQ", days=15):
        # Simulate network latency
        await asyncio.sleep(0.05)
        rows = max(REQUIRED_DAYS, 6)
        return pd.DataFrame(
            {
                # Ensure volume SMA passes filter threshold in tests
                "volume": [1_000_000] * rows,
                "close": [100.0] * rows,
            }
        )


async def main():
    engine = PremarketFilter(FakeDhan())
    symbols = [f"S{i:03d}" for i in range(100)]

    t0 = time.time()
    out = await engine.filter_all_stocks(symbols=symbols, max_in_flight=20)
    elapsed = time.time() - t0

    assert len(out) == len(symbols)
    # If concurrency is working, 100 * 0.05 / 20 ~= 0.25s + overhead.
    assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s (concurrency broken?)"


if __name__ == "__main__":
    asyncio.run(main())
    print("OK")
