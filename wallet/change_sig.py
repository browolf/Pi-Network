"""
This script adds a new signer to a Stellar- or Pi-based account 
and disables the master key (sets its weight to 0), effectively 
handing over control to the new signer.

It supports three networks:
    1) Stellar Testnet
    2) Pi Testnet
    3) Pi Mainnet

Steps:
    - Prompts the user to choose a network.
    - Generates a new keypair for the replacement signer.
    - Prompts for your current secret key to load the account.
    - Builds and submits a transaction to:
        • Set thresholds to 1 for all levels (low, medium, high).
        • Add the new signer with weight 1.
        • Disable the master key by setting its weight to 0.
    - Submits the transaction and prints the result.

⚠️ Warning:
Once the master key is disabled, you will lose access to the account
unless you have the new signer's secret key. Be sure to back up the 
new secret key securely before submitting the transaction.
"""

from stellar_sdk import Keypair, Server, TransactionBuilder, Signer, exceptions
import sys

choose_server = input("choose testnet 1)Stellar or 2)Pi? or 3)Pi Mainnet ")
# Horizon server and network passphrase
if (choose_server == "1"):
    horizon_server = "https://horizon-testnet.stellar.org"
    network_passphrase = "Test SDF Network ; September 2015"
    base_fee = 100
    starting_balance = "1"
elif (choose_server == "2"):
    horizon_server = "https://api.testnet.minepi.com"
    network_passphrase = "Pi Testnet"
    base_fee = 1000000
    starting_balance = "10"
    print("Need more than 20 to do transaction")
elif (choose_server =="3"):
    horizon_server = "https://api.mainnet.minepi.com"
    network_passphrase = "Pi Network"
    base_fee = 1000000
    starting_balance = "1"
else:
    print("Did not recognise choice")
    sys.exit()  

#Generate a new signature key
new_signer = Keypair.random()
print("THE NEW SIGNATURE")
print("=" * (len(new_signer.public_key)+23))
print(f"New Signer Public Key: {new_signer.public_key}")
print(f"New Signer Secret: {new_signer.secret}")
print("=" * (len(new_signer.public_key)+23))
print("\n\n")


#Load your account
server = Server(horizon_server)
your_secret_key = input('Enter your secret key: ')
your_keypair = Keypair.from_secret(your_secret_key)
account = server.load_account(your_keypair.public_key)

#set thresholds
set_thresholds_op = {
    "low_threshold" : 1,
    "med_threshold" : 1,
    "high_threshold" : 1
    }

#add new signer and disable master key
set_options_op = {
    "signer" : Signer.ed25519_public_key(new_signer.public_key,1),
    "master_weight" : 0
}

#Build the transaction

transaction = (
    TransactionBuilder(
        source_account = account,
        network_passphrase = network_passphrase,
        base_fee = base_fee
    )
    .append_set_options_op(**set_thresholds_op)
    .append_set_options_op(**set_options_op)
    .set_timeout(30)
    .build()
)

#sign the transaction
transaction.sign(your_keypair)

#submit transaction to network
try:
    response = server.submit_transaction(transaction)
    print("Transaction successful!")
    #print(response)
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

