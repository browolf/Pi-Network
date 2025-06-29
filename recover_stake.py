'''
the operation that created the claimable balance does not contain the actual balance_id.

To get the claimable balance ID, you must follow the _links.effects URL:

https://api.mainnet.minepi.com/operations/<transactionid}/effects

look for an effect like this 

{
  "type": "claimable_balance_created",
  "balance_id": "0000000080896050f2643dd0d8f068c4bd2a4098966d54db53c62fd8b79b733c860eeda9",
  ...
}

Input: your private key

Output: when it works you get a big json response. check the e

'''

from stellar_sdk import Server, Keypair, TransactionBuilder, exceptions
import requests


# Constants
BALANCE_OPERATION_ID = "92031335153065985"



# Pi Network settings
horizon_server = "https://api.mainnet.minepi.com"
network_passphrase = "Pi Network"
base_fee = 1000000

def get_real_claimable_balance_id(operation_id):
    effects_url = f"{horizon_server}/operations/{operation_id}/effects"
    response = requests.get(effects_url)
    response.raise_for_status()
    effects = response.json()["_embedded"]["records"]

    for effect in effects:
        if effect["type"] == "claimable_balance_created":
            return effect["balance_id"]
    raise Exception("No claimable balance created in this operation.")

def main():
    # Ask for the secret key securely
    secret_key = input("Enter your Stellar secret key: ").strip()
    
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

    # Get actual balance ID
    balance_id = get_real_claimable_balance_id(BALANCE_OPERATION_ID)
    print(f"Claiming balance ID: {balance_id}")

    # Build transaction
    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=network_passphrase,
            base_fee=base_fee
        )
        .append_claim_claimable_balance_op(balance_id)
        .set_timeout(60)
        .build()
    )

  
    tx.sign(keypair)
    
    # Submit the transaction
    try:
        response = server.submit_transaction(tx)
        print("✅ Submitted to the network!")
        print(response)
    except exceptions.BadRequestError as e:
        print("❌ Transaction failed:")
        print(f'result_codes: {e}')
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()
