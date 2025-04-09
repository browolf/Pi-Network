/*
This script creates a new valid Pi account of passphrase and associated keys

Inputs:
(none)

Outputs: 
1. Passphrase (Mnemonic)
2. Private key
3. Secret key

*/


const Stellar = require('stellar-sdk');
const { derivePath } = require("@hawkingnetwork/ed25519-hd-key-rn");
const bip39 = require("bip39");
const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
});

async function createMnemonic() {
    return bip39.generateMnemonic(256); // 256 bits entropy for a 24-word mnemonic
}

async function getApplicationPrivateKey(mnemonic) {
    const seed = await bip39.mnemonicToSeed(mnemonic);
    const derivedSeed = derivePath("m/44'/314159'/0'", seed);

    return Stellar.Keypair.fromRawEd25519Seed(derivedSeed.key.slice(0, 32));
}

async function main() {
    const mnemonic = await createMnemonic();
    console.log('Generated 24-word mnemonic:', mnemonic);

    getApplicationPrivateKey(mnemonic).then((keypair) => {
        console.log('Public Key:', keypair.publicKey());
        console.log('Secret Key:', keypair.secret());
        readline.close();
    }).catch((error) => {
        console.error('Error:', error);
        readline.close();
    });
}

main();
