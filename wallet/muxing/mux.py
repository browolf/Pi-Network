'''
This script creates a Muxed payment address. A Muxed address is the combination of a pi wallet and an alphanumeric id upto 8 bytes worth. 8 alphanumeric characters or less if using special chars. 

Inputs: 
1. Your Pi wallet address starting with 'G'
2. Your choice of  id

Outputs 
1. Base address: <your pi wallet>
   64bit integer created from your id
   Muxed address beginning with 'M'
2. ❌ ID must be alphanumeric.
3. ❌ ID must be 8 bytes or fewer when UTF-8 encoded.
'''

import base64
from stellar_sdk import MuxedAccount, StrKey

def base32_to_int(s):
    padding = '=' * ((8 - len(s) % 8) % 8)
    decoded = base64.b32decode(s.upper() + padding, casefold=True)
    return int.from_bytes(decoded, 'big')

def string_to_64bit_id(s):
    b = s.encode("utf-8")
    if len(b) > 8:
        print("⚠️  Input string longer than 8 bytes; truncating.")
    return int.from_bytes(b[:8].ljust(8, b'\0'), "big")

# Prompt for base address
base_address = input("Input your Pi wallet address: ")

if not StrKey.is_valid_ed25519_public_key(base_address):
    print("Invalid Pi address.")
    exit()

# Prompt for user-provided ID
while True:
    own_choice = input("Enter your own alphanumeric ID (max 8 characters): ")
    if not own_choice.isalnum():
        print("❌ ID must be alphanumeric.")
        continue
    if len(own_choice.encode("utf-8")) > 8:
        print("❌ ID must be 8 bytes or fewer when UTF-8 encoded.")
        continue
    break
chosen_id = string_to_64bit_id(own_choice)

# Create muxed address
try:
    muxed_account = MuxedAccount(base_address, chosen_id)
    muxed_address = muxed_account.account_muxed

    print(f"Base address:   {base_address}")
    print(f"Mux ID:         {chosen_id}")
    print(f"Muxed address:  {muxed_address}")

except Exception as e:
    print("Error:", e)
