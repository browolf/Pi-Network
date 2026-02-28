
import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI()

SPREAD_ALERT_PERCENT = 3  # Alert threshold

async def fetch_exchange_price(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            "enableRateLimit": True,
        })
        await exchange.load_markets()

        if "PI/USDT" in exchange.symbols:
            ticker = await exchange.fetch_ticker("PI/USDT")
            await exchange.close()
            return {
                "exchange": exchange_id,
                "price": ticker.get("last"),
                "volume": ticker.get("quoteVolume", 0)
            }

        await exchange.close()
    except Exception:
        return None

async def scan_markets():
    tasks = [fetch_exchange_price(ex) for ex in ccxt.exchanges]
    results = await asyncio.gather(*tasks)
    markets = [r for r in results if r and r["price"]]

    if not markets:
        return {"markets": [], "spread": 0}

    prices = [m["price"] for m in markets]
    lowest = min(prices)
    highest = max(prices)

    spread = ((highest - lowest) / lowest) * 100 if lowest else 0

    return {
        "markets": markets,
        "spread": round(spread, 2),
        "lowest": lowest,
        "highest": highest,
        "alert": spread > SPREAD_ALERT_PERCENT,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

@app.get("/api")
async def api():
    return await scan_markets()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
<title>PI Market Checker</title>
<style>
body {
    background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    font-family: Arial;
    color: white;
    text-align: center;
}
.container {
    margin-top: 40px;
}
.card {
    background: rgba(255,255,255,0.1);
    padding: 15px;
    margin: 10px;
    border-radius: 15px;
    backdrop-filter: blur(10px);
}
.alert {
    color: #ff4d4d;
    font-weight: bold;
}
.green {
    color: #00ff99;
}
</style>
</head>
<body>
<div class="container">
<h1>🚀 PI/USDT Global Market Checker</h1>
<div id="data">Loading...</div>
</div>

<script>
async function loadData() {
    const res = await fetch("/api");
    const data = await res.json();

    if (!data.markets.length) {
        document.getElementById("data").innerHTML =
        "<div class='card'>No PI/USDT market found.</div>";
        return;
    }

    let html = "";
    data.markets.forEach(m => {
        html += `
        <div class="card">
            <h3>${m.exchange.toUpperCase()}</h3>
            <p>Price: <span class="green">$${m.price}</span></p>
            <p>Volume: ${m.volume}</p>
        </div>
        `;
    });

    html += `
    <div class="card">
        <h2>Spread: ${data.spread}%</h2>
        ${data.alert ? "<div class='alert'>⚠ ARBITRAGE OPPORTUNITY DETECTED</div>" : ""}
        <p>Lowest: $${data.lowest}</p>
        <p>Highest: $${data.highest}</p>
        <p>Updated: ${data.timestamp}</p>
    </div>
    `;

    document.getElementById("data").innerHTML = html;
}

loadData();
setInterval(loadData, 10000);
</script>
</body>
</html>
"""
