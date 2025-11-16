from stellar_sdk import Server
import csv

ACCOUNT_ID = "GCOR3TJAYA4JDV6GJSREO4TRDUW32IA7BQN3IMY553HQ26NL77W7TEAM"
HORIZON_URL = "https://api.mainnet.minepi.com"

# ---------------------------------------------------
# Build a readable summary for each operation
# ---------------------------------------------------
def build_summary(op):
    t = op.get("type")

    if t == "set_options":
        parts = []
        if op.get("signer_key"):
            parts.append(f"add signer {op.get('signer_key')} weight={op.get('signer_weight')}")
        if op.get("master_key_weight") is not None:
            parts.append(f"master_weight={op.get('master_key_weight')}")
        if op.get("low_threshold"):
            parts.append(
                f"thresholds=({op.get('low_threshold')},"
                f"{op.get('med_threshold')},{op.get('high_threshold')})"
            )
        return "set_options: " + ", ".join(parts)

    if t == "payment":
        return f"payment: {op.get('amount')} {op.get('asset_type')} from {op.get('from')} to {op.get('to')}"

    if t == "manage_data":
        return f"manage_data: {op.get('name')} = {op.get('value')}"

    if t == "change_trust":
        return f"change_trust: {op.get('asset_code')} issued by {op.get('asset_issuer')} limit={op.get('limit')}"

    return t  # fallback


# ---------------------------------------------------
# Fetch operations using stellar_sdk with pagination
# ---------------------------------------------------
def fetch_all_operations():
    server = Server(HORIZON_URL)

    call_builder = (
        server.operations()
        .for_account(ACCOUNT_ID)
        .limit(200)
        .order("asc")
    )

    all_ops = []
    records = call_builder.call()["_embedded"]["records"]
    count = 0

    while True:
        all_ops.extend(records)
        count += len(records)
        print(f"Loaded {count} operations...")

        if len(records) < 200:
            break

        next_cursor = records[-1]["paging_token"]
        records = (
            call_builder.cursor(next_cursor)
            .call()["_embedded"]["records"]
        )

    return all_ops


# ---------------------------------------------------
# Save a compact CSV file
# ---------------------------------------------------
def save_minimal_csv(ops, filename="operations_minimal.csv"):
    headers = [
        "id",
        "created_at",
        "type",
        "source_account",
        "transaction_hash",
        "paging_token",
        "summary"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for op in ops:
            writer.writerow({
                "id": op.get("id"),
                "created_at": op.get("created_at"),
                "type": op.get("type"),
                "source_account": op.get("source_account"),
                "transaction_hash": op.get("transaction_hash"),
                "paging_token": op.get("paging_token"),
                "summary": build_summary(op)
            })

    print(f"✅ Saved {len(ops)} operations to {filename}")


# ---------------------------------------------------
# Main
# ---------------------------------------------------
def main():
    ops = fetch_all_operations()
    print(f"Total operations: {len(ops)}")
    save_minimal_csv(ops)


if __name__ == "__main__":
    main()
