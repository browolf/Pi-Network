'''
Inputs:
    Secret key starting with 'S'
    fictious amount of Pi 

Output: 
    A successful transaction outputs the transaction json. 
'''


from stellar_sdk import Keypair, Server, TransactionBuilder, Asset, exceptions

# --- Configuration ---
HORIZON_SERVER = "https://api.mainnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Network"
BASE_FEE = 1000000  # 0.1 Pi


def main():
    # Ask user for secret key and amount
    secret_key = input("Enter your secret key (S...): ").strip()
    amount = input("Enter the amount of Pi to self-pay: ").strip()

    # Build keypair and derive public key
    try:
        keypair = Keypair.from_secret(secret_key)
        public_key = keypair.public_key
        print(f"Using account: {public_key}")
    except Exception as e:
        print("Invalid secret key:", e)
        return

    # Connect to network
    server = Server(HORIZON_SERVER)

    # Load account details
    try:
        account = server.load_account(public_key)
    except exceptions.NotFoundError:
        print("Account not found on the network.")
        return

    # Build transaction: self-payment
    try:
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=NETWORK_PASSPHRASE,
                base_fee=BASE_FEE
            )
            .append_payment_op(
                destination=public_key,  # Self-payment
                amount=amount,
                asset=Asset.native()
            )
            .set_timeout(30)
            .build()
        )
    except Exception as e:
        print("Error building transaction:", e)
        return

    # Sign and submit
    try:
        transaction.sign(keypair)
        response = server.submit_transaction(transaction)
        print("✅ Transaction successful!")
        print(response)
    except exceptions.BadRequestError as e:
        print("❌ Transaction failed with result codes:")
        print(e.extras.get("result_codes", {}))
    except exceptions.ConnectionError as e:
        print("Connection error:", e)
    except exceptions.TimeoutError as e:
        print("Timeout error:", e)
    except exceptions.UnknownRequestError as e:
        print("Unknown request error:", e)


if __name__ == "__main__":
    main()
