from stellar_sdk import (
    Server,
    Keypair,
    TransactionBuilder,
    Asset,
    exceptions
)
from _keys import dist_secret, issuer
import sys

# ---- CONFIG ----
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1000000
TIMEOUT = 60

ASSET_CODE = "GCV"
ISSUER = issuer

# <<<--- ENTER YOUR OFFER ID HERE --->
# https://api.testnet.minepi.com/accounts/<your_distributor_pub>/offers
OFFER_ID = 123456

server = Server(HORIZON_URL)


def load_or_exit(pub):
    try:
        return server.load_account(pub)
    except exceptions.NotFoundError:
        print("Account not found:", pub)
        sys.exit(1)


def main():
    print(f"=== Cancel DEX Offer {OFFER_ID} ===")
    
    # Keys
    dist_kp = Keypair.from_secret(dist_secret)
    dist_pub = dist_kp.public_key
    
    dist_acct = load_or_exit(dist_pub)
    
    # Assets
    gcv = Asset(ASSET_CODE, ISSUER)
    pi = Asset.native()
    
    # Cancel offer by setting amount = 0
    builder = (
        TransactionBuilder(
            source_account=dist_acct,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=BASE_FEE,
        )
        .append_manage_sell_offer_op(
            selling=gcv,
            buying=pi,
            amount="0",            # <-- CANCEL
            price="1",             # ignored for cancel
            offer_id=OFFER_ID
        )
        .set_timeout(TIMEOUT)
    )
    
    tx = builder.build()
    tx.sign(dist_kp)
    
    try:
        resp = server.submit_transaction(tx)
        print("✓ Offer cancelled.")
        print(resp)
    except Exception as e:
        print("❌ Failed to cancel:", e)
        if hasattr(e, "extras"):
            print("Result codes:", e.extras.get("result_codes"))


if __name__ == "__main__":
    main()
