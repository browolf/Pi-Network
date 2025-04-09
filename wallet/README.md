# Decode.js 

This script using NodeJS will decrypt a Pi Network Passphrase to keys

You need to install these modules first:> 
npm install stellar-sdk @hawkingnetwork/ed25519-hd-key-rn bip39 readline

# Create.js

This script creates a Pi Network Passphrase with keys. Wallet needs to be registered on the network using the new wallet script. 

(if you didn't already need to install the modules as above)

# new_wallet.py

You need to decode your own wallet passphrase in order to use the keys to create another wallet.  

You need more than 40 coins to perform this operation and you will get an error if you don't have enough in the base wallet. 

You can either get a random wallet or use the wallet from create.js - recommend this method as you get the passphrase as well. 

# Verify_secret.py

Use this script to verify a secret key works. 

# TEST_create_pi_mainnet_wallet.py

Would create a mainnet wallet if the operation wasn't blocked through the api.


