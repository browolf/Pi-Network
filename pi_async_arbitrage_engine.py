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
SPREAD_ALERT_PERCENT = 3.0        # Alert jika spread > 3%
ARBITRAGE_CAPITAL = 1000          # Modal simulasi (USDT)
CHECK_INTERVAL = 30               # Detik
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# ===============================
# TELEGRAM ALERT
# ===============================

async def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    async with aiohttp.ClientSession() as session:
        await session.post(url, data=payload)

# ===============================
# FETCH TICKER ASYNC
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
        await exchange.close()

        price = ticker.get("last")
        if price:
            return (exchange_id, float(price))

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
# AI INTELLIGENCE INTEGRATION
# ===============================

def generate_intelligence_report(results):
    prices = [price for _, price in results]
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

        results.sort(key=lambda x: x[1])

        lowest = results[0]
        highest = results[-1]

        spread_percent = ((highest[1] - lowest[1]) / lowest[1]) * 100
        spread_percent = round(spread_percent, 2)

        profit = calculate_arbitrage(lowest[1], highest[1])

        print(f"Lowest  : {lowest[0]} @ {lowest[1]}")
        print(f"Highest : {highest[0]} @ {highest[1]}")
        print(f"Spread  : {spread_percent}%")
        print(f"Simulated Profit (1000 USDT): {profit} USDT")

        # Intelligence
        intel = generate_intelligence_report(results)
        print(f"Avg Price: {intel['average_price']}")
        print(f"Volatility: {intel['volatility']}")
        print(f"Exchanges Found: {intel['exchange_count']}")

        # Telegram Alert
        if spread_percent >= SPREAD_ALERT_PERCENT:
            message = (
                f"🚨 PI Arbitrage Alert!\n\n"
                f"Buy: {lowest[0]} @ {lowest[1]}\n"
                f"Sell: {highest[0]} @ {highest[1]}\n"
                f"Spread: {spread_percent}%\n"
                f"Profit (1000 USDT): {profit} USDT"
            )
            await send_telegram(message)

        elapsed = round(time.time() - start_time, 2)
        print(f"Scan completed in {elapsed}s")

        await asyncio.sleep(CHECK_INTERVAL)

# ===============================
# ENTRY
# ===============================

if __name__ == "__main__":
    asyncio.run(main_loop())
