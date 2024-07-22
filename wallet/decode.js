/*
You need to install these modules first using npm

npm install stellar-sdk @hawkingnetwork/ed25519-hd-key-rn bip39 readline

*/

const Stellar = require('stellar-sdk');
const { derivePath } = require("@hawkingnetwork/ed25519-hd-key-rn");
const bip39 = require("bip39");
const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
});

async function getApplicationPrivateKey(mnemonic) {
    const seed = await bip39.mnemonicToSeed(mnemonic);
    const derivedSeed = derivePath("m/44'/314159'/0'", seed);

    return Stellar.Keypair.fromRawEd25519Seed(derivedSeed.key.slice(0, 32));
}

readline.question('Please enter your mnemonic: ', (mnemonic) => {
    getApplicationPrivateKey(mnemonic).then((keypair) => {
        console.log('Public Key:', keypair.publicKey());
        console.log('Secret Key:', keypair.secret());
        readline.close();
    }).catch((error) => {
        console.error('Error:', error);
        readline.close();
    });
});
