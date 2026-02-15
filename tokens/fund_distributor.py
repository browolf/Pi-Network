"""
================================================================================
TOKEN ISSUER TO DISTRIBUTOR TRANSFER - INTERACTIVE
================================================================================

REQUIRED ITEMS CHECKLIST:
------------------------

[ ] 1. TOKEN ISSUER SECRET KEY (S...)
    - The account that created/issued the token
    - Must have sufficient token balance to send
    - Must have Test-π for transaction fees (~0.00001)

[ ] 2. DISTRIBUTOR PUBLIC KEY (G...)
    - The account that will receive the tokens
    - Must have established trustline to the asset
    - Can be the same as used in liquidity pool seeding

[ ] 3. ASSET CODE (e.g., "PI", "MYTOKEN", "ABC")
    - The code of the token being transferred
    - Must match exactly as issued

[ ] 4. TRANSFER AMOUNT
    - How many tokens to send
    - Must not exceed issuer's available balance

================================================================================

This script will:
1. Request issuer secret key (hidden input)
2. Request distributor public key
3. Request asset code and amount
4. Verify both accounts exist and have trustlines
5. Submit payment transaction from issuer to distributor
6. Confirm the transfer

================================================================================
"""

import sys
import getpass
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from stellar_sdk import (
    Keypair, Server, TransactionBuilder, Asset, 
    exceptions, Network
)

# Pi Testnet configuration
HORIZON_URL = "https://api.testnet.minepi.com"
NETWORK_PASSPHRASE = "Pi Testnet"
BASE_FEE = 1_000_000
TIMEOUT = 60

server = Server(HORIZON_URL)


def print_header():
    print("=" * 70)
    print("TOKEN ISSUER → DISTRIBUTOR TRANSFER")
    print("=" * 70)
    print("Send tokens from issuer to distributor account")
    print("=" * 70)


def validate_public_key(key: str) -> bool:
    """Validate Stellar public key format."""
    if not key or len(key) != 56:
        return False
    if not key.startswith('G'):
        return False
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
    return all(c in valid_chars for c in key[1:])


def validate_secret_key(key: str) -> bool:
    """Validate Stellar secret key format."""
    if not key or len(key) != 56:
        return False
    if not key.startswith('S'):
        return False
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ234567')
    return all(c in valid_chars for c in key[1:])


def get_issuer_credentials() -> Tuple[str, str]:
    """Get and validate issuer secret key, return secret and derived public."""
    print("\n" + "-" * 70)
    print("STEP 1: TOKEN ISSUER AUTHENTICATION")
    print("-" * 70)
    print("Enter the issuer's SECRET KEY (S...)")
    print("This account must hold the tokens being sent")
    print("-" * 70)
    
    while True:
        secret = getpass.getpass("\nEnter issuer secret key (S...): ").strip()
        
        if not secret:
            print("  ✗ Secret key is required.")
            continue
        
        if not validate_secret_key(secret):
            print("  ✗ Invalid format. Must be 56 characters starting with 'S'.")
            continue
        
        try:
            kp = Keypair.from_secret(secret)
            public = kp.public_key
            print(f"  ✓ Valid key pair")
            print(f"  ✓ Issuer public key: {public[:20]}...{public[-20:]}")
            return secret, public
        except Exception as e:
            print(f"  ✗ Invalid key: {e}")


def get_distributor_address() -> str:
    """Get and validate distributor public key."""
    print("\n" + "-" * 70)
    print("STEP 2: DISTRIBUTOR RECIPIENT")
    print("-" * 70)
    print("Enter the distributor's PUBLIC KEY (G...)")
    print("This account will receive the tokens")
    print("-" * 70)
    
    while True:
        public = input("\nEnter distributor public key (G...): ").strip().upper()
        
        if not public:
            print("  ✗ Public key is required.")
            continue
        
        if not validate_public_key(public):
            print("  ✗ Invalid format. Must be 56 characters starting with 'G'.")
            continue
        
        try:
            Keypair.from_public_key(public)
            print(f"  ✓ Valid public key: {public[:20]}...{public[-20:]}")
            return public
        except Exception as e:
            print(f"  ✗ Invalid key: {e}")


def get_asset_details() -> Tuple[str, Decimal]:
    """Get asset code and transfer amount."""
    print("\n" + "-" * 70)
    print("STEP 3: TRANSFER DETAILS")
    print("-" * 70)
    
    # Asset code
    while True:
        code = input("\nEnter Asset Code (e.g., PI, MYTOKEN): ").strip().upper()
        
        if not code:
            print("  ✗ Asset code is required.")
            continue
        
        if not (1 <= len(code) <= 12 and code.isalnum()):
            print("  ✗ Must be 1-12 alphanumeric characters.")
            continue
        
        print(f"  ✓ Asset: {code}")
        break
    
    # Amount
    while True:
        amount_str = input(f"Enter amount of {code} to send: ").strip()
        
        if not amount_str:
            print("  ✗ Amount is required.")
            continue
        
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                print("  ✗ Amount must be greater than zero.")
                continue
            
            print(f"  ✓ Amount: {amount} {code}")
            break
        except InvalidOperation:
            print("  ✗ Invalid number format.")
    
    return code, amount


def verify_accounts(issuer_pub: str, dist_pub: str, asset_code: str, asset_issuer: str) -> Tuple[Optional[dict], Optional[dict]]:
    """Verify both accounts exist and check balances/trustlines."""
    print("\n" + "-" * 70)
    print("STEP 4: VERIFYING ACCOUNTS")
    print("-" * 70)
    
    # Check issuer
    print(f"\nChecking issuer: {issuer_pub[:20]}...{issuer_pub[-20:]}")
    try:
        issuer_acct = server.accounts().account_id(issuer_pub).call()
        print("  ✓ Issuer account exists")
        
        # Find asset balance
        issuer_balance = None
        for bal in issuer_acct['balances']:
            if bal.get('asset_code') == asset_code and bal.get('asset_issuer') == asset_issuer:
                issuer_balance = Decimal(bal['balance'])
                print(f"  ✓ {asset_code} balance: {issuer_balance}")
                break
        
        if issuer_balance is None:
            print(f"  ✗ Issuer does not hold {asset_code}!")
            return None, None
        
        # Check native balance for fees
        native_balance = None
        for bal in issuer_acct['balances']:
            if bal.get('asset_type') == 'native':
                native_balance = Decimal(bal['balance'])
                break
        
        if native_balance < Decimal('0.01'):
            print(f"  ⚠ Low Test-π balance: {native_balance} (need ~0.01 for fees)")
        else:
            print(f"  ✓ Test-π balance: {native_balance}")
            
    except exceptions.NotFoundError:
        print(f"  ✗ Issuer account not found!")
        return None, None
    except Exception as e:
        print(f"  ✗ Error checking issuer: {e}")
        return None, None
    
    # Check distributor
    print(f"\nChecking distributor: {dist_pub[:20]}...{dist_pub[-20:]}")
    try:
        dist_acct = server.accounts().account_id(dist_pub).call()
        print("  ✓ Distributor account exists")
        
        # Check trustline
        has_trustline = False
        for bal in dist_acct['balances']:
            if bal.get('asset_code') == asset_code and bal.get('asset_issuer') == asset_issuer:
                has_trustline = True
                current = Decimal(bal['balance'])
                limit = Decimal(bal['limit'])
                print(f"  ✓ Trustline established")
                print(f"  ℹ Current balance: {current}")
                print(f"  ℹ Trustline limit: {limit}")
                
                # Check if limit allows receiving more
                available = limit - current
                print(f"  ℹ Available capacity: {available}")
                break
        
        if not has_trustline:
            print(f"  ✗ Distributor missing trustline for {asset_code}!")
            print(f"  → Distributor must first: ChangeTrust {asset_code}:{issuer_pub}")
            return None, None
            
    except exceptions.NotFoundError:
        print(f"  ✗ Distributor account not found!")
        print(f"  → Fund distributor first with Test-π faucet")
        return None, None
    except Exception as e:
        print(f"  ✗ Error checking distributor: {e}")
        return None, None
    
    return issuer_acct, dist_acct


def submit_payment(issuer_secret: str, issuer_pub: str, dist_pub: str, 
                   asset_code: str, amount: Decimal) -> Optional[str]:
    """Submit the payment transaction from issuer to distributor."""
    print("\n" + "-" * 70)
    print("STEP 5: SUBMITTING PAYMENT")
    print("-" * 70)
    
    # Create asset object
    asset = Asset(asset_code, issuer_pub)
    
    # Load issuer account
    try:
        source = server.load_account(issuer_pub)
    except Exception as e:
        print(f"  ✗ Failed to load issuer account: {e}")
        return None
    
    # Build transaction
    print(f"Building transaction...")
    print(f"  From: {issuer_pub[:20]}...")
    print(f"  To: {dist_pub[:20]}...")
    print(f"  Amount: {amount} {asset_code}")
    
    try:
        tx = (
            TransactionBuilder(
                source_account=source,
                network_passphrase=NETWORK_PASSPHRASE,
                base_fee=BASE_FEE,
            )
            .append_payment_op(
                destination=dist_pub,
                amount=str(amount),
                asset=asset,
            )
            .set_timeout(TIMEOUT)
            .build()
        )
        
        # Sign
        kp = Keypair.from_secret(issuer_secret)
        tx.sign(kp)
        print("  ✓ Transaction signed")
        
        # Submit
        print("  Submitting to network...")
        result = server.submit_transaction(tx)
        tx_hash = result['hash']
        print(f"  ✓ Success! Transaction hash: {tx_hash[:20]}...{tx_hash[-20:]}")
        return tx_hash
        
    except exceptions.BadRequestError as e:
        print(f"  ✗ Transaction failed: {e}")
        if hasattr(e, 'extras') and e.extras:
            print(f"  Result codes: {e.extras.get('result_codes', {})}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def confirm_transfer(asset_code: str, dist_pub: str, asset_issuer: str, expected_amount: Decimal):
    """Verify the transfer by checking distributor's new balance."""
    print("\n" + "-" * 70)
    print("STEP 6: CONFIRMING TRANSFER")
    print("-" * 70)
    
    try:
        acct = server.accounts().account_id(dist_pub).call()
        
        for bal in acct['balances']:
            if bal.get('asset_code') == asset_code and bal.get('asset_issuer') == asset_issuer:
                new_balance = Decimal(bal['balance'])
                print(f"  ✓ Distributor now holds: {new_balance} {asset_code}")
                return True
        
        print("  ✗ Could not verify balance")
        return False
        
    except Exception as e:
        print(f"  ✗ Error confirming: {e}")
        return False


def display_summary(issuer_pub: str, dist_pub: str, asset_code: str, 
                    amount: Decimal, tx_hash: Optional[str], success: bool):
    """Display final summary."""
    print("\n" + "=" * 70)
    print("TRANSFER SUMMARY")
    print("=" * 70)
    print(f"Issuer:      {issuer_pub}")
    print(f"Distributor: {dist_pub}")
    print(f"Asset:       {asset_code}")
    print(f"Amount:      {amount}")
    print("-" * 70)
    
    if success and tx_hash:
        print("Status:      ✓ COMPLETED")
        print(f"Transaction: {tx_hash}")
        print(f"Explorer:    https://testnet.minepi.com/transactions/{tx_hash}")
    elif tx_hash:
        print("Status:      ⏳ SUBMITTED (confirmation pending)")
        print(f"Transaction: {tx_hash}")
    else:
        print("Status:      ✗ FAILED")
    
    print("=" * 70)


def main():
    print_header()
    
    # Collect inputs
    issuer_secret, issuer_pub = get_issuer_credentials()
    dist_pub = get_distributor_address()
    asset_code, amount = get_asset_details()
    
    # Verify accounts
    issuer_acct, dist_acct = verify_accounts(issuer_pub, dist_pub, asset_code, issuer_pub)
    
    if not issuer_acct or not dist_acct:
        print("\n" + "=" * 70)
        print("Cannot proceed due to account issues.")
        print("=" * 70)
        return
    
    # Check issuer has enough
    issuer_balance = None
    for bal in issuer_acct['balances']:
        if bal.get('asset_code') == asset_code and bal.get('asset_issuer') == issuer_pub:
            issuer_balance = Decimal(bal['balance'])
            break
    
    if issuer_balance < amount:
        print(f"\n✗ Insufficient balance!")
        print(f"  Available: {issuer_balance} {asset_code}")
        print(f"  Requested: {amount} {asset_code}")
        return
    
    # Final confirmation
    print("\n" + "-" * 70)
    print("CONFIRM TRANSFER")
    print("-" * 70)
    print(f"Send {amount} {asset_code}")
    print(f"From: {issuer_pub[:20]}...")
    print(f"To:   {dist_pub[:20]}...")
    
    confirm = input("\nConfirm transfer? (yes/no): ").strip().lower()
    if confirm not in ('yes', 'y'):
        print("Aborted.")
        return
    
    # Submit
    tx_hash = submit_payment(issuer_secret, issuer_pub, dist_pub, asset_code, amount)
    
    # Confirm
    success = False
    if tx_hash:
        success = confirm_transfer(asset_code, dist_pub, issuer_pub, amount)
    
    # Summary
    display_summary(issuer_pub, dist_pub, asset_code, amount, tx_hash, success)
    
    if success:
        print(f"\n✓ Transfer complete!")
        print(f"  Distributor now has more {asset_code} for liquidity pooling.")
    else:
        print(f"\n⚠ Transfer status unclear. Check explorer for details.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
