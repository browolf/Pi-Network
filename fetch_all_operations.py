# -----------------------------------------------------------------------------
# Pi Network Horizon Operations Exporter
# -----------------------------------------------------------------------------
# This script fetches the *full operations history* for a single Pi Network
# account using the public Horizon-compatible API at:
#
#     https://api.mainnet.minepi.com
#
# It paginates through all account operations in ascending ledger order and
# writes them to a CSV file with the following columns:
#
#   type, source, from, to, amount, asset, transaction_hash, date
#
# Notes:
# - Dates are resolved via the transaction endpoint and normalized to UTC.
# - A simple in-memory cache is used to avoid refetching transaction timestamps.
# - Designed to run unattended (no interactive paging).
# - Includes optional rate-limit throttling between pages.
#
# This tool is intended for independent ledger analysis, auditing, and research.
# No private keys are required or used.
#
# -----------------------------------------------------------------------------

#!/usr/bin/env python3
import csv
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import requests

ACCOUNT_ID = "GCD3SZ3TFJAESWFZFROZZHNRM5KWFO25TVNR6EMLWNYL47V5A72HBWXP"
HORIZON_URL = "https://api.mainnet.minepi.com"

PAGE_LIMIT = 200
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_PAGES = 1  # set >0 if Pi rate-limits


def iso_to_utc(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def horizon_get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_tx_created_at(tx_hash: str, cache: Dict[str, str]) -> str:
    if not tx_hash:
        return ""
    if tx_hash in cache:
        return cache[tx_hash]

    tx = horizon_get(f"{HORIZON_URL}/transactions/{tx_hash}")
    created_at = tx.get("created_at", "")
    cache[tx_hash] = iso_to_utc(created_at) if created_at else ""
    return cache[tx_hash]


def op_asset_string(op: Dict[str, Any]) -> str:
    at = op.get("asset_type")
    if not at:
        return ""
    if at == "native":
        return "native"
    code = op.get("asset_code", "")
    issuer = op.get("asset_issuer", "")
    if code and issuer:
        return f"{code}:{issuer}"
    return at


def pick(d: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            return str(v)
    return ""


def main() -> int:
    out_csv = f"operations_{ACCOUNT_ID}.csv"

    url = f"{HORIZON_URL}/accounts/{ACCOUNT_ID}/operations"
    params = {"limit": PAGE_LIMIT, "order": "asc"}

    tx_date_cache: Dict[str, str] = {}

    print(f"API: {HORIZON_URL}")
    print(f"Account: {ACCOUNT_ID}")
    print(f"Writing CSV: {out_csv}")
    print("Columns: type, source, from, to, amount, asset, transaction_hash, date")
    print("-" * 140)

    total = 0
    page_num = 0

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "type",
                "source",
                "from",
                "to",
                "amount",
                "asset",
                "transaction_hash",
                "date",
            ],
        )
        writer.writeheader()

        next_url = url
        next_params = params

        while True:
            page_num += 1
            data = horizon_get(next_url, next_params)
            records: List[Dict[str, Any]] = data.get("_embedded", {}).get("records", [])

            if not records:
                break

            for op in records:
                row = {
                    "type": pick(op, "type"),
                    "source": pick(op, "source_account"),
                    "from": pick(op, "from", "funder", "source_account"),
                    "to": pick(op, "to", "account", "created_account"),
                    "amount": pick(op, "amount", "starting_balance"),
                    "asset": op_asset_string(op),
                    "transaction_hash": pick(op, "transaction_hash"),
                    "date": fetch_tx_created_at(pick(op, "transaction_hash"), tx_date_cache),
                }

                writer.writerow(row)
                f.flush()

                print(
                    f"{row['date']}\t{row['type']}\t"
                    f"{row['amount']}\t{row['asset']}\t"
                )

                total += 1

            links = data.get("_links", {})
            next_link = links.get("next", {}).get("href")

            if not next_link:
                break

            next_url = next_link
            next_params = None

            if SLEEP_BETWEEN_PAGES > 0:
                time.sleep(SLEEP_BETWEEN_PAGES)

    print(f"\nDone. Total operations written: {total}")
    print(f"CSV saved to: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
