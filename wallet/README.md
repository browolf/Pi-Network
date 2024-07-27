# Decode.js 

This script using NodeJS will decrypt a Pi Network Passphrase to keys

You need to install these modules first:> 
npm install stellar-sdk @hawkingnetwork/ed25519-hd-key-rn bip39 readline

# Create.js

This script creates a Pi Network Passphrase with keys. Wallet needs to be registered on the network using the new wallet script. 

# new_wallet.py

This script using Python and stellar-sdk module can create a new wallet with keys using the secret key you got from decode

You need a minium amount of coins to perform this operation and you will get an error if you don't have enough in the base wallet. 

You can either get a random wallet or use the wallet from create.js - recommend this method as you get the passphrase as well. 

# Verify_secret.py

Use this script to verify a secret key works. 

# Notes

I don't have a mainnet wallet to ensure it works there. 
