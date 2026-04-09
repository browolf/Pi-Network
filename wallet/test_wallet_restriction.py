"""
Pi Network Transaction Builder (CLI)

Description:
A simple command-line tool for creating, signing, and submitting Pi Network
(Stellar-based) transactions using the official stellar_sdk.

Features:
- Secure input for secret keys (hidden via getpass)
- Basic validation for Stellar addresses and amounts
- Interactive transaction summary and confirmation
- Builds, signs, and submits native PI payments
- Detailed error handling and debugging output

Configuration:
- Network: Pi Network (mainnet)
- Horizon Server: https://api.mainnet.minepi.com
- Base Fee: 1,000,000 stroops

Requirements:
- Python 3.x
- stellar-sdk

Output:
- Specifically checks for blocked destinations 
- These return the message : '{"error":"Bad request - Invalid Operation - Bad request - ' 'Permission denied (destination)"}',

Security Notes:
- Your secret key is never stored, only used in-memory for signing
- Always verify destination address and amount before confirming
- Use at your own risk
"""


from stellar_sdk import Keypair, Server, TransactionBuilder, Asset, exceptions
import getpass
from pprint import pprint


def get_input(prompt, required=True, secret=False):
    """Helper function to get user input with optional masking for secrets."""
    while True:
        if secret:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        if required and not value.strip():
            print("This field is required. Please enter a value.")
            continue
        return value.strip()


def validate_stellar_address(address):
    """Basic validation for Stellar address format."""
    if not address:
        return False
    return address.startswith("G") and len(address) == 56


def validate_amount(amount_str):
    """Validate that amount is a positive number."""
    try:
        amount = float(amount_str)
        return amount > 0
    except ValueError:
        return False


def main():
    # Hardcoded network configuration
    horizon_server = "https://api.mainnet.minepi.com"
    network_passphrase = "Pi Network"
    base_fee = 1000000

    print("=" * 60)
    print("Pi Network Transaction Builder")
    print("=" * 60)
    print(f"Network:  {network_passphrase}")
    print(f"Server:   {horizon_server}")
    print(f"Base Fee: {base_fee} stroops")
    print("=" * 60)
    print()

    # Get sender's secret key
    print("Paste sender's secret key (input will be hidden):")
    existing_secret_key = get_input("Secret Key: ", required=True, secret=True)

    # Validate secret key
    try:
        existing_keypair = Keypair.from_secret(existing_secret_key)
        print(f"✓ Sender Public Key: {existing_keypair.public_key}")
    except Exception as e:
        print(f"Error: Invalid secret key - {e}")
        return

    # Get destination address
    while True:
        destination_address = get_input("Destination Address: ", required=True)
        if validate_stellar_address(destination_address):
            break
        print("Error: Invalid Stellar address format. Address should start with 'G' and be 56 characters.")

    # Get amount
    while True:
        send_amount = get_input("Amount to send (in Pi): ", required=True)
        if validate_amount(send_amount):
            break
        print("Error: Please enter a valid positive number.")

    print()
    print("=" * 60)
    print("TRANSACTION SUMMARY")
    print("=" * 60)
    print(f"To:       {destination_address}")
    print(f"Amount:   {send_amount} PI")
    print(f"Fee:      {base_fee} stroops")
    print(f"Network:  {network_passphrase}")
    print("=" * 60)
    print()

    # Confirmation
    while True:
        confirm = get_input("Proceed with transaction? (yes/no): ").lower()
        if confirm in ["yes", "y"]:
            break
        elif confirm in ["no", "n"]:
            print("Transaction cancelled.")
            return
        else:
            print("Please enter 'yes' or 'no'.")

    print()
    print("Executing transaction...")

    # Connect and load account
    try:
        server = Server(horizon_server)
        existing_account = server.load_account(existing_keypair.public_key)
        print("✓ Account loaded")
    except exceptions.NotFoundError:
        print("✗ Error: Sender account not found.")
        return
    except exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        return
    except Exception as e:
        print(f"✗ Error loading account: {e}")
        return

    # Build transaction
    try:
        transaction = (
            TransactionBuilder(
                source_account=existing_account,
                network_passphrase=network_passphrase,
                base_fee=base_fee
            )
            .append_payment_op(
                destination=destination_address,
                amount=send_amount,
                asset=Asset.native()
            )
            .set_timeout(30)
            .build()
        )
        print("✓ Transaction built")
    except Exception as e:
        print(f"✗ Error building transaction: {e}")
        return

    # Sign
    try:
        transaction.sign(existing_keypair)
        print("✓ Transaction signed")
    except Exception as e:
        print(f"✗ Error signing: {e}")
        return

    # Submit
    print()
    print("Submitting to network...")

    try:
        response = server.submit_transaction(transaction)

        print()
        print("=" * 60)
        print("✓ TRANSACTION SUCCESSFUL")
        print("=" * 60)
        print(f"Hash:        {response.get('hash', 'N/A')}")
        print(f"Ledger:      {response.get('ledger', 'N/A')}")
        print("Envelope XDR:")
        print(response.get("envelope_xdr", "N/A"))
        print("=" * 60)





    except exceptions.BadRequestError as e:
        print("\n✗ TRANSACTION FAILED\n")
        pprint(vars(e))
        print("\nargs:")
        pprint(e.args)

    except exceptions.ConnectionError as e:
        print(f"\n✗ Connection error: {e}")

    except exceptions.TimeoutError as e:
        print(f"\n✗ Timeout: {e}")

    except exceptions.UnknownRequestError as e:
        print(f"\n✗ Unknown error: {e}")

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()
