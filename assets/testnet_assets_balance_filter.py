"""
Export listed assets from Pi Testnet Horizon (/assets) to a CSV.

- Output filename is ALWAYS: YYYYMMDD-HHMMSS-pi-testnet-assets.csv
- Sleeps 0.2 seconds between pages (fixed)
- ONLY saves assets where balances.authorized > 1 (excludes NFTs)
- Progress is a SINGLE updating line
- The counter counts ONLY the filtered assets written to the CSV

At the time of writing: Pages scanned: 575 | Assets written: 363 | 200 tokens per page

"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_HORIZON = "https://api.testnet.minepi.com"
ASSETS_ENDPOINT = "/assets"

# Included fields (per your spec)
FIELDS = [
    "toml_href",
    "asset_type",
    "asset_code",
    "asset_issuer",
    "paging_token",
    "num_claimable_balances",
    "num_liquidity_pools",
    "accounts_authorized",
    "accounts_unauthorized",
    "claimable_balances_amount",
    "liquidity_pools_amount",
    "balances_authorized",
]

PAGE_SLEEP_SECONDS = 0.2


def timestamped_outfile() -> str:
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{ts}-pi-testnet-assets.csv"


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=8,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def safe_get(d: Dict[str, Any], *path: str, default: Any = "") -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def normalize_asset_row(asset: Dict[str, Any]) -> Dict[str, Any]:
    toml_href = safe_get(asset, "_links", "toml", "href", default="")
    accounts = asset.get("accounts") or {}
    balances = asset.get("balances") or {}

    return {
        "toml_href": toml_href,
        "asset_type": asset.get("asset_type", ""),
        "asset_code": asset.get("asset_code", ""),
        "asset_issuer": asset.get("asset_issuer", ""),
        "paging_token": asset.get("paging_token", ""),
        "num_claimable_balances": asset.get("num_claimable_balances", 0),
        "num_liquidity_pools": asset.get("num_liquidity_pools", 0),
        "accounts_authorized": accounts.get("authorized", 0),
        "accounts_unauthorized": accounts.get("unauthorized", 0),
        "claimable_balances_amount": asset.get("claimable_balances_amount", "0.0000000"),
        "liquidity_pools_amount": asset.get("liquidity_pools_amount", "0.0000000"),
        "balances_authorized": balances.get("authorized", "0.0000000"),
    }


def iter_assets_pages(
    session: requests.Session,
    horizon_base: str,
    page_limit: int,
):
    """
    Yields (page_no, records_list) for each page.
    """
    url = f"{horizon_base.rstrip('/')}{ASSETS_ENDPOINT}?limit={page_limit}&order=asc"
    page_no = 0

    while url:
        page_no += 1

        r = session.get(url, timeout=45)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} from Horizon: {r.text[:400]}")

        payload = r.json()
        records = safe_get(payload, "_embedded", "records", default=[])
        if not isinstance(records, list):
            raise RuntimeError("Unexpected Horizon response: _embedded.records is not a list")

        yield page_no, records

        next_href = safe_get(payload, "_links", "next", "href", default=None)
        if not next_href or next_href == url:
            return

        time.sleep(PAGE_SLEEP_SECONDS)
        url = next_href


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Export Pi Testnet Horizon /assets to CSV (authorized balance > 1 only)."
    )
    ap.add_argument(
        "--horizon",
        default=DEFAULT_HORIZON,
        help=f"Horizon base URL (default: {DEFAULT_HORIZON})",
    )
    ap.add_argument(
        "--page-limit",
        type=int,
        default=200,
        help="Assets per page (default: 200)",
    )
    args = ap.parse_args()

    outfile = timestamped_outfile()
    session = make_session()

    written = 0
    last_page_scanned: Optional[int] = None

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()

        for page_no, records in iter_assets_pages(session, args.horizon, args.page_limit):
            last_page_scanned = page_no

            # Single-line progress
            print(
                f"\rPages scanned: {page_no} | Assets written: {written} | Last page size: {len(records)}",
                end="",
                flush=True,
            )

            for asset in records:
                # ✅ Filter: only save assets where balances.authorized > 1
                balances = asset.get("balances") or {}
                authorized_str = balances.get("authorized", "0")

                try:
                    authorized_val = float(authorized_str)
                except ValueError:
                    authorized_val = 0.0

                if authorized_val > 1:
                    w.writerow(normalize_asset_row(asset))
                    written += 1

                    # Update progress line after each write
                    print(
                        f"\rPages scanned: {page_no} | Assets written: {written} | Last page size: {len(records)}",
                        end="",
                        flush=True,
                    )

    print()
    if last_page_scanned is None:
        print("No pages scanned (unexpected).")
        return 2

    print(f"Done. Saved {written} assets (authorized balance > 1) to {outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
