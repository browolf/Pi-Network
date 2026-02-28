def calculate_arbitrage(prices):
    if len(prices) < 2:
        return None

    sorted_prices = sorted(prices, key=lambda x: x["price"])
    buy = sorted_prices[0]
    sell = sorted_prices[-1]

    spread = ((sell["price"] - buy["price"]) / buy["price"]) * 100

    return {
        "buy_from": buy["exchange"],
        "sell_to": sell["exchange"],
        "spread_percent": round(spread, 2),
        "potential_profit_per_1000": round((sell["price"] - buy["price"]) * 1000, 2)
    }
