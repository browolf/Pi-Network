'''
This script decrypts a passphrase to keys. 
Also can be used to verify that a passphrase is linked to the correct Pi Network public key

Inputs:
1. Mneumonic passphrase

Outputs:
2. Public and Secret key

Notes:
You need to install visual studio community edition, "Desktop development with C++" before you can install the 
bip_utils module. 

'''


from bip_utils import Bip39SeedGenerator, Bip39MnemonicValidator,  Bip39Languages, Bip32Slip10Ed25519
from stellar_sdk import Keypair



def derive_stellar_keypair(mnemonic):
    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(mnemonic, Bip39Languages.ENGLISH).Generate()


    # Derive path m/44'/314159'/0' directly (no need for Bip44Coins)
    bip32_ctx = Bip32Slip10Ed25519.FromSeed(seed_bytes)
    derived_key = bip32_ctx.DerivePath("m/44'/314159'/0'")

    # Get raw private key bytes and derive Stellar keypair
    raw_private_key = derived_key.PrivateKey().Raw().ToBytes()
    keypair = Keypair.from_raw_ed25519_seed(raw_private_key)
    return keypair

def main():
    #test
    #mnemonic = "detect tool foot absurd egg leave core hello tenant consider tip glow school column garbage exit lesson razor pattern impact ribbon tuna behind desert"

    mnemonic = input("Enter passphrase: ")

    validator = Bip39MnemonicValidator()
    if not validator.IsValid(mnemonic):
        raise ValueError("Invalid mnemonic.")

    try:
        keypair = derive_stellar_keypair(mnemonic)
        print("✅ Pi Network Keypair Derived:")
        print("Public Key :", keypair.public_key)
        print("Secret Key :", keypair.secret)
    except Exception as e:
        print("❌ Error deriving keypair:", e)

if __name__ == "__main__":
    main()
