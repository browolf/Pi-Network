import numpy as np

def analyze_market(prices):
    if not prices:
        return "NO DATA"

    values = [p["price"] for p in prices]
    avg = np.mean(values)
    std = np.std(values)

    if std > avg * 0.05:
        return "HIGH VOLATILITY"
    elif std > avg * 0.02:
        return "MODERATE VOLATILITY"
    else:
        return "STABLE MARKET"
