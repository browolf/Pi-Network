"""
Fetch Pi Mainnet create_account operations and aggregate counts per day/month.

Change the start gate to limit the search to a given past date

1 month will be around 15k pages 

"""

import csv
import sys
import time
import requests
from datetime import datetime, timezone
from collections import Counter

HORIZON_URL = "https://api.mainnet.minepi.com"
OPS_URL = f"{HORIZON_URL}/operations"

# -----------------------------
# Config
# -----------------------------
ORDER = "desc"
LIMIT = 200
SLEEP_SECONDS = 0.2

START_DATE = "2026-01-01"
END_DATE = None

RAW_OUT = "create_account_records.csv"
DAY_OUT = "create_account_per_day.csv"
MONTH_OUT = "create_account_per_month.csv"


def parse_iso8601_utc(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def iso_date(d: datetime) -> str:
    return d.date().isoformat()


def iso_month(d: datetime) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def main():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    start_dt = parse_iso8601_utc(START_DATE + "T00:00:00Z") if START_DATE else None
    end_dt = parse_iso8601_utc(END_DATE + "T23:59:59Z") if END_DATE else None

    params = {"order": ORDER, "limit": LIMIT}
    next_url = OPS_URL

    day_counts = Counter()
    month_counts = Counter()

    fetched = 0
    matched = 0
    page_num = 0

    raw_headers = [
        "created_at",
        "date",
        "month",
        "operation_id",
        "transaction_hash",
        "source_account",
        "account",
        "starting_balance",
        "paging_token",
    ]

    with open(RAW_OUT, "w", newline="", encoding="utf-8") as raw_f:
        raw_writer = csv.DictWriter(raw_f, fieldnames=raw_headers)
        raw_writer.writeheader()

        while True:
            page_num += 1

            if next_url == OPS_URL:
                r = session.get(next_url, params=params, timeout=30)
            else:
                r = session.get(next_url, timeout=30)

            if r.status_code != 200:
                print(f"HTTP {r.status_code}: {r.text[:300]}", file=sys.stderr)
                sys.exit(1)

            data = r.json()
            records = data.get("_embedded", {}).get("records", [])
            if not records:
                break

            fetched += len(records)

            # Count create_account ops on THIS page only
            page_create_count = 0

            stop_due_to_start = False

            for op in records:
                created_at = op.get("created_at")
                if not created_at:
                    continue

                dt = parse_iso8601_utc(created_at)

                if end_dt and dt > end_dt:
                    continue

                if start_dt and dt < start_dt and ORDER.lower() == "desc":
                    stop_due_to_start = True
                    break

                if op.get("type") != "create_account":
                    continue

                # ✅ This is a create_account operation
                page_create_count += 1
                matched += 1

                d = iso_date(dt)
                m = iso_month(dt)

                day_counts[d] += 1
                month_counts[m] += 1

                raw_writer.writerow({
                    "created_at": created_at,
                    "date": d,
                    "month": m,
                    "operation_id": op.get("id"),
                    "transaction_hash": op.get("transaction_hash"),
                    "source_account": op.get("source_account"),
                    "account": op.get("account"),
                    "starting_balance": op.get("starting_balance"),
                    "paging_token": op.get("paging_token"),
                })

            # ✅ Print page result ONLY if > 0
            if page_create_count > 0:
                print(f"Page {page_num}: {page_create_count} create_account ops")

            # Stop early if cutoff reached
            if stop_due_to_start:
                break

            # Pagination
            next_url = data.get("_links", {}).get("next", {}).get("href")
            if not next_url:
                break

            time.sleep(SLEEP_SECONDS)

    # Write aggregates
    with open(DAY_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "create_account_count"])
        for d in sorted(day_counts.keys()):
            w.writerow([d, day_counts[d]])

    with open(MONTH_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "create_account_count"])
        for m in sorted(month_counts.keys()):
            w.writerow([m, month_counts[m]])

    print()
    print(f"✅ Total create_account ops saved: {matched:,}")
    print(f"✅ Raw records: {RAW_OUT}")
    print(f"✅ Per-day:     {DAY_OUT}")
    print(f"✅ Per-month:   {MONTH_OUT}")


if __name__ == "__main__":
    main()
