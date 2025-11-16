from stellar_sdk import (
    Keypair,
    Server,
    TransactionBuilder,
    exceptions
)
from _keys import issuer_secret     # <-- imported here
import sys

# -------- CONFIG --------
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1_000_000   # stroops
TIMEOUT = 60
HOME_DOMAIN = "gcv.com"   # <-- domain to set

server = Server(HORIZON_URL)

def load_account_or_exit(pub):
    try:
        return server.load_account(pub)
    except exceptions.NotFoundError:
        print(f"ERROR: Account {pub} not found on Pi Testnet.")
        sys.exit(1)

def submit_tx(builder, signer):
    tx = builder.set_timeout(TIMEOUT).build()
    tx.sign(signer)
    try:
        resp = server.submit_transaction(tx)
        print("✓ Transaction submitted successfully.")
        return resp
    except Exception as e:
        print("❌ Transaction failed:", e)
        if hasattr(e, "extras"):
            print("Result codes:", e.extras.get("result_codes"))
        sys.exit(1)

def main():
    print("=== Set Home Domain on Pi Testnet (Issuer Account) ===")

    # Loaded from _keys.py
    issuer_kp = Keypair.from_secret(issuer_secret)
    issuer_pub = issuer_kp.public_key

    issuer_acct = load_account_or_exit(issuer_pub)

    print(f"\nSetting home domain to: {HOME_DOMAIN}")

    # Build transaction: set home domain
    builder = TransactionBuilder(
        source_account=issuer_acct,
        network_passphrase=NETWORK_PASSPHRASE,
        base_fee=BASE_FEE
    ).append_set_options_op(
        home_domain=HOME_DOMAIN
    )

    submit_tx(builder, issuer_kp)

    print(f"\n✓ Home domain successfully set to: {HOME_DOMAIN}")
    print("Verify via:")
    print(f"https://api.testnet.minepi.com/accounts/{issuer_pub}")

if __name__ == "__main__":
    main()
