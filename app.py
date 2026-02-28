import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
import statistics

app = FastAPI()

TARGET_SYMBOL = "PI/USDT"

async def fetch_price(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({"enableRateLimit": True})

        await exchange.load_markets()

        if TARGET_SYMBOL not in exchange.symbols:
            await exchange.close()
            return None

        ticker = await exchange.fetch_ticker(TARGET_SYMBOL)
        await exchange.close()

        return (exchange_id, float(ticker["last"]))

    except:
        return None


@app.get("/scan")
async def scan_market():
    tasks = [fetch_price(e) for e in ccxt.exchanges]
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r]

    if not results:
        return {"status": "No market found"}

    results.sort(key=lambda x: x[1])
    prices = [r[1] for r in results]

    return {
        "lowest": results[0],
        "highest": results[-1],
        "average_price": statistics.mean(prices),
        "exchange_count": len(results)
    }
