'''
This script will find PI/USDT markets on ccxt and display the current price
created by https://x.com/PiNetworkUpdate
'''


import ccxt
import urllib3

# Suppress SSL warnings (only needed if using verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("ccxt Results:")
for exchange_id in ccxt.exchanges:
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            "enableRateLimit": True,
            "verify": False,  # remove if SSL fixed properly
        })

        exchange.load_markets()

        for symbol in exchange.symbols:
            if symbol == "PI/USDT":
                ticker = exchange.fetch_ticker(symbol)
                last_price = ticker.get("last")

               
                print(f"Found on {exchange_id}: {symbol} @ {last_price}")

    except Exception:
        continue
