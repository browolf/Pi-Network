#!/usr/bin/env python3
# =============================================================================
# Pi Network Unique Memo Extractor
# =============================================================================
# Extracts unique transaction memos from a Pi wallet operations CSV.
# Counts payment operations per memo and sorts by frequency (highest first).
#
# Usage:  python extract_unique_memos.py
# Input:  operations_<WALLET_ID>.csv
# Output: unique_memos_<WALLET_ID>.txt
#
# =============================================================================


#!/usr/bin/env python3

import csv
from collections import Counter
from pathlib import Path


PAYMENT_TYPES = {
    "payment",
    "path_payment",
    "path_payment_strict_send",
    "path_payment_strict_receive",
}


def main():
    print("=" * 60)
    print("       PI NETWORK MEMO PAYMENT COUNTER")
    print("=" * 60)

    account_id = input(
        "\nEnter Pi wallet account ID: "
    ).strip().upper()

    if not account_id:
        print("Error: No wallet ID entered.")
        return

    input_csv = Path(f"operations_{account_id}.csv")
    output_txt = Path(f"unique_memos_{account_id}.txt")

    if not input_csv.exists():
        print(f"\nError: CSV file not found: {input_csv}")
        return

    print(f"\nReading: {input_csv}")

    memo_counts = Counter()
    total_operations = 0
    total_payments = 0
    payments_with_memos = 0

    try:
        with open(
            input_csv,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as f:

            reader = csv.DictReader(f)

            required = {"memo", "type"}

            if not required.issubset(reader.fieldnames or []):
                print(
                    "\nError: CSV must contain "
                    "'memo' and 'type' columns."
                )
                return

            for row in reader:
                total_operations += 1

                memo = (row.get("memo") or "").strip()
                op_type = (row.get("type") or "").strip()

                # Preserve every unique memo, even if it
                # appears only on non-payment operations.
                if memo:
                    memo_counts.setdefault(memo, 0)

                if op_type not in PAYMENT_TYPES:
                    continue

                total_payments += 1

                if memo:
                    memo_counts[memo] += 1
                    payments_with_memos += 1

        # Sort by payment count, highest first
        sorted_memos = sorted(
            memo_counts.items(),
            key=lambda item: (-item[1], item[0])
        )

        with open(
            output_txt,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("PAYMENTS\tMEMO\n")
            f.write("-" * 70 + "\n")

            for memo, count in sorted_memos:
                safe_memo = (
                    memo.replace("\\", "\\\\")
                        .replace("\r", "\\r")
                        .replace("\n", "\\n")
                        .replace("\t", "\\t")
                )

                f.write(f"{count}\t{safe_memo}\n")

        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)

        print(f"Total operations:       {total_operations:,}")
        print(f"Total payments:         {total_payments:,}")
        print(f"Payments with memos:    {payments_with_memos:,}")
        print(f"Unique memos:           {len(memo_counts):,}")

        print("\nTop 10 memos by payment count:")
        print("-" * 60)

        for memo, count in sorted_memos[:10]:
            print(f"{count:>8,}  {memo[:45]}")

        print(f"\nText file saved to:\n{output_txt.resolve()}")
        print("=" * 60)

    except (OSError, csv.Error) as e:
        print(f"\nError processing CSV: {e}")


if __name__ == "__main__":
    main()
