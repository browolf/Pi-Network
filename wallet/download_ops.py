#!/usr/bin/env python3
# =============================================================================
# Pi Network Wallet Operations Downloader
# =============================================================================
#
# Description:
#   Downloads the operation history of a Pi Network wallet using the
#   Pi Mainnet Horizon API and exports the results to a CSV file.
#
#   Designed for blockchain research, wallet activity monitoring,
#   transaction analysis and historical data collection.
#
# Features:
#   - Prompts for a Pi wallet address with checksum validation
#   - Retrieves operations using paginated Horizon API requests
#   - Supports all operation types, including claimable balances
#   - Records timestamps, ledger numbers, amounts and transaction hashes
#   - Identifies incoming and outgoing payments where applicable
#   - Supports transaction memo extraction when transaction joining is enabled
#   - Automatically retries failed requests and handles API rate limiting
#   - Resumes interrupted downloads without duplicating operations
#   - Displays live progress, download speed and operation counts
#   - Exports results to a structured CSV file
#
# Requirements:
#   Python 3.9+
#   requests
#
# Installation:
#   pip install requests
#
# Usage:
#   python pi_operations.py
#
#   Enter the Pi wallet address when prompted.
#   If a previous CSV exists, choose to resume or overwrite.
#
# Output:
#   operations_<WALLET_ADDRESS>.csv
#
# API:
#   https://api.mainnet.minepi.com
#
# Notes:
#   - Uses publicly accessible blockchain data.
#   - Does not require wallet private keys or authentication.
#   - Historical coverage depends on Horizon data availability.
#   - Payment amounts and directions may not apply to all operation types.
#   - Memos belong to transactions and require transaction data to be joined.
#
# Disclaimer:
#   This is an independent, open-source blockchain analysis utility.
#   It is not affiliated with or endorsed by Pi Network.
#
# =============================================================================


#!/usr/bin/env python3

import base64
import binascii
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ==========================================
# CONFIGURATION
# ==========================================

HORIZON_URL = "https://api.mainnet.minepi.com"

PAGE_LIMIT = 200
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_PAGES = 0.1
MAX_RETRIES = 6

CSV_FIELDS = [
    "operation_id",
    "ledger",
    "date",
    "type",
    "direction",
    "source",
    "from",
    "to",
    "amount",
    "asset",
    "claimable_balance_id",
    "claimants",
    "transaction_hash",
    "paging_token",
    "memo_type",
    "memo",
]


# ==========================================
# WALLET VALIDATION
# ==========================================

def valid_wallet(account_id):
    """Validate Stellar G-address and checksum."""
    if len(account_id) != 56 or not account_id.startswith("G"):
        return False

    try:
        raw = base64.b32decode(account_id)
    except (binascii.Error, ValueError):
        return False

    if len(raw) != 35 or raw[0] != 48:
        return False

    expected = binascii.crc_hqx(raw[:-2], 0)
    actual = int.from_bytes(raw[-2:], "little")

    return expected == actual


def request_wallet():
    while True:
        account_id = input(
            "Enter Pi wallet account ID: "
        ).strip().upper()

        if valid_wallet(account_id):
            return account_id

        print("Invalid Pi wallet address. Please try again.\n")


# ==========================================
# HTTP SESSION AND RETRIES
# ==========================================

def create_session():
    session = requests.Session()

    retries = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "Accept": "application/json",
        "User-Agent": "PiOperationsDownloader/2.0",
    })

    return session


def horizon_get(session, url, params=None):
    response = session.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


# ==========================================
# DATA FORMATTING
# ==========================================

def iso_to_utc(value):
    if not value:
        return ""

    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    return dt.astimezone(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def pick(data, *keys):
    for key in keys:
        value = data.get(key)

        if isinstance(value, (str, int, float, bool)):
            return str(value)

    return ""


def op_asset_string(op):
    """Extract the operation's asset where available."""

    asset = op.get("asset")

    if isinstance(asset, str):
        return asset

    prefix = ""

    if op.get("type", "").startswith("path_payment"):
        prefix = "destination_"

    asset_type = op.get(prefix + "asset_type")

    if not asset_type:
        return ""

    if asset_type == "native":
        return "native"

    code = op.get(prefix + "asset_code", "")
    issuer = op.get(prefix + "asset_issuer", "")

    if code and issuer:
        return f"{code}:{issuer}"

    return str(asset_type)


def operation_accounts(op):
    """Identify sender and recipient for supported operations."""

    op_type = op.get("type", "")

    if op_type == "create_account":
        return (
            pick(op, "funder", "source_account"),
            pick(op, "account"),
        )

    if op_type == "account_merge":
        return (
            pick(op, "source_account"),
            pick(op, "into"),
        )

    if op_type == "claim_claimable_balance":
        return (
            "",
            pick(op, "claimant"),
        )

    return (
        pick(op, "from", "source_account"),
        pick(op, "to", "account", "created_account"),
    )


def operation_direction(op, account_id, sender, recipient):
    """
    Direction only for operations where sender/recipient
    represent a direct account transfer.
    """

    supported = {
        "payment",
        "create_account",
        "account_merge",
        "path_payment",
        "path_payment_strict_send",
        "path_payment_strict_receive",
    }

    if op.get("type") not in supported:
        return ""

    if not sender or not recipient:
        return ""

    if sender == account_id and recipient == account_id:
        return "self"

    if recipient == account_id:
        return "incoming"

    if sender == account_id:
        return "outgoing"

    return ""


def ledger_from_token(token):
    """
    Stellar's total-order ID encodes the ledger in
    the upper 32 bits.
    """
    try:
        return str(int(token) >> 32)
    except (ValueError, TypeError):
        return ""


def extract_claimants(op):
    claimants = op.get("claimants", [])

    if not isinstance(claimants, list):
        return ""

    addresses = [
        item.get("destination", "")
        for item in claimants
        if isinstance(item, dict)
    ]

    return ";".join(a for a in addresses if a)


def operation_to_row(op, account_id):
    sender, recipient = operation_accounts(op)

    token = pick(op, "paging_token")

    return {
        "operation_id": (
            pick(op, "id")
            if pick(op, "id").isdigit()
            else token
        ),
        "ledger": ledger_from_token(token),
        "date": iso_to_utc(op.get("created_at", "")),
        "type": pick(op, "type"),
        "direction": operation_direction(
            op, account_id, sender, recipient
        ),
        "source": pick(op, "source_account"),
        "from": sender,
        "to": recipient,
        "amount": pick(op, "amount", "starting_balance"),
        "asset": op_asset_string(op),
        "claimable_balance_id": pick(op, "balance_id"),
        "claimants": extract_claimants(op),
        "transaction_hash": pick(op, "transaction_hash"),
        "paging_token": token,
        "memo_type": pick(op.get("transaction") or {}, "memo_type"),
        "memo": pick(op.get("transaction") or {}, "memo"),
    }


# ==========================================
# CSV RECOVERY AND RESUME
# ==========================================

def repair_incomplete_line(path):
    """
    Remove an incomplete final CSV line left by a crash.
    The script writes one operation per physical line.
    """

    with open(path, "rb+") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()

        if size == 0:
            return

        f.seek(-1, os.SEEK_END)

        if f.read(1) == b"\n":
            return

        position = size

        while position > 0:
            block_size = min(8192, position)
            position -= block_size

            f.seek(position)
            block = f.read(block_size)

            index = block.rfind(b"\n")

            if index >= 0:
                new_size = position + index + 1
                f.truncate(new_size)

                print(
                    "Recovered incomplete CSV line "
                    f"({size - new_size} bytes removed)."
                )
                return

        raise ValueError(
            "CSV has no complete header line. "
            "Cannot safely resume."
        )


def scan_existing_csv(path):
    """
    Read the existing CSV to find the last paging token.
    This makes the CSV itself the resume checkpoint.
    """

    total = 0
    last_cursor = None
    first_date = ""
    last_date = ""

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames != CSV_FIELDS:
            raise ValueError(
                "Existing CSV has incompatible columns. "
                "Choose overwrite or use another filename."
            )

        for row in reader:
            token = row.get("paging_token", "")

            if not token or not token.isdigit():
                raise ValueError(
                    "Existing CSV contains an invalid paging token."
                )

            total += 1
            last_cursor = token

            if not first_date:
                first_date = row.get("date", "")

            last_date = row.get("date", "")

    return total, last_cursor, first_date, last_date


def choose_file_mode(path):
    """Ask whether to resume, overwrite or cancel."""

    if not path.exists() or path.stat().st_size == 0:
        return False

    print(f"\nExisting CSV found: {path.name}")

    while True:
        choice = input(
            "[R]esume / [O]verwrite / [C]ancel [R]: "
        ).strip().lower()

        if choice in ("", "r"):
            return True

        if choice == "o":
            return False

        if choice == "c":
            print("Cancelled.")
            return None

        print("Please enter R, O or C.")


# ==========================================
# MAIN DOWNLOADER
# ==========================================

def main():
    print("=" * 65)
    print("       PI NETWORK WALLET OPERATIONS DOWNLOADER")
    print("=" * 65)

    account_id = request_wallet()

    out_csv = Path(f"operations_{account_id}.csv")

    resume = choose_file_mode(out_csv)

    if resume is None:
        return 0

    total = 0
    cursor = None
    first_date = ""
    last_date = ""

    if resume:
        repair_incomplete_line(out_csv)

        total, cursor, first_date, last_date = scan_existing_csv(
            out_csv
        )

        print(f"\nResuming from {total:,} existing operations.")

    print(f"\nAPI:     {HORIZON_URL}")
    print(f"Wallet:  {account_id}")
    print(f"Output:  {out_csv}")
    print(f"Mode:    {'Resume' if resume else 'New download'}")
    print("-" * 65)

    url = f"{HORIZON_URL}/accounts/{account_id}/operations"

    page_num = 0
    new_operations = 0
    start_time = time.monotonic()

    mode = "a" if resume else "w"

    with create_session() as session:
        with open(
            out_csv, mode, newline="", encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=CSV_FIELDS,
            )

            if not resume:
                writer.writeheader()
                f.flush()

            while True:
                params = {
                    "limit": PAGE_LIMIT,
                    "order": "asc",
                    "join": "transactions",
                }

                if cursor:
                    params["cursor"] = cursor

                data = horizon_get(
                    session,
                    url,
                    params=params,
                )

                records = data.get(
                    "_embedded", {}
                ).get("records", [])

                if not records:
                    break

                page_num += 1
                previous_cursor = cursor

                # Validate the page before writing any rows.
                if any(
                    not str(op.get("paging_token", "")).isdigit()
                    for op in records
                ):
                    raise ValueError(
                        "Horizon returned an operation "
                        "without a valid paging token."
                    )

                for op in records:
                    row = operation_to_row(op, account_id)

                    writer.writerow(row)

                    cursor = row["paging_token"]

                    total += 1
                    new_operations += 1

                    if not first_date:
                        first_date = row["date"]

                    last_date = row["date"]

                # Save every completed page to disk.
                f.flush()
                os.fsync(f.fileno())

                if cursor == previous_cursor:
                    raise RuntimeError(
                        "Pagination cursor did not advance."
                    )

                elapsed = max(
                    time.monotonic() - start_time,
                    0.001,
                )

                rate = new_operations / elapsed

                print(
                    f"\rPages: {page_num:,}"
                    f" | Operations: {total:,}"
                    f" | Rate: {rate:,.1f}/sec"
                    f" | Latest: {last_date}",
                    end="",
                    flush=True,
                )

                if SLEEP_BETWEEN_PAGES > 0:
                    time.sleep(SLEEP_BETWEEN_PAGES)

    elapsed = time.monotonic() - start_time

    print("\n")
    print("=" * 65)
    print("DOWNLOAD COMPLETE")
    print("=" * 65)

    print(f"Wallet:             {account_id}")
    print(f"Pages downloaded:   {page_num:,}")
    print(f"New operations:     {new_operations:,}")
    print(f"Total operations:   {total:,}")
    print(f"First operation:    {first_date or 'N/A'}")
    print(f"Latest operation:   {last_date or 'N/A'}")
    print(f"Elapsed time:       {elapsed:,.1f} seconds")
    print(f"CSV saved to:       {out_csv.resolve()}")

    print("=" * 65)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except KeyboardInterrupt:
        print(
            "\n\nDownload interrupted. "
            "Run again and select Resume."
        )
        raise SystemExit(130)

    except (
        requests.RequestException,
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"\n\nError: {exc}")
        print(
            "Any completed CSV records have been preserved. "
            "Run again to resume."
        )
        raise SystemExit(1)
