#!/usr/bin/env python3
"""
Sum amounts per muxed destination address.

Input:
    Flattened operations CSV

Output:
    mux_sums.csv containing:
        mux_address,amount
"""

import csv
import sys
from decimal import Decimal


def main():
    if len(sys.argv) < 2:
        print("Usage: python sum_mux.py <input.csv>")
        sys.exit(1)

    infile = sys.argv[1]
    outfile = "mux_sums.csv"

    totals = {}

    with open(infile, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if "to_muxed" not in reader.fieldnames:
            print("Column 'to_muxed' not found")
            sys.exit(1)

        if "amount" not in reader.fieldnames:
            print("Column 'amount' not found")
            sys.exit(1)

        for row in reader:
            mux = (row["to_muxed"] or "").strip()
            amt = (row["amount"] or "").strip()

            if not mux or not amt:
                continue

            try:
                amt = Decimal(amt)
            except:
                continue

            totals[mux] = totals.get(mux, Decimal("0")) + amt

    # Write output
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["mux_address", "amount"])

        for mux, total in sorted(totals.items()):
            writer.writerow([mux, str(total)])

    print(f"Done — wrote {len(totals)} mux addresses")
    print(f"Output: {outfile}")


if __name__ == "__main__":
    main()
