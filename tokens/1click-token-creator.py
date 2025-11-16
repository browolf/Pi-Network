from stellar_sdk import (
    Keypair,
    Server,
    TransactionBuilder,
    Asset,
    exceptions,
)
import sys
import time

# ------------ CONFIG ------------
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1_000_000   # stroops
TIMEOUT = 60

# How much Pi to fund each new account with
ISSUER_START_BALANCE = "2"   # Pi
DIST_START_BALANCE   = "2"   # Pi

server = Server(HORIZON_URL)


# ------------ HELPERS ------------

def load_account_or_exit(pub):
    try:
        return server.load_account(pub)
    except exceptions.NotFoundError:
        print(f"ERROR: Account {pub} not found on Pi Testnet.")
        sys.exit(1)


def get_native_balance(pub):
    """Return native Pi balance as float."""
    acct = server.accounts().account_id(pub).call()
    for b in acct["balances"]:
        if b["asset_type"] == "native":
            return float(b["balance"])
    return 0.0


def wait_for_account(pub):
    """Wait until account exists."""
    while True:
        try:
            server.load_account(pub)
            return
        except exceptions.NotFoundError:
            print(f"  Waiting for account to appear on-chain: {pub[:6]}...{pub[-6:]}")
            time.sleep(2)


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
    except Exception as e:
        print("Unknown exception while submitting tx:", e)
        sys.exit(1)


def ensure_positive_amount(name, value):
    try:
        f = float(value)
        if f <= 0:
            raise ValueError
    except ValueError:
        print(f"ERROR: {name} must be a positive number, got '{value}'.")
        sys.exit(1)


# ------------ MAIN WIZARD ------------

def main():
    print("=== Pi Testnet Token Wizard ===")
    print("This script will:")
    print("  • Use an existing wallet to fund two new accounts")
    print("  • Create an ISSUER and DISTRIBUTOR")
    print("  • Mint your custom asset")
    print("  • Set a home domain on the issuer")
    print("  • Create a sell offer on the DEX (Asset / Pi)\n")

    # 1) Ask for funder secret
    fund_secret = input("Enter the SECRET KEY of the existing funding wallet: ").strip()
    try:
        fund_kp = Keypair.from_secret(fund_secret)
    except Exception:
        print("ERROR: Invalid secret key format.")
        sys.exit(1)

    fund_pub = fund_kp.public_key

    # Confirm they know what they're doing
    print("\nPlease confirm this wallet will pay to create 2 new accounts and several transactions.")
    confirm = input("Does it hold enough Pi to proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborting by user request.")
        sys.exit(0)

    # Check balance (soft check, but we'll warn)
    try:
        fund_acct = load_account_or_exit(fund_pub)
        bal = get_native_balance(fund_pub)
    except Exception as e:
        print("ERROR: Could not load funder account or balance:", e)
        sys.exit(1)

    required_min = float(ISSUER_START_BALANCE) + float(DIST_START_BALANCE) + 0.1  # small buffer
    print(f"\nFunder wallet: {fund_pub}")
    print(f"  Native Pi balance: {bal}")
    print(f"  Recommended minimum to proceed: ~{required_min:.2f} Pi")

    if bal < required_min:
        print("WARNING: Balance looks low. You may hit minimum balance limits or fail account creation.")
        cont = input("Continue anyway? (yes/no): ").strip().lower()
        if cont != "yes":
            print("Aborting due to low balance.")
            sys.exit(0)

    # 2) Create issuer & distributor accounts
    print("\n--- Creating issuer & distributor accounts ---")

    issuer_kp = Keypair.random()
    dist_kp   = Keypair.random()

    issuer_pub = issuer_kp.public_key
    dist_pub   = dist_kp.public_key

    print(f"  Issuer     : {issuer_pub}")
    print(f"  Distributor: {dist_pub}")

    builder = TransactionBuilder(
        source_account=fund_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_create_account_op(
        destination=issuer_pub,
        starting_balance=ISSUER_START_BALANCE,
    ).append_create_account_op(
        destination=dist_pub,
        starting_balance=DIST_START_BALANCE,
    )

    submit_tx(builder, [fund_kp])

    # Wait for accounts to show
    print("  Waiting for accounts to be ready on-chain...")
    wait_for_account(issuer_pub)
    wait_for_account(dist_pub)

    issuer_acct = load_account_or_exit(issuer_pub)
    dist_acct   = load_account_or_exit(dist_pub)

    print("✓ Issuer & Distributor successfully created.\n")

    # 3) Ask for asset + config
    asset_code = input("Enter ASSET CODE (1–12 chars): ").strip().upper()
    if not (1 <= len(asset_code) <= 12):
        print("ERROR: Asset code must be between 1 and 12 characters.")
        sys.exit(1)

    home_domain = input("Enter home domain (e.g., gcv.page.gd): ").strip()

    total_supply = input("Enter TOTAL SUPPLY to create (amount to mint): ").strip()
    ensure_positive_amount("Total supply", total_supply)

    amount_to_sell = input("How many tokens to SELL on the DEX?: ").strip()
    ensure_positive_amount("Amount to sell", amount_to_sell)

    price_in_pi = input("Price per token in Pi (e.g., 0.1): ").strip()
    ensure_positive_amount("Price in Pi", price_in_pi)

    # Make sure sell amount <= total supply (soft check)
    if float(amount_to_sell) > float(total_supply):
        print("ERROR: Amount to sell cannot be greater than total supply.")
        sys.exit(1)

    asset = Asset(asset_code, issuer_pub)

    # 4) Set trustline on distributor
    print("\n--- Setting trustline on distributor ---")
    builder = TransactionBuilder(
        source_account=dist_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_change_trust_op(
        asset=asset,
        limit=total_supply,  # limit = total supply
    )

    submit_tx(builder, [dist_kp])

    dist_acct = load_account_or_exit(dist_pub)
    print("✓ Trustline set.\n")

    # 5) Issue tokens from issuer -> distributor
    print(f"--- Issuing {total_supply} {asset_code} to distributor ---")
    issuer_acct = load_account_or_exit(issuer_pub)

    builder = TransactionBuilder(
        source_account=issuer_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_payment_op(
        destination=dist_pub,
        amount=total_supply,
        asset=asset,
    )

    submit_tx(builder, [issuer_kp])

    dist_acct = load_account_or_exit(dist_pub)
    print("✓ Tokens issued.\n")

    # 6) Set home domain on issuer
    if home_domain:
        print(f"--- Setting home domain to '{home_domain}' on issuer ---")
        issuer_acct = load_account_or_exit(issuer_pub)

        builder = TransactionBuilder(
            source_account=issuer_acct,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=BASE_FEE,
        ).append_set_options_op(
            home_domain=home_domain
        )

        submit_tx(builder, [issuer_kp])
        print("✓ Home domain set.\n")
    else:
        print("No home domain provided; skipping set_options.\n")

    # 7) Create DEX sell offer (asset / Pi)
    print(f"--- Creating DEX sell offer: {amount_to_sell} {asset_code} for {price_in_pi} Pi each ---")
    dist_acct = load_account_or_exit(dist_pub)

    builder = TransactionBuilder(
        source_account=dist_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE,
    ).append_manage_sell_offer_op(
        selling=asset,
        buying=Asset.native(),   # Pi (native)
        amount=amount_to_sell,
        price=price_in_pi,
    )

    resp = submit_tx(builder, [dist_kp])

    print("✓ Sell offer created.")
    offer_info = resp.get("effects", None)
    # We won't over-parse here; user can view offers via Horizon.

    # 8) Output keys and summary
    print("\n==============================================")
    print("              SETUP COMPLETE")
    print("==============================================\n")

    print("Funder Wallet (you entered):")
    print(f"  Public: {fund_pub}\n")

    print("Issuer Wallet:")
    print(f"  Public: {issuer_pub}")
    print(f"  SECRET: {issuer_kp.secret}\n")

    print("Distributor Wallet:")
    print(f"  Public: {dist_pub}")
    print(f"  SECRET: {dist_kp.secret}\n")

    print("Token Details:")
    print(f"  Asset Code      : {asset_code}")
    print(f"  Issuer          : {issuer_pub}")
    print(f"  Home Domain     : {home_domain or '(none)'}")
    print(f"  Total Supply    : {total_supply}")
    print(f"  Amount on Sale  : {amount_to_sell}")
    print(f"  Price per Token : {price_in_pi} Pi\n")

    print("You can inspect the distributor account (offers & balances) here:")
    print(f"  https://api.testnet.minepi.com/accounts/{dist_pub}\n")

    print("Done.\n")


if __name__ == "__main__":
    main()
