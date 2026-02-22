"""
# ============================================================
# Pi Network Transaction Builder (Stellar SDK)
# ============================================================
# ------------------------------------------------------------
# DESCRIPTION
# ------------------------------------------------------------
# Interactive command-line tool for sending native Pi payments
# on the Pi Network using the Stellar SDK.
#
# The script securely prompts for the sender’s secret key,
# validates input values, builds a payment transaction, signs
# it locally, and submits it to the Pi Network Horizon server.
#
# Designed for simple, direct transfers between accounts with
# clear confirmation and detailed error handling.
#
# ------------------------------------------------------------
# FEATURES
# ------------------------------------------------------------
# • Secure masked input for secret key
# • Stellar address format validation
# • Positive numeric amount validation
# • Transaction preview and confirmation step
# • Automatic account loading from Horizon
# • Native Pi payment operation builder
# • Local transaction signing
# • Network submission with structured error reporting
# • Clean CLI output and status indicators
#
# ------------------------------------------------------------
# NETWORK CONFIGURATION (HARDCODED)
# ------------------------------------------------------------
# Horizon Server:     https://api.mainnet.minepi.com
# Network Passphrase: Pi Network
# Base Fee:           1,000,000 stroops
#
# ------------------------------------------------------------
# REQUIREMENTS
# ------------------------------------------------------------
# pip install stellar-sdk
#
# ------------------------------------------------------------
# SECURITY NOTES
# ------------------------------------------------------------
# • Secret keys are entered locally and never stored.
# • Transactions are signed locally before submission.
# • Always verify destination address and amount before
#   confirming the transaction.
#
# ------------------------------------------------------------
# USAGE
# ------------------------------------------------------------
# python send_pi.py
#
# Follow the prompts:
#   1. Enter sender secret key (hidden input)
#   2. Enter destination address
#   3. Enter amount to send
#   4. Confirm transaction
#
# ------------------------------------------------------------
# DISCLAIMER
# ------------------------------------------------------------
# This script submits real transactions to the Pi Network.
# Use at your own risk. Always test with small amounts first.
#
# ------------------------------------------------------------
# PROJECT PURPOSE
# ------------------------------------------------------------
# Utility script for manual Pi transfers, testing workflows,
# and interacting directly with Pi’s Stellar-based settlement
# layer without a wallet UI.
# ============================================================
"""
from stellar_sdk import Keypair, Server, TransactionBuilder, Asset, exceptions
import getpass

def get_input(prompt, required=True, secret=False):
    """Helper function to get user input with optional masking for secrets"""
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
    """Basic validation for Stellar address format"""
    if not address:
        return False
    return address.startswith('G') and len(address) == 56

def validate_amount(amount_str):
    """Validate that amount is a positive number"""
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
    print(f"Network: {network_passphrase}")
    print(f"Server:  {horizon_server}")
    print(f"Base Fee: {base_fee} stroops")
    print("=" * 60)
    print()

    # Get sender's secret key (masked input)
    print("Enter sender's secret key (input will be hidden):")
    existing_secret_key = get_input("Secret Key: ", required=True, secret=True)
    
    # Validate secret key
    try:
        existing_keypair = Keypair.from_secret(existing_secret_key)
        sender_public = existing_keypair.public_key
        print(f"✓ Sender Public Key: {sender_public}")
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
    print(f"From:     {sender_public}")
    print(f"To:       {destination_address}")
    print(f"Amount:   {send_amount} PI")
    print(f"Fee:      {base_fee} stroops")
    print(f"Network:  {network_passphrase}")
    print("=" * 60)
    print()

    # Confirmation
    while True:
        confirm = get_input("Proceed with transaction? (yes/no): ").lower()
        if confirm in ['yes', 'y']:
            break
        elif confirm in ['no', 'n']:
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
        print("✓ TRANSACTION SUCCESSFUL!")
        print("=" * 60)
        print(f"Hash:   {response.get('hash', 'N/A')}")
        print(f"Ledger: {response.get('ledger', 'N/A')}")
        print()
    except exceptions.BadRequestError as e:
        print("✗ Transaction failed:")
        print(e.extras.get('result_codes', {}))
    except exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
    except exceptions.TimeoutError as e:
        print(f"✗ Timeout: {e}")
    except exceptions.UnknownRequestError as e:
        print(f"✗ Unknown error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

if __name__ == "__main__":
    main()
