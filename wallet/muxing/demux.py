'''
This script will demux an Muxed Pi payment address and recover the original wallet and string if the Mux id was a string

Inputs:
1. Muxed Pi address starting with 'M'

Output 
1. Base address: <Original Pi wallet address starting with 'G'>
   Muxed ID (int): <muxed integer>
   Recovered String: <original string>
2. Recovered String:  [not valid UTF-8 or empty]

Notes:
1. This script can decode strings from mux.py, other ways to encode strings exist

'''

#test address: MDFNWH6ZFJVHJDLBMNOUT35X4EEKQVJAO3ZDL4NL7VQJLC4PJOQFWYTVOJXHA2IAABRQ4

from stellar_sdk import MuxedAccount

def id_to_string(id_value):
    try:
        b = id_value.to_bytes(8, byteorder='big')
        return b.rstrip(b'\0').decode('utf-8')
    except Exception:
        return None

def decode_muxed_address(muxed_address):
    try:
        muxed = MuxedAccount.from_account(muxed_address)
        base_address = muxed.account_id
        muxed_id = muxed.account_muxed_id
        recovered_str = id_to_string(muxed_id) if muxed_id is not None else None

        print("\n🔍 Decoded Info:")
        print(f"Base Address:      {base_address}")
        print(f"Muxed ID (int):    {muxed_id}")
        if recovered_str:
            print(f"Recovered String:  \"{recovered_str}\"")
        else:
            print("Recovered String:  [not valid UTF-8 or empty]")

    except Exception as e:
        print("❌ Invalid muxed address:", e)

if __name__ == "__main__":
    muxed_address = input("Please enter the muxed Pi address (starting with 'M'): ").strip()
    decode_muxed_address(muxed_address)





