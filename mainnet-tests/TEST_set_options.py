from stellar_sdk import Keypair, Server, TransactionBuilder, exceptions

# Pi Network settings
horizon_server = "https://api.mainnet.minepi.com"
network_passphrase = "Pi Network"
base_fee = 1000000
secret_key = "your secret key"

# Create keypair and connect to server
keypair = Keypair.from_secret(secret_key)
public_key = keypair.public_key
server = Server(horizon_server)

# Load account details
try:
    account = server.load_account(public_key)
except exceptions.NotFoundError:
    print("Account not found on the Pi Network.")
    exit()

# Build transaction to set home domain
tx = (
    TransactionBuilder(
        source_account=account,
        network_passphrase=network_passphrase,
        base_fee=base_fee
    )
    .append_set_options_op(home_domain="reddit.com")
    .set_timeout(30)
    .build()
)
tx.sign(keypair)

# Submit the transaction
try:
    response = server.submit_transaction(tx)
    print("✅ set_options operation (home_domain) succeeded!")
    print(response)
except exceptions.BadRequestError as e:
    print("❌ set_options operation failed:")
    print(f'result_codes: {e}')
except Exception as e:
    print("Unexpected error:", e)
