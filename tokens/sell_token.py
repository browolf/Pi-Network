from stellar_sdk import (
    Server,
    Keypair,
    TransactionBuilder,
    Asset,
    exceptions
)
from _keys import dist_secret, issuer   # <<-- issuer is already the PUBLIC key
import sys

# ---- CONFIG ----
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1000000
TIMEOUT = 60

ASSET_CODE = "GCV"
ISSUER = issuer          # <-- use the public key from _keys.py

SELL_AMOUNT = "50"       # how much GCV to sell
PRICE = "100"            # 1 GCV = 0.1 XLM

server = Server(HORIZON_URL)


def load_or_exit(pub):
    try:
        return server.load_account(pub)
    except exceptions.NotFoundError:
        print("Account not found:", pub)
        sys.exit(1)


def main():
    print("=== Create DEX Offer: Sell GCV for XLM ===")

    # Load distributor keys
    dist_kp = Keypair.from_secret(dist_secret)
    dist_pub = dist_kp.public_key

    dist_acct = load_or_exit(dist_pub)

    # Define assets
    gcv = Asset(code=ASSET_CODE, issuer=ISSUER)
    pi = Asset.native()

    # Build offer
    builder = (
        TransactionBuilder(
            source_account=dist_acct,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=BASE_FEE,
        )
        .append_manage_sell_offer_op(
            selling=gcv,
            buying=pi,
            amount=SELL_AMOUNT,
            price=PRICE,
        )
    )

    tx = builder.set_timeout(TIMEOUT).build()
    tx.sign(dist_kp)

    try:
        resp = server.submit_transaction(tx)
        print("✓ Offer successfully created.")
        print(resp)
    except Exception as e:
        print("❌ Offer failed:", e)
        if hasattr(e, "extras"):
            print("Result codes:", e.extras.get("result_codes"))


if __name__ == "__main__":
    main()
