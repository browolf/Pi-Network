'''
use this script to verify a secret key works. 
this works by changing the home_domain of the account

'''
from stellar_sdk import Keypair, Server, TransactionBuilder, Account, exceptions
import sys

def check_signature(secret: str, wallet: str ) -> bool:
    try:
        #secret > keypair
        keypair = Keypair.from_secret(secret)
        signer_public_key = keypair.public_key

        #connect to network
        server = Server(horizon_server)

        #load account
        account = server.accounts().account_id(wallet).call()
        print(f"Account {wallet[:4]} exists on the network")

        #check the signer
        signers= account['signers']      
        if any(signer['key'] == signer_public_key for signer in signers):
            print("Signer found:")
            for signer in signers:
                print(f"{signer['key'][:4]} - Weight: {signer['weight']}")
        else:
            print(f"Signer not found. Exiting")
            sys.exit()
    
        #create a transaction to change a trivial account variable
        new_home_domain = "lexwolfe.com"

        account_sequence = account['sequence']
        account_obj = Account(
            account=wallet,
            sequence=int(account_sequence)
        )
        
        transaction=(
            TransactionBuilder(
                source_account=account_obj,
                network_passphrase=network_passphrase,
                base_fee=base_fee
            )
            .append_set_options_op(home_domain=new_home_domain)
            .set_timeout(30)
            .build()
        )

        #sign the transaction
        transaction.sign(keypair)

        try:
            response = server.submit_transaction(transaction)
            return True
        except exceptions.BadRequestError as e:
            result_codes = e.extras.get('result_codes', None)
            print("Transaction failed with result codes:")
            print(result_codes)
            return False     

    except exceptions.NotFoundError:
        print(f"Account for {wallet[:4]} not found")
    except exceptions.Ed25519SecretSeedInvalidError:
        print(f"Invalid Secret key")    
    except exceptions.BadRequestError as e:
        # Assuming 'e' contains the response object or JSON data
        error_details = e.response.json() if hasattr(e, 'response') else {}
        invalid_field = error_details.get('extras', {}).get('invalid_field')
        if invalid_field == "account_id":
            print("Wallet address Problem")
        else:
            print(f"Some other error from BRE, Type: {type(e).__name__} \n Description:{e}")  
    except Exception as e:
        print(f"Some other error, Type: {type(e).__name__} \n Description:{e}")    


    

if __name__ == "__main__":

    wallet = input("Enter the public key of the wallet: ")
    secret_to_check=input("Enter the new secret key you want to check? ")

    choose_server = input("choose testnet 1)Stellar or 2)Pi? or 3)Pi Mainnet ")

    # Horizon server and network passphrase
    if (choose_server == "1"):
        horizon_server = "https://horizon-testnet.stellar.org"
        network_passphrase = "Test SDF Network ; September 2015"
        base_fee = 100
        starting_balance = "1"
    elif (choose_server == "2"):
        horizon_server = "https://api.testnet.minepi.com"
        network_passphrase = "Pi Testnet"
        base_fee = 1000000
        starting_balance = "10"
        print("Need more than 20 to do transaction")
    elif (choose_server =="3"):
        horizon_server = "https://api.mainnet.minepi.com"
        network_passphrase = "Pi Network"
        base_fee = 1000000
        starting_balance = "1"
    else:
        print("Did not recognise choice")
        sys.exit()     

    is_valid = check_signature(secret_to_check,wallet)
    if is_valid:
        print("A transaction signed with this key was successful")
       

