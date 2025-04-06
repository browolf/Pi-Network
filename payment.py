'''You can send payments through api.mainnet.minepi.com if you  know your secret key and the destination wallet, 
without using the Pi SDK

The inputs of this script
1. Destination wallet address starting with G
2. Your wallet secret key starting with S
3. Payment amount 

the response of a successful payment is a json object of various fields including the transaction hash

'''


from stellar_sdk import Keypair, Server, TransactionBuilder, Asset, exceptions
from stellar_sdk.exceptions import Ed25519PublicKeyInvalidError

#test for a valid unregistered wallet
#GAJMF3PZL4LQTQNPLASFIR7JYJTNKY3H3Y65ZFOOSHONUZR3R6O6QLB7
#test for a valid unregistered secret key
#SDIMOETTFURK264PCCBSRNUPILXLIADAY2S6F4DGWQ6XYH5GCXORLTGJ


# Configuration
horizon_server = "https://api.mainnet.minepi.com"
network_passphrase = "Pi Network"
base_fee = 1000000
server = Server(horizon_server)

# Prompt for inputs
destination_address = input("Enter the destination public key: ").strip()

# Validate destination format
try:
    Keypair.from_public_key(destination_address)
except Ed25519PublicKeyInvalidError:
    print("Invalid destination public key format.")
    exit()

# Validate destination account
try:
    server.load_account(destination_address)
except exceptions.NotFoundError:
    print("Destination account not found on the network.")
    exit()


existing_secret_key = input("Enter your secret key: ").strip()

# Set up keypair and server
existing_keypair = Keypair.from_secret(existing_secret_key)

# Validate sender account
try:
    existing_account = server.load_account(existing_keypair.public_key)
except exceptions.NotFoundError:
    print("Sender account not found on the network.")
    exit()


send_amount = float(input("Enter amount to send: ").strip())


# Build the transaction
transaction = (
    TransactionBuilder(
        source_account=existing_account,
        network_passphrase=network_passphrase,
        base_fee=base_fee
    )
    .append_payment_op(
        destination=destination_address,
        amount=send_amount,
        asset=Asset.native()  # Native PI token
    )
    .set_timeout(30)
    .build()
)

# Sign and submit the transaction
transaction.sign(existing_keypair)

try:
    response = server.submit_transaction(transaction)
    print("Transaction successful!")
    print(response)
except exceptions.BadRequestError as e:
    print("Transaction failed with result codes:")
    print(e.extras.get('result_codes', {}))
except exceptions.ConnectionError as e:
    print("Connection error occurred:", e)
except exceptions.TimeoutError as e:
    print("Timeout error occurred:", e)
except exceptions.UnknownRequestError as e:
    print("Unknown request error occurred:", e)
