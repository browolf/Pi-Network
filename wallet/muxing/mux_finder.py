'''
Each wallet has approx 4 billion possible muxed addresses.  
This program searches the the entire address space for addresses ending in words using multithreads to speed up the search. 

Input:  Your Pi Wallet public address starting with G

Output: A file containing notable addresses

On a Xeon workstation this script took a week to search the address space. 

'''



import threading
import os
import time
from stellar_sdk import MuxedAccount
from wordfreq import top_n_list

# Load dictionary
english_words = set(w.upper() for w in top_n_list('en', 5000))

# === User input ===
G_ADDRESS = input("Enter your G-address: ").strip().upper()
OUTPUT_FILE = f"{G_ADDRESS}.words.txt"

if os.path.exists(OUTPUT_FILE):
    os.remove(OUTPUT_FILE)

# === Globals ===
stop_event = threading.Event()
threads = []
attempts_lock = threading.Lock()
output_lock = threading.Lock()
total_attempts = 0
match_count = 0
matches = []
current_subid = 0
subid_lock = threading.Lock()
MAX_SUBID = 2**32
last_saved_count = 0
found_words = set()

# === Check if suffix is a word ===
def is_valid_suffix(m_address: str) -> str | None:
    for length in range(4, 10):
        suffix = m_address[-length:].upper()
        if suffix in english_words:
            return suffix
    return None

# === Thread worker ===
def search_for_word_suffix(thread_id):
    global total_attempts, current_subid, match_count, last_saved_count

    while not stop_event.is_set():
        with subid_lock:
            if current_subid >= MAX_SUBID:
                stop_event.set()
                return
            sub_id = current_subid
            current_subid += 1

        m_address = MuxedAccount(G_ADDRESS, sub_id).account_muxed
        match = is_valid_suffix(m_address)

        if match:
            with output_lock:
                if match not in found_words:
                    found_words.add(match)
                    match_count += 1
                    line = f"{m_address}  <- ends in word: {match}\n"
                    matches.append(line)
                    if match_count % 100 == 0:
                        with open(OUTPUT_FILE, 'a') as f:
                            f.writelines(matches)
                        matches.clear()

        with attempts_lock:
            total_attempts += 1

# === Start Threads ===
def start_threads():
    cpu_threads = os.cpu_count()
    print(f"[MAIN] Spinning up {cpu_threads} threads...")
    for i in range(cpu_threads):
        t = threading.Thread(target=search_for_word_suffix, args=(i+1,), daemon=True)
        threads.append(t)
        t.start()

# === Monitor stats ===
def monitor_attempts(interval=5):
    global total_attempts, match_count
    start_time = time.time()
    while not stop_event.is_set():
        time.sleep(interval)
        with attempts_lock:
            current = total_attempts
        with output_lock:
            found = match_count
        elapsed = time.time() - start_time
        rate = current / elapsed if elapsed > 0 else 0
        ratio = (found / current * 100) if current > 0 else 0
        print(f"[STATS] Checked: {current:,} | Found: {found} | Speed: {rate:,.2f} per second | F/C: {ratio:.4f}%")


# === Main ===
def main():
    print(f"[MAIN] Starting muxed address word search for: {G_ADDRESS}")
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    start_threads()
    threading.Thread(target=monitor_attempts, daemon=True).start()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted. Stopping...")
        stop_event.set()

    for t in threads:
        t.join()

    if matches:
        with open(OUTPUT_FILE, 'a') as f:
            f.writelines(matches)

    print(f"\n✅ Done. Output saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
