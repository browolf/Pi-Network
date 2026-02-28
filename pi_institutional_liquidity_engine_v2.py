"""
PI Institutional Liquidity Core
Depth-Based Arbitrage + Risk Engine
Author: Clawue884
LEVEL: INSTITUTIONAL CORE
"""

import asyncio
import ccxt.async_support as ccxt
import statistics
import aiosqlite
import time
from datetime import datetime

# =========================
# CONFIG
# =========================

SYMBOL = "PI/USDT"
CAPITAL = 1000
MIN_SPREAD = 2.0
DEPTH_USDT = 300
CHECK_INTERVAL = 20

# =========================
# DATABASE INIT
# =========================

async def init_db():
    async with aiosqlite.connect("intel.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            timestamp TEXT,
            buy_ex TEXT,
            sell_ex TEXT,
            spread REAL,
            profit REAL
        )
        """)
        await db.commit()

# =========================
# DEPTH ANALYSIS
# =========================

async def fetch_depth(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({"enableRateLimit": True})
        await exchange.load_markets()

        if SYMBOL not in exchange.symbols:
            await exchange.close()
            return None

        market = exchange.markets[SYMBOL]
        if not market.get("spot") or not market.get("active"):
            await exchange.close()
            return None

        orderbook = await exchange.fetch_order_book(SYMBOL)
        await exchange.close()

        best_ask = orderbook["asks"][0][0] if orderbook["asks"] else None
        best_bid = orderbook["bids"][0][0] if orderbook["bids"] else None

        if not best_ask or not best_bid:
            return None

        return {
            "exchange": exchange_id,
            "ask": float(best_ask),
            "bid": float(best_bid)
        }

    except:
        return None

# =========================
# PROFIT MODEL
# =========================

def calculate_profit(buy_price, sell_price):
    amount = CAPITAL / buy_price
    gross = amount * sell_price
    return round(gross - CAPITAL, 2)

# =========================
# INTELLIGENCE SCORE
# =========================

def confidence_score(spread, volatility):
    score = (spread / (volatility + 0.01)) * 10
    return round(min(score, 100), 2)

# =========================
# MAIN ENGINE
# =========================

async def core_loop():

    await init_db()

    while True:

        print("\n🔍 Scanning Institutional Layer...")
        start = time.time()

        tasks = [fetch_depth(ex) for ex in ccxt.exchanges]
        results = await asyncio.gather(*tasks)

        markets = [r for r in results if r]

        if len(markets) < 2:
            print("Not enough depth markets.")
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        markets.sort(key=lambda x: x["ask"])

        buy = markets[0]
        sell = sorted(markets, key=lambda x: x["bid"], reverse=True)[0]

        spread = ((sell["bid"] - buy["ask"]) / buy["ask"]) * 100
        spread = round(spread, 2)

        profit = calculate_profit(buy["ask"], sell["bid"])

        prices = [m["ask"] for m in markets]
        volatility = statistics.pstdev(prices)

        score = confidence_score(spread, volatility)

        print(f"BUY  : {buy['exchange']} @ {buy['ask']}")
        print(f"SELL : {sell['exchange']} @ {sell['bid']}")
        print(f"Spread: {spread}%")
        print(f"Profit: {profit} USDT")
        print(f"Volatility: {volatility}")
        print(f"Confidence Score: {score}/100")

        if spread >= MIN_SPREAD and profit > 0:
            print("🔥 Institutional Arbitrage Signal!")

            async with aiosqlite.connect("intel.db") as db:
                await db.execute(
                    "INSERT INTO scans VALUES (?, ?, ?, ?, ?)",
                    (datetime.utcnow().isoformat(),
                     buy["exchange"],
                     sell["exchange"],
                     spread,
                     profit)
                )
                await db.commit()

        else:
            print("No institutional-grade signal.")

        print(f"Scan time: {round(time.time()-start,2)}s")

        await asyncio.sleep(CHECK_INTERVAL)

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    asyncio.run(core_loop())
