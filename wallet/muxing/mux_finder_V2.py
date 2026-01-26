"""
mux_wordhunt_mp.py  (Windows / multiprocessing)

How this version is improved vs the threaded script:
- Uses multiprocessing (real parallelism on Windows): avoids the GIL bottleneck that makes CPU-bound threading slow.
- Chunked sub-ID allocation: each worker processes a whole range of IDs at once (far fewer locks / shared-state overhead).
- No per-attempt global locks: attempts are counted locally in each process and reported back in batches.
- Single writer process: workers never write to disk (avoids file corruption/locking). A dedicated writer receives results and appends safely.
- Time/line-based flushing: results are written steadily (not “every 100 unique words”, which may never happen).
- Duplicate-word suppression is centralized: only one place decides whether a word was already seen.

Notes:
- MAX_SUBID is set to 2**32 by default (4,294,967,296). Muxed IDs are actually uint64 (2**64),
  but scanning anywhere near that is infeasible; raise MAX_SUBID only if you have a bounded target range.
- On Windows you MUST keep the `if __name__ == "__main__":` guard for multiprocessing.
"""

import os
import time
import queue
import multiprocessing as mp
from typing import Optional, Tuple

from stellar_sdk import MuxedAccount
from wordfreq import top_n_list


# -------------------- Config --------------------

TOP_WORDS = 5000
MIN_WORD_LEN = 4
MAX_WORD_LEN = 10

# Default range (fast enough to demo; still huge). Change to 2**64 for the true space (not realistically scannable).
MAX_SUBID = 2**32

# Chunk size per worker fetch (tune for throughput; larger = fewer scheduler hops, but less responsive to stop).
CHUNK_SIZE = 200_000

# How often workers report attempts (in attempts per report).
REPORT_EVERY = 250_000

# Writer flush control
FLUSH_EVERY_LINES = 50
STATS_INTERVAL_SEC = 5


# -------------------- Helpers --------------------

def build_dictionary() -> set[str]:
    # Uppercase set for quick membership checks
    return set(w.upper() for w in top_n_list("en", TOP_WORDS))


def is_valid_suffix(m_address: str, english_words: set[str]) -> Optional[str]:
    # Longest-first tends to be more “interesting” (more specific) matches
    upper = m_address.upper()
    for length in range(MAX_WORD_LEN, MIN_WORD_LEN - 1, -1):
        suffix = upper[-length:]
        if suffix in english_words:
            return suffix
    return None


# -------------------- Worker --------------------

def worker_process(
    g_address: str,
    english_words: set[str],
    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]",
    result_q: "mp.Queue[Tuple[str, str]]",
    stats_q: "mp.Queue[int]",
    stop_event: "mp.Event",
) -> None:
    """
    Receives (start, end) subid ranges from chunk_q.
    Generates muxed addresses and sends (m_address, matched_word) to result_q.
    Reports attempt counts periodically to stats_q.
    """
    local_attempts = 0
    try:
        while not stop_event.is_set():
            try:
                chunk = chunk_q.get(timeout=0.5)
            except queue.Empty:
                continue

            if chunk is None:
                # Sentinel => no more work
                break

            start, end = chunk
            for sub_id in range(start, end):
                if stop_event.is_set():
                    break

                m_address = MuxedAccount(g_address, sub_id).account_muxed
                match = is_valid_suffix(m_address, english_words)
                if match:
                    # Send the full muxed address + the matched word
                    result_q.put((m_address, match))

                local_attempts += 1
                if local_attempts >= REPORT_EVERY:
                    stats_q.put(local_attempts)
                    local_attempts = 0

    finally:
        if local_attempts:
            stats_q.put(local_attempts)


# -------------------- Writer / Coordinator --------------------

def writer_and_monitor(
    output_file: str,
    result_q: "mp.Queue[Tuple[str, str]]",
    stats_q: "mp.Queue[int]",
    stop_event: "mp.Event",
) -> None:
    """
    Single place that:
    - writes matches to disk
    - suppresses duplicate matched words (global)
    - prints stats periodically
    """
    found_words: set[str] = set()
    buffer: list[str] = []

    total_attempts = 0
    total_found = 0

    start_time = time.time()
    last_stats = start_time

    # Ensure output file is fresh
    if os.path.exists(output_file):
        os.remove(output_file)

    while not stop_event.is_set():
        now = time.time()

        # Drain stats updates quickly
        drained_any = False
        while True:
            try:
                inc = stats_q.get_nowait()
            except queue.Empty:
                break
            total_attempts += inc
            drained_any = True

        # Drain results
        while True:
            try:
                m_address, word = result_q.get_nowait()
            except queue.Empty:
                break

            word_u = word.upper()
            if word_u not in found_words:
                found_words.add(word_u)
                total_found += 1
                buffer.append(f"{m_address}  <- ends in word: {word_u}\n")

                if len(buffer) >= FLUSH_EVERY_LINES:
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.writelines(buffer)
                    buffer.clear()

        # Periodic stats print
        if now - last_stats >= STATS_INTERVAL_SEC:
            elapsed = now - start_time
            rate = (total_attempts / elapsed) if elapsed > 0 else 0.0
            ratio = (total_found / total_attempts * 100) if total_attempts else 0.0
            print(
                f"[STATS] Checked: {total_attempts:,} | Found(unique words): {total_found} "
                f"| Speed: {rate:,.2f}/s | F/C: {ratio:.6f}%"
            )
            last_stats = now

        # Light sleep to avoid busy spinning if queues are empty
        if not drained_any and result_q.empty():
            time.sleep(0.02)

    # Final flush on stop
    if buffer:
        with open(output_file, "a", encoding="utf-8") as f:
            f.writelines(buffer)


# -------------------- Chunk feeder --------------------

def feed_chunks(
    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]",
    stop_event: "mp.Event",
    max_subid: int,
    chunk_size: int,
    n_workers: int,
) -> None:
    """
    Pushes (start, end) ranges into chunk_q up to max_subid.
    Then sends one None sentinel per worker.
    """
    subid = 0
    while subid < max_subid and not stop_event.is_set():
        end = min(max_subid, subid + chunk_size)
        chunk_q.put((subid, end))
        subid = end

    # Tell workers to exit
    for _ in range(n_workers):
        chunk_q.put(None)


# -------------------- Main --------------------

def main():
    english_words = build_dictionary()

    g_address = input("Enter your G-address: ").strip().upper()
    output_file = f"{g_address}.words.txt"

    # Multiprocessing config
    n_workers = os.cpu_count() or 4
    print(f"[MAIN] Starting muxed address word search for: {g_address}")
    print(f"[MAIN] Using {n_workers} worker processes (Windows multiprocessing).")
    print(f"[MAIN] MAX_SUBID={MAX_SUBID:,} | CHUNK_SIZE={CHUNK_SIZE:,}")

    mp.freeze_support()  # helpful on Windows packaging; harmless otherwise

    manager_stop = mp.Event()

    # Queues: chunks, results, stats
    chunk_q: "mp.Queue[Optional[Tuple[int, int]]]" = mp.Queue(maxsize=n_workers * 4)
    result_q: "mp.Queue[Tuple[str, str]]" = mp.Queue(maxsize=10_000)
    stats_q: "mp.Queue[int]" = mp.Queue(maxsize=10_000)

    # Writer/monitor runs in the main process (simpler output + file IO)
    # Start workers
    workers: list[mp.Process] = []
    for _ in range(n_workers):
        p = mp.Process(
            target=worker_process,
            args=(g_address, english_words, chunk_q, result_q, stats_q, manager_stop),
            daemon=True,
        )
        p.start()
        workers.append(p)

    # Feed chunks from a separate process so the main can focus on writing/stats
    feeder = mp.Process(
        target=feed_chunks,
        args=(chunk_q, manager_stop, MAX_SUBID, CHUNK_SIZE, n_workers),
        daemon=True,
    )
    feeder.start()

    try:
        writer_and_monitor(output_file, result_q, stats_q, manager_stop)
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted. Stopping...")
        manager_stop.set()
    finally:
        # Ensure stop and wait
        manager_stop.set()

        # Allow writer loop to exit cleanly
        time.sleep(0.1)

        # Join feeder/workers
        feeder.join(timeout=2)
        for p in workers:
            p.join(timeout=2)

        print(f"\n✅ Done. Output saved to {output_file}")


if __name__ == "__main__":
    main()
