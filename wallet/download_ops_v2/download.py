#!/usr/bin/env python3

import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Set

import requests

HORIZON_URL = "https://api.mainnet.minepi.com"

ORDER = "asc"
LIMIT = 200
SLEEP_SECONDS = 0.2
TIMEOUT_SECONDS = 30

START_DATE = ""
END_DATE = ""

# Columns to drop
DROP_FIELDS = {
    "_links.effects.href",
    "_links.precedes.href",
    "_links.self.href",
    "_links.succeeds.href",
    "_links.transaction.href",
    "asset",
    "asset_type",
    "balance_id",
    "derived.date",
    "funder",
    "id",
    "paging_token",
    "sponsor",
    "starting_balance",
    "type_i",
}


# ---------------- Helpers ----------------

def parse_iso8601_utc(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def iso_date(dt: datetime) -> str:
    return dt.date().isoformat()


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def flatten(obj: Any, prefix="") -> Dict[str, Any]:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(flatten(v, key))
            elif isinstance(v, list):
                out[key] = json.dumps(v, separators=(",", ":"))
            else:
                out[key] = v
    else:
        out[prefix] = obj
    return out


def iter_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


# ---------------- Download ----------------

def download_jsonl(account: str, outfile: str):
    ops_url = f"{HORIZON_URL}/accounts/{account}/operations"

    start_dt = parse_iso8601_utc(START_DATE + "T00:00:00Z") if START_DATE else None
    end_dt = parse_iso8601_utc(END_DATE + "T23:59:59Z") if END_DATE else None

    session = requests.Session()
    params = {"order": ORDER, "limit": LIMIT}
    next_url = ops_url

    total = 0
    page = 0

    with open(outfile, "w", encoding="utf-8") as out:
        while True:
            page += 1

            r = session.get(
                next_url,
                params=params if next_url == ops_url else None,
                timeout=TIMEOUT_SECONDS,
            )

            if r.status_code != 200:
                print(r.text[:300])
                sys.exit(1)

            data = r.json()
            records = data.get("_embedded", {}).get("records", [])
            if not records:
                break

            written = 0

            for op in records:
                created = op.get("created_at")
                if created:
                    dt = parse_iso8601_utc(created)
                    if start_dt and dt < start_dt:
                        continue
                    if end_dt and dt > end_dt:
                        continue

                out.write(json.dumps(op) + "\n")
                written += 1
                total += 1

            print(f"Page {page}: kept {written}")

            next_url = data["_links"]["next"]["href"]
            time.sleep(SLEEP_SECONDS)

    return total


# ---------------- CSV Build ----------------

def build_csv(jsonl_path: str, csv_path: str):
    keys: Set[str] = set()

    # Collect keys
    for rec in iter_jsonl(jsonl_path):
        flat = flatten(rec)
        flat["derived.date"] = iso_date(parse_iso8601_utc(rec["created_at"]))
        keys.update(flat.keys())

    # Remove unwanted columns
    keys = {k for k in keys if k not in DROP_FIELDS}

    header = sorted(keys)

    with open(csv_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=header)
        writer.writeheader()

        for rec in iter_jsonl(jsonl_path):
            flat = flatten(rec)
            flat["derived.date"] = iso_date(parse_iso8601_utc(rec["created_at"]))

            row = {k: flat.get(k, "") for k in header}
            writer.writerow(row)

    return len(header)


# ---------------- Main ----------------

def main():
    account = input("Enter account address: ").strip()
    if not account:
        return

    safe = sanitize(account)
    jsonl_file = f"ops-{safe}.jsonl"
    csv_file = f"ops-{safe}.csv"

    print("\nDownloading operations...")
    count = download_jsonl(account, jsonl_file)
    print(f"Saved {count:,} records")

    print("\nFlattening to CSV...")
    cols = build_csv(jsonl_file, csv_file)
    print(f"CSV columns: {cols}")

    os.remove(jsonl_file)

    print("\nDone")
    print(f"Output: {csv_file}")
    print("Temporary JSONL deleted")


if __name__ == "__main__":
    main()
