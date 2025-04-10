'''
This standalone script searches for Pi Network wallet addresses with a specific suffix. 

Inputs:
1. suffix to search for

Outputs:
1. Enter the suffix to search for (e.g., 'XYZ'): 
2. [MAIN] Starting search for suffix: <suffix>
3. [MAIN] Spinning up <x> Threads
4. [STATS] Attempts/sec: <x> | Total: <x>
5. ✅ MATCH FOUND by T<x>!
6. KeyboardInterrupt

Notes:
1. Difficult ramps up exponentially. Expect at least 1 billion attempts for a 6 char suffix. You don't need to run the program in one go. There's basically a zero chance of retesting the same attempt. 
2. If you are running the client on windows, need to install visual studio community edition, "Desktop development with C++" before you can install the bip_utils module.  I can't remember if it manages itself on ubuntu. 
3. Due the way threads report attempts there's not a smooth continuous output. 
'''


import threading, os, time
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip32Slip10Ed25519
from stellar_sdk import Keypair

SUFFIX = input("Enter the suffix to search for (e.g., 'XYZ'): ").upper()
stop_event = threading.Event()
threads = []
attempts_lock = threading.Lock()
total_attempts = 0

def search_for_suffix(suffix, thread_id):
    global total_attempts
    while not stop_event.is_set():
        local_attempts = 0
        for _ in range(1000):
            if stop_event.is_set():
                return
            mnemonic = Bip39MnemonicGenerator().FromWordsNumber(24)
            seed = Bip39SeedGenerator(mnemonic).Generate()
            key = Bip32Slip10Ed25519.FromSeed(seed).DerivePath("m/44'/314159'/0'")
            pub = Keypair.from_raw_ed25519_seed(key.PrivateKey().Raw().ToBytes()).public_key
            local_attempts += 1
            if pub.endswith(suffix):
                stop_event.set()
                print(f"\n✅ MATCH FOUND by T{thread_id}!")
                print(f"Address: {pub}")
                print(f"Mnemonic: {mnemonic}")
                return
        with attempts_lock:
            total_attempts += local_attempts

def client_worker(thread_id):
    #print(f"[T{thread_id}] Started.")
    search_for_suffix(SUFFIX, thread_id)

def start_threads():
    global threads
    threads = [threading.Thread(target=client_worker, args=(i+1,), daemon=True) for i in range(os.cpu_count())]
    print(f"[MAIN] Spinning up {len(threads)} Threads")
    for t in threads:
        t.start()

def monitor_attempts(interval=5):
    global total_attempts
    start_time = time.time()
    while not stop_event.is_set():
        time.sleep(interval)
        with attempts_lock:
            current = total_attempts
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        print(f"[STATS] Attempts/sec: {rate:.2f} | Total: {current}")

def main():
    print(f"[MAIN] Starting search for suffix: {SUFFIX}")
    
    start_threads()
    monitor_thread = threading.Thread(target=monitor_attempts, daemon=True)
    monitor_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == '__main__':
    main()
