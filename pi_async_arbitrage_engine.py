"""
PI Global Liquidity Intelligence Engine
Async Arbitrage + Telegram Alert + AI Integration
Author: Clawue884
"""

import asyncio
import ccxt.async_support as ccxt
import statistics
import time
import aiohttp
from datetime import datetime

# ===============================
# CONFIG
# ===============================

TARGET_SYMBOL = "PI/USDT"
SPREAD_ALERT_PERCENT = 3.0
ARBITRAGE_CAPITAL = 1000
CHECK_INTERVAL = 30
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# ===============================
# TELEGRAM ALERT
# ===============================

async def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        await session.post(url, data=payload)

# ===============================
# FETCH TICKER + MARKET INFO
# ===============================

async def fetch_price(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            "enableRateLimit": True,
            "timeout": 10000,
        })

        if not exchange.has.get("fetchTicker", False):
            return None

        await exchange.load_markets()

        if TARGET_SYMBOL not in exchange.symbols:
            await exchange.close()
            return None

        ticker = await exchange.fetch_ticker(TARGET_SYMBOL)
        market = exchange.markets[TARGET_SYMBOL]

        await exchange.close()

        price = ticker.get("last")
        if price:
            return {
                "exchange": exchange_id,
                "price": float(price),
                "type": market.get("type"),
                "spot": market.get("spot"),
                "active": market.get("active")
            }

    except Exception:
        return None

# ===============================
# ARBITRAGE CALCULATOR
# ===============================

def calculate_arbitrage(low_price, high_price):
    amount_pi = ARBITRAGE_CAPITAL / low_price
    sell_value = amount_pi * high_price
    profit = sell_value - ARBITRAGE_CAPITAL
    return round(profit, 2)

# ===============================
# AI INTELLIGENCE
# ===============================

def generate_intelligence_report(results):
    prices = [r["price"] for r in results]
    avg_price = statistics.mean(prices)
    volatility = statistics.pstdev(prices)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "average_price": avg_price,
        "volatility": volatility,
        "exchange_count": len(results)
    }

# ===============================
# MAIN LOOP
# ===============================

async def main_loop():

    while True:
        print(f"\nScanning {TARGET_SYMBOL} markets...")
        start_time = time.time()

        tasks = [fetch_price(exchange_id) for exchange_id in ccxt.exchanges]
        results = await asyncio.gather(*tasks)
        results = [r for r in results if r is not None]

        if not results:
            print("No markets found.")
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        results.sort(key=lambda x: x["price"])

        lowest = results[0]
        highest = results[-1]

        spread_percent = ((highest["price"] - lowest["price"]) / lowest["price"]) * 100
        spread_percent = round(spread_percent, 2)

        profit = calculate_arbitrage(lowest["price"], highest["price"])

        print("\n=== MARKET DETAIL ===")
        for r in results:
            print(
                f"{r['exchange']} | "
                f"Price: {r['price']} | "
                f"Type: {r['type']} | "
                f"Spot: {r['spot']} | "
                f"Active: {r['active']}"
            )

        print("\n=== ARBITRAGE ===")
        print(f"Buy  : {lowest['exchange']} @ {lowest['price']}")
        print(f"Sell : {highest['exchange']} @ {highest['price']}")
        print(f"Spread : {spread_percent}%")
        print(f"Profit (1000 USDT): {profit} USDT")

        intel = generate_intelligence_report(results)
        print("\n=== INTELLIGENCE ===")
        print(f"Avg Price: {intel['average_price']}")
        print(f"Volatility: {intel['volatility']}")
        print(f"Exchanges Found: {intel['exchange_count']}")

        if spread_percent >= SPREAD_ALERT_PERCENT:
            message = (
                f"🚨 PI Arbitrage Alert!\n\n"
                f"Buy: {lowest['exchange']} @ {lowest['price']}\n"
                f"Sell: {highest['exchange']} @ {highest['price']}\n"
                f"Spread: {spread_percent}%\n"
                f"Profit: {profit} USDT"
            )
            await send_telegram(message)

        elapsed = round(time.time() - start_time, 2)
        print(f"\nScan completed in {elapsed}s")

        await asyncio.sleep(CHECK_INTERVAL)

# ===============================
# ENTRY
# ===============================

if __name__ == "__main__":
    asyncio.run(main_loop())
