"""
Pi Network Advanced Intelligence Engine
Production Grade Analytics Module
Author: Clawue884
"""

import asyncio
import aiohttp
import statistics
import json
import csv
from datetime import datetime
from collections import defaultdict
import math

HORIZON_URL = "https://api.mainnet.minepi.com"
OP_LIMIT = 200


class PiNetworkIntelligence:

    def __init__(self):
        self.operations = []
        self.wallet_volume = defaultdict(float)
        self.wallet_count = defaultdict(int)

    # ===============================
    # ASYNC FETCH ENGINE
    # ===============================
    async def fetch_operations(self):
        url = f"{HORIZON_URL}/operations?order=desc&limit={OP_LIMIT}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.operations = data["_embedded"]["records"]

    # ===============================
    # CORE ANALYSIS
    # ===============================
    def process_operations(self):
        for op in self.operations:
            if op["type"] == "payment":
                amount = float(op.get("amount", 0))
                source = op["source_account"]

                self.wallet_volume[source] += amount
                self.wallet_count[source] += 1

    def total_volume(self):
        return sum(self.wallet_volume.values())

    def top_wallets(self, n=10):
        return sorted(
            self.wallet_volume.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]

    # ===============================
    # WHALE DETECTION
    # ===============================
    def detect_whales_dynamic(self):
        volumes = list(self.wallet_volume.values())
        if not volumes:
            return []

        mean = statistics.mean(volumes)
        stdev = statistics.pstdev(volumes)

        threshold = mean + (2 * stdev)

        whales = [
            wallet for wallet, volume in self.wallet_volume.items()
            if volume >= threshold
        ]

        return whales

    # ===============================
    # CENTRALIZATION (GINI INDEX)
    # ===============================
    def gini_coefficient(self):
        volumes = sorted(self.wallet_volume.values())
        if not volumes:
            return 0

        n = len(volumes)
        cumulative = 0

        for i, val in enumerate(volumes):
            cumulative += (i + 1) * val

        total = sum(volumes)
        gini = (2 * cumulative) / (n * total) - (n + 1) / n

        return round(gini, 4)

    # ===============================
    # NETWORK HEALTH SCORE
    # ===============================
    def network_health_score(self):
        volume = self.total_volume()
        unique_wallets = len(self.wallet_volume)
        gini = self.gini_coefficient()

        decentralization_score = (1 - gini) * 40
        activity_score = min(40, unique_wallets / 5)
        liquidity_score = min(20, volume / 10000)

        score = decentralization_score + activity_score + liquidity_score
        return round(min(score, 100), 2)

    # ===============================
    # VELOCITY SCORE
    # ===============================
    def velocity_score(self):
        tx_count = sum(self.wallet_count.values())
        unique_wallets = len(self.wallet_volume)

        if unique_wallets == 0:
            return 0

        velocity = tx_count / unique_wallets
        return round(velocity, 2)

    # ===============================
    # ANOMALY DETECTION
    # ===============================
    def detect_anomalies(self):
        volumes = list(self.wallet_volume.values())
        if not volumes:
            return []

        mean = statistics.mean(volumes)
        stdev = statistics.pstdev(volumes)

        anomalies = [
            wallet for wallet, volume in self.wallet_volume.items()
            if abs(volume - mean) > 3 * stdev
        ]

        return anomalies

    # ===============================
    # REPORT GENERATOR
    # ===============================
    def generate_report(self):

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_volume": self.total_volume(),
            "unique_wallets": len(self.wallet_volume),
            "top_wallets": self.top_wallets(),
            "whales": self.detect_whales_dynamic(),
            "anomalies": self.detect_anomalies(),
            "gini_index": self.gini_coefficient(),
            "velocity_score": self.velocity_score(),
            "network_health_score": self.network_health_score()
        }

        # JSON export
        with open("pi_network_intelligence_report.json", "w") as f:
            json.dump(report, f, indent=4)

        # CSV export (top wallets)
        with open("top_wallets.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Wallet", "Volume"])
            for wallet, volume in self.top_wallets():
                writer.writerow([wallet, volume])

        print("Advanced Intelligence Report Generated")
        return report


# ===============================
# MAIN EXECUTION
# ===============================
async def main():
    engine = PiNetworkIntelligence()
    await engine.fetch_operations()
    engine.process_operations()
    engine.generate_report()


if __name__ == "__main__":
    asyncio.run(main())
