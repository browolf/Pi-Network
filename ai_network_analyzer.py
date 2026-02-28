# ai_network_analyzer.py

import requests
import statistics
import json
from collections import defaultdict
from datetime import datetime

HORIZON_URL = "https://api.mainnet.minepi.com"

class PiNetworkAIAnalyzer:

    def __init__(self):
        self.operations = []
        self.wallet_activity = defaultdict(float)

    def fetch_operations(self, limit=200):
        print("Fetching latest operations...")
        url = f"{HORIZON_URL}/operations?order=desc&limit={limit}"
        response = requests.get(url)
        data = response.json()
        self.operations = data['_embedded']['records']

    def analyze_volume(self):
        total_volume = 0
        for op in self.operations:
            if op['type'] == "payment":
                amount = float(op.get('amount', 0))
                total_volume += amount
        return total_volume

    def analyze_wallet_activity(self):
        for op in self.operations:
            if op['type'] == "payment":
                source = op['source_account']
                amount = float(op.get('amount', 0))
                self.wallet_activity[source] += amount

        sorted_wallets = sorted(
            self.wallet_activity.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_wallets[:10]

    def detect_whales(self, threshold=10000):
        whales = []
        for wallet, volume in self.wallet_activity.items():
            if volume >= threshold:
                whales.append(wallet)
        return whales

    def calculate_network_health(self):
        volumes = list(self.wallet_activity.values())
        if not volumes:
            return 0

        avg_volume = statistics.mean(volumes)
        variance = statistics.pstdev(volumes)

        score = min(100, (avg_volume / (variance + 1)) * 10)
        return round(score, 2)

    def generate_report(self):
        volume = self.analyze_volume()
        top_wallets = self.analyze_wallet_activity()
        whales = self.detect_whales()
        health_score = self.calculate_network_health()

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_volume": volume,
            "top_wallets": top_wallets,
            "whales_detected": whales,
            "network_health_score": health_score
        }

        with open("pi_network_ai_report.json", "w") as f:
            json.dump(report, f, indent=4)

        print("AI Network Report Generated Successfully!")
        return report


if __name__ == "__main__":
    analyzer = PiNetworkAIAnalyzer()
    analyzer.fetch_operations()
    analyzer.generate_report()
