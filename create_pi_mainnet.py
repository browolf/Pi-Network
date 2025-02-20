from stellar_sdk import Keypair, Server, TransactionBuilder, exceptions
import sys


horizon_server = "https://api.mainnet.minepi.com"
network_passphrase = "Pi Network"
base_fee = 1000000
starting_balance = "1"
              


secret_key = input("Enter the secret key of the new account: ")
new_keypair = Keypair.from_secret(secret_key)

# Load the existing account
server = Server(horizon_server)
existing_secret_key = input('Enter your existing account secret key: ')
existing_keypair = Keypair.from_secret(existing_secret_key)
existing_account = server.load_account(existing_keypair.public_key)

# Build the transaction to create the new account
transaction = (
    TransactionBuilder(
        source_account=existing_account,
        network_passphrase=network_passphrase,
        base_fee=base_fee
    )
    .append_create_account_op(destination=new_keypair.public_key, starting_balance=starting_balance)
    .set_timeout(30)
    .build()
)

# Sign the transaction with the existing account's keypair
transaction.sign(existing_keypair)

# Submit the transaction to the network
try:
    response = server.submit_transaction(transaction)
    print("Transaction successful!")
except exceptions.BadRequestError as e:
    result_codes = e.extras.get('result_codes', None)
    print("Transaction failed with result codes:")
    print(result_codes)
except exceptions.ConnectionError as e:
    print("Connection error occurred:", e)
except exceptions.TimeoutError as e:
    print("Timeout error occurred:", e)
except exceptions.UnknownRequestError as e:
    print("Unknown request error occurred:", e)
