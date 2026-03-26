#!/usr/bin/env python3
"""
categorize_balances.py — bucket Pi balances from balances.csv in the same folder.

Input : balances.csv  (headers: account_id,balance_pi)
Output: balance_buckets.csv
Also prints a console summary table and locked supply info.
"""

import csv
from decimal import Decimal, getcontext, ROUND_UP, ROUND_HALF_UP
from pathlib import Path
import sys
import os

getcontext().prec = 40

HERE = Path(__file__).resolve().parent
INPUT_CSV  = HERE / "all_wallets.csv"
OUTPUT_CSV = HERE / "balance_buckets.csv"

# Delete existing output file at the very start
if OUTPUT_CSV.exists():
    try:
        os.remove(OUTPUT_CSV)
        print(f"Deleted old {OUTPUT_CSV}")
    except Exception as e:
        sys.stderr.write(f"Could not delete {OUTPUT_CSV}: {e}\n")
        sys.exit(1)

TOTAL_SUPPLY = Decimal("100000000000")  # 100 Billion
ONE_MILLION  = Decimal("1000000")

# Half-open intervals [lo, hi), no overlaps
BINS = [
    ("PCT+EXCH", Decimal("1000000"),   None,       ">= 1M"),
    ("dolphins", Decimal("100000"),    Decimal("1000000"),  "[100k - 1M)"),
    ("tunas",    Decimal("10000"),     Decimal("100000"),   "[10k - 100k)"),
    ("fish",     Decimal("1000"),      Decimal("10000"),    "[1k - 10k)"),
    ("shrimps",  Decimal("100"),       Decimal("1000"),     "[100 - 1k)"),
    ("plankton", Decimal("10"),        Decimal("100"),      "[10 - 100)"),
    ("microbes", Decimal("1"),         Decimal("10"),       "[1 - 10)"),
    ("atoms",    Decimal("0"),         Decimal("1"),        "[0 - 1)"),
]

ORDER = [name for name, *_ in BINS]

def fmt_int(n: int) -> str:
    return f"{n:,}"

def fmt_dec(d: Decimal, places=2, rounding=ROUND_HALF_UP, comma=True) -> str:
    q = Decimal(1).scaleb(-places)  # 10^-places
    s = str(d.quantize(q, rounding=rounding))
    if comma:
        if "." in s:
            i, f = s.split(".", 1)
            return f"{int(i):,}.{f}"
        return f"{int(s):,}"
    return s

def main():
    if not INPUT_CSV.exists():
        sys.stderr.write(f"Missing {INPUT_CSV}\n")
        sys.exit(1)

    counts = {name: 0 for name, *_ in BINS}
    sums   = {name: Decimal("0") for name in counts}
    ranges = {name: rng for name, *_skip, rng in BINS}

    # Stream the big CSV safely
    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                bal = Decimal(str(row["balance_pi"]).strip())
            except Exception:
                continue
            if bal < 0:
                continue

            cat = None
            for name, lo, hi, _rng in BINS:
                if hi is None:
                    if bal >= lo:
                        cat = name; break
                else:
                    if lo <= bal < hi:
                        cat = name; break

            if cat:
                counts[cat] += 1
                sums[cat]   += bal

    # Totals
    total_accounts = sum(counts.values())
    total_pi_all   = sum(sums.values())

    # Write CSV (without raw "total pi" column)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "category name", "range", "number of accounts",
            "total (millions Pi)", "avg pi per account", "% of the supply (100Bill)"
        ])

        rows_for_console = []
        for name in ORDER:
            total_pi = sums[name]
            count    = counts[name]
            total_millions = (total_pi / ONE_MILLION).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            avg = (total_pi / count).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if count > 0 else ""
            pct = (total_pi / TOTAL_SUPPLY * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_UP)

            w.writerow([
                name, ranges[name], count,
                f"{total_millions}",
                f"{avg}" if avg != "" else "",
                f"{pct}"
            ])

            rows_for_console.append((
                name,
                ranges[name],
                fmt_int(count),
                fmt_dec(total_millions, 2),
                (fmt_dec(avg, 1) if avg != "" else ""),
                fmt_dec(pct, 2, rounding=ROUND_UP, comma=False) + "%"
            ))

        # grand total row
        total_millions_all = (total_pi_all / ONE_MILLION).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        avg_all = (total_pi_all / total_accounts).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if total_accounts > 0 else ""
        pct_all = (total_pi_all / TOTAL_SUPPLY * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_UP)

        w.writerow([
            "TOTAL", "--", total_accounts,
            f"{total_millions_all}",
            f"{avg_all}" if avg_all != "" else "",
            f"{pct_all}"
        ])

    # Console summary
    headers = [
        "category", "range", "accounts",
        "total (M Pi)", "avg pi/account", "% of supply"
    ]
    cols = list(zip(*(
        [headers] + [
            [*r] for r in rows_for_console + [(
                "TOTAL", "--", fmt_int(total_accounts),
                fmt_dec(total_millions_all, 2),
                (fmt_dec(avg_all, 1) if avg_all != "" else ""),
                fmt_dec(pct_all, 2, rounding=ROUND_UP, comma=False) + "%"
            )]
        ]
    )))
    widths = [max(len(str(x)) for x in col) for col in cols]

    def row_to_line(row):
        return "  ".join(str(val).rjust(widths[i]) if i in (2,3,4,5) else str(val).ljust(widths[i]) for i, val in enumerate(row))

    print("\nSummary:")
    print(row_to_line(headers))
    print(row_to_line(["-"*w for w in widths]))
    for r in rows_for_console:
        print(row_to_line(r))
    print(row_to_line(["-"*w for w in widths]))
    print(row_to_line((
        "TOTAL", "--", fmt_int(total_accounts),
        fmt_dec(total_millions_all, 2),
        (fmt_dec(avg_all, 1) if avg_all != "" else ""),
        fmt_dec(pct_all, 2, rounding=ROUND_UP, comma=False) + "%"
    )))

    # Locked supply
    locked_pi = (TOTAL_SUPPLY - total_pi_all) if TOTAL_SUPPLY > total_pi_all else Decimal("0")
    locked_pct = (locked_pi / TOTAL_SUPPLY * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_UP)

    print(f"\nLocked supply : {locked_pct}%  ({fmt_dec(locked_pi, 2)} Pi)")

    print(f"\nWrote {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
