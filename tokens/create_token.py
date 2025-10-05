"""
------------------------------------------------------------
Pi Testnet Asset Issuance & Distribution Script
------------------------------------------------------------
This script demonstrates how to create and distribute a custom 
asset on the Pi Testnet using the Stellar SDK.

Workflow:
  1. Ensure the distributor account creates a trustline for the new asset.
  2. The issuer account mints (issues) the asset and sends it to the distributor.
  3. Print and verify balances of issuer and distributor accounts.

Key Points:
  - Uses two accounts: 
      A = Issuer (creates the asset, can mint more at any time)
      B = Distributor (receives supply, can send further)
  - Supply is NOT capped: issuer can send more to distributor later.
  - Requires both accounts to already exist and be funded on Pi Testnet.
  - Includes error handling for missing accounts, bad requests, and timeouts.

Configuration:
  - HORIZON_URL: Pi Testnet Horizon server
  - NETWORK_PASSPHRASE: "Pi Testnet"
  - BASE_FEE: Transaction fee in stroops
  - ASSET_CODE: Asset code (e.g., "GCV")
  - TOTAL_SUPPLY: Initial amount to distribute
  - TRUSTLINE_LIMIT: Max asset balance distributor can hold

Usage:
  - Replace <issuer key> and <distributor key> with valid secret keys.
  - Run with Python 3 and `stellar-sdk` installed.
------------------------------------------------------------
"""

from stellar_sdk import (
    Keypair,
    Server,
    TransactionBuilder,
    Asset,
    exceptions,
)
import sys
import time

# ---------- CONFIG ----------
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1_000_000  # stroops
ASSET_CODE = "GCV"
TOTAL_SUPPLY = "7003"  # not fixed; you can mint more later
TRUSTLINE_LIMIT = "1000000000"  # generous limit for distributor
TIMEOUT = 60

server = Server(HORIZON_URL)

def load_account_or_exit(pub):
    try:
        return server.load_account(pub)
    except exceptions.NotFoundError:
        print(f"Account {pub} not found on Pi Testnet. Make sure it's created/funded.")
        sys.exit(1)

def print_balances(label, pubkey):
    acct = server.accounts().account_id(pubkey).call()
    bals = {b["asset_type"] + (":" + b.get("asset_code","") + ":" + b.get("asset_issuer","") if b["asset_type"]!="native" else ""): b["balance"] for b in acct["balances"]}
    print(f"\n[{label}] Balances for {pubkey[:6]}...{pubkey[-6:]}:")
    for k,v in bals.items():
        print(f"  {k:<35} {v}")

def submit_tx(builder, signers):
    tx = builder.set_timeout(TIMEOUT).build()
    for s in signers:
        tx.sign(s)
    try:
        resp = server.submit_transaction(tx)
        return resp
    except exceptions.BadRequestError as e:
        print("BadRequestError:", e)
        if hasattr(e, "extras") and e.extras:
            print("Result codes:", e.extras.get("result_codes"))
        sys.exit(1)
    except exceptions.ConnectionError as e:
        print("Connection error:", e)
        sys.exit(1)
    except exceptions.TimeoutError as e:
        print("Timeout:", e)
        sys.exit(1)
    except exceptions.UnknownRequestError as e:
        print("Unknown request error:", e)
        sys.exit(1)

def main():
    print("=== Pi Testnet: Create & Distribute Asset ===")
    issuer_secret = "<issuer key>"
    dist_secret   = "<distributor key>"

    issuer_kp = Keypair.from_secret(issuer_secret)
    dist_kp   = Keypair.from_secret(dist_secret)

    issuer_pub = issuer_kp.public_key
    dist_pub   = dist_kp.public_key

    # Ensure accounts exist
    issuer_acct = load_account_or_exit(issuer_pub)
    dist_acct   = load_account_or_exit(dist_pub)

    # Define the asset
    asset = Asset(ASSET_CODE, issuer_pub)

    print("\nStep 1/3: Create/ensure trustline on DISTRIBUTOR (B) to GCV...")
    # Build change_trust from distributor
    builder = TransactionBuilder(
        source_account=dist_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_change_trust_op(
        asset=asset,
        limit=TRUSTLINE_LIMIT
    )

    submit_tx(builder, [dist_kp])

    # Re-load accounts after tx
    issuer_acct = server.load_account(issuer_pub)
    dist_acct   = server.load_account(dist_pub)
    print("✓ Trustline set (or already existed).")

    print("\nStep 2/3: Send 7003 GCV from ISSUER (A) → DISTRIBUTOR (B)...")
    builder = TransactionBuilder(
        source_account=issuer_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_payment_op(
        destination=dist_pub,
        amount=TOTAL_SUPPLY,
        asset=asset
    )

    submit_tx(builder, [issuer_kp])
    print("✓ Distribution payment submitted.")

    print("\nStep 3/3: Verify balances...")
    print_balances("Issuer (A)", issuer_pub)
    print_balances("Distributor (B)", dist_pub)

    print("\nDone. Supply is NOT fixed: the issuer can mint more by paying additional GCV from A to B (or others).")

if __name__ == "__main__":
    main()
