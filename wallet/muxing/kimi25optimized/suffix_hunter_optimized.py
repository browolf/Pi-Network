#!/usr/bin/env python3
"""
Muxed Address Suffix Hunter - Config-Driven Edition
Usage: 
  python suffix_hunter_optimized.py          # Uses search_config.py or asks
  python suffix_hunter_optimized.py --workers 4 --priority idle
"""
import os
import re
import sys
import time
import queue
import signal
import struct
import base64
import random
import argparse
import multiprocessing as mp
from typing import Optional, Tuple

from stellar_sdk.strkey import StrKey

# -------------------- Config Loading --------------------

def load_config_file():
    """
    Try to load search_config.py for automatic parameters.
    Returns: (g_address, suffix, resume_file) or None if not found/invalid.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("search_config", "search_config.py")
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        
        # Validate required fields exist
        g = config.G_ADDRESS
        suffix = config.TARGET_SUFFIX
        resume = getattr(config, 'RESUME_FILE', None)
        
        print(f"[CONFIG] Loaded from search_config.py")
        print(f"[CONFIG] Address: {g[:12]}...{g[-4:]} | Suffix: '{suffix}'")
        return g, suffix, resume
        
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[WARN] Found search_config.py but couldn't load it: {e}")
        print(f"[WARN] Falling back to interactive mode...\n")
        return None

def save_config_file(g_address, suffix, resume_file):
    """Offer to save current settings to search_config.py"""
    try:
        with open("search_config.py", "w", encoding="utf-8") as f:
            f.write(f'''# Auto-generated search configuration
G_ADDRESS = "{g_address}"
TARGET_SUFFIX = "{suffix}"
RESUME_FILE = "{resume_file or 'hunt_progress.txt'}"
''')
        print(f"\n💾 Settings saved to search_config.py for next time.")
    except Exception as e:
        print(f"\n⚠️  Could not save config: {e}")

# -------------------- CRC & Encoder --------------------

try:
    from crc_table import CRC16_XMODEM_TABLE
    _CRC_SOURCE = "file"
except ImportError:
    def _gen_crc():
        table = []
        for i in range(256):
            crc = i << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
            table.append(crc)
        return table
    CRC16_XMODEM_TABLE = _gen_crc()
    _CRC_SOURCE = "runtime"

def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc = ((CRC16_XMODEM_TABLE[((crc >> 8) ^ byte) & 0xFF]) ^ (crc << 8)) & 0xFFFF
    return crc

def decode_g_address(g_addr: str) -> bytes:
    if not re.match(r'^G[A-Z2-7]{55}$', g_addr):
        raise ValueError("Invalid G-address format")
    return StrKey.decode_ed25519_public_key(g_addr)

def encode_muxed_bytes(pubkey_bytes: bytes, sub_id: int) -> bytes:
    payload = b'\x60' + pubkey_bytes + struct.pack('>Q', sub_id)
    payload += struct.pack('>H', crc16_xmodem(payload))
    return base64.b32encode(payload).rstrip(b'=')

# -------------------- Worker & Feeder --------------------

def worker_process(pubkey_bytes, target_bytes, chunk_q, found_q, n_attempts, stop_event):
    local_count = 0
    flush_every = 100_000
    
    while not stop_event.is_set():
        try:
            chunk = chunk_q.get(timeout=0.1)
        except queue.Empty:
            continue
        if chunk is None:
            break
        
        start, end = chunk
        for sub_id in range(start, end):
            if local_count >= flush_every:
                if stop_event.is_set(): break
                with n_attempts.get_lock():
                    n_attempts.value += local_count
                local_count = 0
            
            if encode_muxed_bytes(pubkey_bytes, sub_id).endswith(target_bytes):
                found_q.put(encode_muxed_bytes(pubkey_bytes, sub_id).decode('ascii'))
                stop_event.set()
                break
            local_count += 1
    
    if local_count:
        with n_attempts.get_lock():
            n_attempts.value += local_count

def feed_chunks(chunk_q, stop_event, max_subid, chunk_size, n_workers, resume_file, throttle):
    start_id = 0
    resuming = False
    
    if resume_file and os.path.exists(resume_file):
        try:
            with open(resume_file, 'r') as f:
                start_id = int(f.read().strip())
            print(f"[FEEDER] Resuming from: {start_id:,}")
            resuming = True
        except:
            pass
    
    if not resuming:
        start_id = random.randint(0, max(0, max_subid - chunk_size * 1000))
        print(f"[FEEDER] Random start: {start_id:,} (hex: {start_id:016x})")
    
    subid = start_id
    checkpoint_every = 5_000_000
    
    while subid < max_subid and not stop_event.is_set():
        end = min(max_subid, subid + chunk_size)
        try:
            chunk_q.put((subid, end), timeout=0.1)
        except queue.Full:
            continue
        subid = end
        if throttle > 0:
            time.sleep(throttle)
        if resume_file and subid % checkpoint_every == 0:
            with open(resume_file, 'w') as f:
                f.write(str(subid))
    
    for _ in range(n_workers):
        try:
            chunk_q.put(None, timeout=1)
        except queue.Full:
            pass

# -------------------- System Limits --------------------

def set_process_priority(priority_str):
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        priorities = {'idle': 64, 'low': 16384, 'normal': 32, 'high': 128}
        if priority_str.lower() in priorities:
            kernel32.SetPriorityClass(handle, priorities[priority_str.lower()])
            print(f"[SYSTEM] Priority set to: {priority_str.upper()}")
    except Exception as e:
        print(f"[WARN] Could not set priority: {e}")

def set_cpu_affinity(cores):
    if not cores:
        return
    try:
        if sys.platform == 'win32':
            import ctypes
            mask = sum(1 << c for c in cores)
            ctypes.windll.kernel32.SetProcessAffinityMask(ctypes.windll.kernel32.GetCurrentProcess(), mask)
            print(f"[SYSTEM] Affinity: cores {cores}")
        elif sys.platform == 'linux':
            os.sched_setaffinity(0, set(cores))
    except Exception as e:
        print(f"[WARN] Could not set affinity: {e}")

# -------------------- Main --------------------

def interactive_setup():
    """Ask user for inputs and offer to save them."""
    print("=" * 60)
    print("Muxed Address Hunter - Interactive Setup")
    print("=" * 60)
    print("(Tip: Run 'python create_search_config.py' to avoid this step)\n")
    
    while True:
        g = input("G-address: ").strip().upper()
        try:
            decode_g_address(g)  # validate
            break
        except Exception as e:
            print(f"❌ Invalid: {e}")
    
    while True:
        suffix = input("Target suffix: ").strip().upper()
        if len(suffix) >= 2 and re.match(r'^[A-Z2-7]+$', suffix):
            break
        print("❌ Use A-Z, 2-7 (min 2 chars)")
    
    resume = input("Resume file [hunt_progress.txt]: ").strip()
    if not resume:
        resume = "hunt_progress.txt"
    
    save = input("Save these settings to search_config.py? (y/n): ").strip().lower()
    if save == 'y':
        save_config_file(g, suffix, resume)
    
    return g, suffix, resume

def parse_args():
    parser = argparse.ArgumentParser(description='Muxed Address Suffix Hunter')
    parser.add_argument('-w', '--workers', type=int, default=max(1, (os.cpu_count() or 4) - 2))
    parser.add_argument('--priority', choices=['idle', 'low', 'normal', 'high'], default='normal')
    parser.add_argument('--affinity', type=str, default=None)
    parser.add_argument('--throttle', type=float, default=0, help='Seconds between chunks')
    return parser.parse_args()

def main():
    args = parse_args()
    mp.freeze_support()
    mp.set_start_method('spawn', force=True)
    
    # Apply system limits
    set_process_priority(args.priority)
    if args.affinity:
        set_cpu_affinity([int(x) for x in args.affinity.split(',')])
    
    # Load config or ask
    config = load_config_file()
    if config:
        g_address, target_suffix, resume_file = config
        # Validate the loaded address still works
        try:
            pubkey_bytes = decode_g_address(g_address)
        except Exception as e:
            print(f"❌ Config file has invalid address: {e}")
            print(f"❌ Delete search_config.py and run again.")
            return
    else:
        g_address, target_suffix, resume_file = interactive_setup()
        pubkey_bytes = decode_g_address(g_address)
    
    # Setup
    MAX_SUBID = 2**64
    CHUNK_SIZE = 500_000
    target_bytes = target_suffix.encode('ascii')
    n_workers = max(1, min(args.workers, os.cpu_count() or 4))
    
    print(f"\n[SETUP] Workers: {n_workers} | Throttle: {args.throttle}s | CRC: {_CRC_SOURCE}")
    
    # Shared state
    stop_event = mp.Event()
    n_attempts = mp.Value('Q', 0)
    chunk_q = mp.Queue(maxsize=n_workers * 2)
    found_q = mp.Queue(maxsize=1)
    
    signal.signal(signal.SIGINT, lambda s, f: stop_event.set())
    
    # Launch
    feeder = mp.Process(target=feed_chunks, 
                       args=(chunk_q, stop_event, MAX_SUBID, CHUNK_SIZE, n_workers, resume_file, args.throttle),
                       daemon=True)
    feeder.start()
    time.sleep(0.1)  # Let feeder print start position
    
    workers = []
    for i in range(n_workers):
        p = mp.Process(target=worker_process,
                      args=(pubkey_bytes, target_bytes, chunk_q, found_q, n_attempts, stop_event),
                      daemon=True)
        p.start()
        workers.append(p)
    
    print(f"\n🔍 Hunting for '{target_suffix}' with {n_workers} workers...")
    print(f"   Output will save to: {g_address}.suffix_{target_suffix}.txt\n")
    
    # Monitor
    start_time = time.time()
    last_stats = start_time
    found_address = None
    
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
            try:
                found_address = found_q.get_nowait()
                stop_event.set()
                break
            except queue.Empty:
                pass
            
            if time.time() - last_stats >= 10:
                total = n_attempts.value
                elapsed = time.time() - start_time
                print(f"[STATS] {total:,} checked | {total/elapsed:,.0f}/s | {elapsed:.1f}s")
                last_stats = time.time()
    except KeyboardInterrupt:
        stop_event.set()
    
    # Cleanup
    stop_event.set()
    feeder.join(timeout=2)
    for p in workers:
        p.join(timeout=1)
    
    # Results
    total = n_attempts.value
    elapsed = time.time() - start_time
    
    if not found_address:
        try:
            found_address = found_q.get_nowait()
        except:
            pass
    
    print("\n" + "=" * 60)
    if found_address:
        with open(f"{g_address}.suffix_{target_suffix}.txt", "w") as f:
            f.write(f"{found_address}  <- {target_suffix}\n")
        print(f"✅ FOUND: {found_address}")
        print(f"   Checked: {total:,} in {elapsed:.2f}s")
        if resume_file and os.path.exists(resume_file):
            os.remove(resume_file)
    else:
        print(f"⏹️  Stopped. Checked: {total:,}")
        if resume_file:
            print(f"   Resume: {resume_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
