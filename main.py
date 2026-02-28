import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI, WebSocket
from arbitrage import calculate_arbitrage
from ai_engine import analyze_market

app = FastAPI(title="PI Market Intelligence")

EXCHANGES = ["binance", "gateio", "okx", "mexc"]
SYMBOL = "PI/USDT"

async def fetch_prices():
    results = []
    tasks = []

    for ex_id in EXCHANGES:
        try:
            exchange = getattr(ccxt, ex_id)({
                "enableRateLimit": True,
            })
            tasks.append(exchange.fetch_ticker(SYMBOL))
        except:
            continue

    tickers = await asyncio.gather(*tasks, return_exceptions=True)

    for i, ticker in enumerate(tickers):
        if isinstance(ticker, dict):
            results.append({
                "exchange": EXCHANGES[i],
                "price": ticker["last"],
                "volume": ticker["quoteVolume"]
            })

    return results


@app.get("/api/prices")
async def get_prices():
    prices = await fetch_prices()
    arbitrage = calculate_arbitrage(prices)
    ai = analyze_market(prices)
    return {
        "prices": prices,
        "arbitrage": arbitrage,
        "ai_signal": ai
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        prices = await fetch_prices()
        arbitrage = calculate_arbitrage(prices)
        await websocket.send_json({
            "prices": prices,
            "arbitrage": arbitrage
        })
        await asyncio.sleep(5)
