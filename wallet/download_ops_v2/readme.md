# Pi Horizon Operation Extraction Tools

This repository contains two small utility scripts for working with Pi Mainnet Horizon operation data exported to CSV.

They are designed for bulk ledger inspection and downstream analysis rather than interactive use.
The workflow is intentionally simple and reproducible.

---

## Overview

### Script 1 — Operation Export & Flatten

This script downloads **all operations for a specified account** from the Pi Mainnet Horizon API and writes them to a flattened CSV.

It performs:

1. Pagination through `/accounts/{account}/operations`
2. JSON capture of each operation record
3. Flattening of nested structures into dot-notation columns
4. Removal of non-useful metadata fields
5. CSV output
6. Automatic deletion of temporary intermediate data

Nested Horizon fields such as:

```
_links.self.href
_links.transaction.href
```

become:

```
_links.self.href
_links.transaction.href
```

Columns can be filtered via the `DROP_FIELDS` set inside the script.

This produces a dataset suitable for:

* Ledger flow inspection
* Account behaviour analysis
* Payment observation
* Data aggregation pipelines
* Excel / Pandas ingestion

---

### Script 2 — Muxed Payment Aggregator

This script operates on the flattened CSV produced by Script 1.

It aggregates Pi sent to muxed addresses by:

1. Reading the CSV
2. Selecting rows containing:

```
to_muxed
amount
```

3. Summing amounts grouped by muxed destination
4. Writing output:

```
mux_address,amount
```

This enables rapid identification of:

* Custodial routing
* Exchange-style deposit flows
* Payment clustering
* Address distribution patterns

No operation-type logic is applied.
The script performs exactly one task — grouping and summation.

---

## Typical Workflow

### Step 1 — Export Operations

Run:

```
python export_operations.py
```

Provide account address when prompted.

Output:

```
ops-<ACCOUNT>.csv
```

---

### Step 2 — Aggregate Mux Flows

Run:

```
python sum_mux.py ops-<ACCOUNT>.csv
```

Output:

```
mux_sums.csv
```

---

## Design Philosophy

These scripts intentionally avoid:

* SDK abstractions
* Database requirements
* Persistent state
* External dependencies beyond `requests`

They operate directly on Horizon responses and CSV data to ensure:

* Transparency
* Reproducibility
* Easy inspection
* Minimal setup friction

They are intended as building blocks within larger analysis pipelines rather than polished end-user tools.

---

## Requirements

Python 3.9+

Install dependency:

```
pip install requests
```

---

## Notes

* CSV column structure depends on Horizon operation types observed
* Large accounts may produce very large files
* Pagination respects Horizon limits
* Rate throttling is included
* Decimal precision is preserved in aggregation

---

## License

Use freely. No warranty.
