import asyncio
import httpx

BASE_URL = "http://localhost:2024"


async def test_time_series():
    """Example: fetch asset time series with technical indicators."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(
            f"{BASE_URL}/api/time-series",
            params={"symbol": "EUR/USD", "interval": "1h", "asset_type": "forex"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"symbol={data['symbol']} interval={data['interval']} rows={len(data['data'])}")
        if data["data"]:
            print("latest bar:", data["data"][-1])


async def test_pivot_levels():
    """Example: fetch pivot levels for a symbol."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.get(
            f"{BASE_URL}/api/pivot-levels",
            params={"symbol": "EUR/USD", "asset_type": "forex"},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"pivot levels for {data['symbol']}:")
        print(data["pivot_levels"])


if __name__ == "__main__":
    asyncio.run(test_time_series())
    asyncio.run(test_pivot_levels())
