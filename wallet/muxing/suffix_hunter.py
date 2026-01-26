"""
mux_suffixhunt_mp.py  (Windows / multiprocessing)

How this version is improved vs the threaded script:
- Uses multiprocessing (real parallelism on Windows): avoids the GIL bottleneck that makes CPU-bound threading slow.
- Chunked sub-ID allocation: each worker processes a whole range of IDs at once (far fewer locks / shared-state overhead).
- No per-attempt global locks: attempts are counted locally in each process and reported back in batches.
- Single writer/monitor in the main process: workers never write to disk (avoids file corruption/locking).
- Early stop when a match is found: once the target suffix is found, all workers are signaled to stop quickly.
- Steady stats reporting: prints speed/progress every few seconds.

Notes:
- MAX_SUBID is set to 2**32 by default. Muxed IDs are actually uint64 (2**64), but scanning the full space is infeasible.
- On Windows you MUST keep the `if __name__ == "__main__":` guard for multiprocessing.
"""

import os
import time
import queue
import multiprocessing as mp
from typing import Optional, Tuple

from stellar_sdk import MuxedAccount


# -------------------- Config --------------------

MAX_SUBID = 2**32           # change if you want a different search range
CHUNK_SIZE = 200_000        # tune for throughput
REPORT_EVERY = 50_000      # per-worker attempt reporting
STATS_INTERVAL_SEC = 5      # stats print interval


# -------------------- Worker --------------------

def worker_process(
    g_address: str,
    target_suffix: str,
    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]",
    found_q: "mp.Queue[str]",
    stats_q: "mp.Queue[int]",
    stop_event: "mp.Event",
) -> None:
    """
    Receives (start, end) subid ranges from chunk_q.
    Generates muxed addresses and checks whether they end in target_suffix.
    On first match, pushes the muxed address to found_q and sets stop_event.
    """
    local_attempts = 0
    suf = target_suffix.upper()

    try:
        while not stop_event.is_set():
            try:
                chunk = chunk_q.get(timeout=0.5)
            except queue.Empty:
                continue

            if chunk is None:
                break

            start, end = chunk
            for sub_id in range(start, end):
                if stop_event.is_set():
                    break

                m_address = MuxedAccount(g_address, sub_id).account_muxed
                if m_address.upper().endswith(suf):
                    # report and stop everything
                    found_q.put(m_address)
                    stop_event.set()
                    break

                local_attempts += 1
                if local_attempts >= REPORT_EVERY:
                    stats_q.put(local_attempts)
                    local_attempts = 0

    finally:
        if local_attempts:
            stats_q.put(local_attempts)


# -------------------- Chunk feeder --------------------

def feed_chunks(
    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]",
    stop_event: "mp.Event",
    max_subid: int,
    chunk_size: int,
    n_workers: int,
) -> None:
    subid = 0
    while subid < max_subid and not stop_event.is_set():
        end = min(max_subid, subid + chunk_size)
        chunk_q.put((subid, end))
        subid = end

    # Tell workers to exit
    for _ in range(n_workers):
        chunk_q.put(None)


# -------------------- Main monitor / writer --------------------

def monitor_and_write(
    output_file: str,
    found_q: "mp.Queue[str]",
    stats_q: "mp.Queue[int]",
    stop_event: "mp.Event",
    target_suffix: str,
) -> None:
    total_attempts = 0
    start_time = time.time()
    last_stats = start_time

    # fresh output
    if os.path.exists(output_file):
        os.remove(output_file)

    found_address: Optional[str] = None

    while not stop_event.is_set():
        now = time.time()

        # drain stats
        while True:
            try:
                inc = stats_q.get_nowait()
            except queue.Empty:
                break
            total_attempts += inc

        # check found
        try:
            found_address = found_q.get_nowait()
            stop_event.set()
        except queue.Empty:
            pass

        # stats print
        if now - last_stats >= STATS_INTERVAL_SEC:
            elapsed = now - start_time
            rate = (total_attempts / elapsed) if elapsed > 0 else 0.0
            print(
                f"[STATS] Checked: {total_attempts:,} | Speed: {rate:,.2f}/s | Target suffix: {target_suffix}"
            )
            last_stats = now

        time.sleep(0.02)

    # final drain in case something arrived just as we stopped
    if found_address is None:
        try:
            found_address = found_q.get_nowait()
        except queue.Empty:
            pass

    if found_address:
        line = f"{found_address}  <- ends with: {target_suffix}\n"
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(line)
        print(f"\n✅ FOUND: {found_address}")
    else:
        print(f"\n❌ Not found in range 0..{MAX_SUBID-1:,}")

    print(f"Output saved to {output_file}")


def main():
    mp.freeze_support()

    g_address = input("Enter your G-address: ").strip().upper()
    target_suffix = input("Enter target suffix (e.g. WORD): ").strip().upper()

    if not target_suffix:
        raise SystemExit("Target suffix cannot be empty.")

    output_file = f"{g_address}.suffix_{target_suffix}.txt"

    n_workers = os.cpu_count() or 4
    print(f"[MAIN] Searching muxed addresses for: {g_address}")
    print(f"[MAIN] Target suffix: {target_suffix}")
    print(f"[MAIN] Using {n_workers} worker processes.")
    print(f"[MAIN] MAX_SUBID={MAX_SUBID:,} | CHUNK_SIZE={CHUNK_SIZE:,}")

    stop_event = mp.Event()

    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]" = mp.Queue(maxsize=n_workers * 4)
    found_q: "mp.Queue[str]" = mp.Queue(maxsize=10)
    stats_q: "mp.Queue[int]" = mp.Queue(maxsize=10_000)

    workers: list[mp.Process] = []
    for _ in range(n_workers):
        p = mp.Process(
            target=worker_process,
            args=(g_address, target_suffix, chunk_q, found_q, stats_q, stop_event),
            daemon=True,
        )
        p.start()
        workers.append(p)

    feeder = mp.Process(
        target=feed_chunks,
        args=(chunk_q, stop_event, MAX_SUBID, CHUNK_SIZE, n_workers),
        daemon=True,
    )
    feeder.start()

    try:
        monitor_and_write(output_file, found_q, stats_q, stop_event, target_suffix)
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted. Stopping...")
        stop_event.set()
    finally:
        stop_event.set()
        time.sleep(0.1)

        feeder.join(timeout=2)
        for p in workers:
            p.join(timeout=2)

        print("\n✅ Done.")


if __name__ == "__main__":
    main()
