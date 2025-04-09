'''
This script picks search suffix from search, generates passphraases, searches for suffix in public address. 

Inputs:
1. Server IP

Outputs:
1. [MAIN] Checking server at <ip>:65432...
2. [MAIN] Server not available. Retrying in 10s...
3. [MAIN] Server available. Restarting threads.
4. [Tx] Started.
5. [Tx] Searching for suffix: <suffix>
6. [Tx] Server down.
7. [Tx] <number> attempts sent
8. [Tx] Match found!
9. Pub: <public address>
   Mnemonic: <passphrase>
10.[T10] Match found but server unavailable. 


Notes:
1. If the search is too short it may find additional matches before the threads can shut down. 
the server end exits when it receives a result
2. If you are running the client on windows, need to install visual studio community edition, "Desktop development with C++" before you can install the 
bip_utils module.  I can't remember if it manages itself on ubuntu or not

'''


import socket, time, threading, os, sys
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip32Slip10Ed25519
from stellar_sdk import Keypair

SERVER = input("Server IP: ")
PORT, RETRY_DELAY = 65432, 10
stop_event = threading.Event()
threads = []

def check_server():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((SERVER, PORT))
        return s
    except:
        return None

def search_for_suffix(suffix, thread_id):
    attempts = 0
    while not stop_event.is_set():
        for _ in range(1000):
            if stop_event.is_set():
                return "stop", None, None
            attempts += 1
            mnemonic = Bip39MnemonicGenerator().FromWordsNumber(24)
            seed = Bip39SeedGenerator(mnemonic).Generate()
            key = Bip32Slip10Ed25519.FromSeed(seed).DerivePath("m/44'/314159'/0'")
            pub = Keypair.from_raw_ed25519_seed(key.PrivateKey().Raw().ToBytes()).public_key
            if pub.endswith(suffix):
                return "found", mnemonic, pub

        s = check_server()
        if not s:
            print(f"[T{thread_id}] Server down. ")
            stop_event.set()
            return "server_down", None, None
        try:
            s.sendall(f"[T{thread_id}] {attempts} attempts.".encode())
            print (f"[T{thread_id}] {attempts} attempts sent")
        except:
            pass
        s.close()

def client_worker(thread_id):
    print(f"[T{thread_id}] Started.")
    while not stop_event.is_set():
        s = check_server()
        if not s:
            print(f"[T{thread_id}] Server down.")
            stop_event.set()
            break
        try:
            suffix = s.recv(1024).decode().strip().upper()
            s.close()

            # Proceed with searching once the suffix is available
            if suffix:
                print(f"[T{thread_id}] Searching for suffix: {suffix}")
                result, mnemonic, pub = search_for_suffix(suffix, thread_id)

                if result == "found":
                    print(f"[T{thread_id}] Match found!\nPub: {pub}\nMnemonic: {mnemonic}")
                    s = check_server()
                    if s:
                        msg = f"✅ MATCH FOUND by T{thread_id}!\nAddress: {pub}\nMnemonic: {mnemonic}"
                        s.sendall(msg.encode())
                        s.close()
                        print(f"[T{thread_id}] Reported to server.")
                    else:
                        print(f"[T{thread_id}] Match found but server unavailable.")
                        stop_event.set()
                elif result == "server_down":
                    stop_event.set()
            else:
                print(f"[T{thread_id}] No suffix received, retrying.")
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[T{thread_id}] Error: {e}")
            stop_event.set()
        time.sleep(RETRY_DELAY)

def start_threads():
    global threads
    threads = [threading.Thread(target=client_worker, args=(i+1,), daemon=True) for i in range(os.cpu_count())]
    for t in threads:
        t.start()

def stop_threads():
    stop_event.set()
    for t in threads:
        t.join()

def main():
    global threads
    while True:
        print(f"[MAIN] Checking server at {SERVER}:{PORT}...")
        
        # Wait for the server to be available
        while not check_server():
            print(f"[MAIN] Server not available. Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        
        print("[MAIN] Server available. Restarting threads.")
        
        # Stop old threads if they are running
        if threads:
            stop_threads()
        
        # Reset the stop event and start new threads
        stop_event.clear()
        start_threads()

        # Wait for threads to finish
        for t in threads:
            t.join()

if __name__ == '__main__':
    main()
