#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bitcoin Puzzle #71 Solver
Random block scanning with immediate global stop
+ incremental EC point (P -= G) via coincurve instead of
full scalar multiplication on every key.
"""

import multiprocessing
import os
import random
import sys
import time
from hashlib import sha256, new
from queue import Empty

try:
    from coincurve import PublicKey
    USE_COINCURVE = True
except ImportError:
    from secp256k1 import PrivateKey
    USE_COINCURVE = False


# ========= CONFIG =========

PUZZLE_BITS = 71

START = 1 << (PUZZLE_BITS - 1)
END = (1 << PUZZLE_BITS) - 1

NUM_WORKERS = max(1, multiprocessing.cpu_count())

BLOCK_SIZE = 100_000

# How often to poll the global stop event (keys)
CHECK_EVERY = 10_000

# Parent status line refresh interval (seconds)
LOG_INTERVAL = 1.0

TARGET_ADDRESS = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"

TARGET_HASH = bytes.fromhex(
    "f6f5431d25bbf7b12e8add9af5e3475c44a0a5b8"
)

# ==========================


def _negate_compressed(pub: "PublicKey") -> "PublicKey":
    data = bytearray(pub.format(compressed=True))
    data[0] = 0x03 if data[0] == 0x02 else 0x02
    return PublicKey(bytes(data))


NEG_G = None
if USE_COINCURVE:
    _G = PublicKey.from_valid_secret((1).to_bytes(32, "big"))
    NEG_G = _negate_compressed(_G)


def privkey_to_pubkey(priv_int):
    priv_bytes = priv_int.to_bytes(32, "big")

    if USE_COINCURVE:
        return PublicKey.from_valid_secret(priv_bytes).format(compressed=True)

    priv = PrivateKey()
    priv.secret = priv_bytes
    return priv.pubkey.serialize()


def pubkey_to_hash160(pub_bytes):
    return new("ripemd160", sha256(pub_bytes).digest()).digest()


def generate_random_block():
    start_key = random.randint(START + BLOCK_SIZE, END)
    end_key = start_key - BLOCK_SIZE
    return start_key, end_key


def scan_block_incremental(start_key, end_key, found_event):
    pub = PublicKey.from_valid_secret(start_key.to_bytes(32, "big"))
    checked = 0

    for priv in range(start_key, end_key, -1):
        if checked % CHECK_EVERY == 0 and found_event.is_set():
            return None

        if pubkey_to_hash160(pub.format(compressed=True)) == TARGET_HASH:
            return priv

        pub.combine([NEG_G], update=True)
        checked += 1

    return None


def scan_block_scalar(start_key, end_key, found_event):
    checked = 0

    for priv in range(start_key, end_key, -1):
        if checked % CHECK_EVERY == 0 and found_event.is_set():
            return None

        if pubkey_to_hash160(privkey_to_pubkey(priv)) == TARGET_HASH:
            return priv

        checked += 1

    return None


def worker(worker_id, found_event, result_queue, counts):
    """Workers never print — only update shared counters."""
    random.seed(os.getpid() ^ time.time_ns() ^ (worker_id << 16))
    scan = scan_block_incremental if USE_COINCURVE else scan_block_scalar
    total_processed = 0

    while not found_event.is_set():
        start_key, end_key = generate_random_block()

        found = scan(start_key, end_key, found_event)
        if found is not None:
            found_event.set()
            result_queue.put((worker_id, found))
            return

        if found_event.is_set():
            return

        total_processed += start_key - end_key
        counts[worker_id] = total_processed


def _fmt_keys(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _status_line(elapsed, total, workers_alive, num_workers):
    speed = total / elapsed if elapsed > 0 else 0
    return (
        f"\r  {elapsed:7.1f}s │ {_fmt_keys(total):>8} keys │ "
        f"{speed:>10,.0f} keys/s │ "
        f"{workers_alive}/{num_workers} workers"
    )


def main():
    mode = "incremental P-=G" if USE_COINCURVE else "scalar fallback"
    backend = "coincurve" if USE_COINCURVE else "secp256k1"

    print(
        f"\nBitcoin Puzzle #{PUZZLE_BITS}\n"
        f"  mode     {mode}\n"
        f"  backend  {backend}\n"
        f"  address  {TARGET_ADDRESS}\n"
        f"  range    {START:#x} .. {END:#x}\n"
        f"  workers  {NUM_WORKERS}  ·  block {BLOCK_SIZE:,}\n"
    )

    start_time = time.time()
    found_event = multiprocessing.Event()
    result_queue = multiprocessing.Queue()
    counts = multiprocessing.Array("Q", NUM_WORKERS)

    processes = []
    for wid in range(NUM_WORKERS):
        p = multiprocessing.Process(
            target=worker,
            args=(wid, found_event, result_queue, counts),
        )
        p.start()
        processes.append(p)

    found_key = None
    found_by = None
    last_log = 0.0

    try:
        while True:
            now = time.time()
            if now - last_log >= LOG_INTERVAL:
                last_log = now
                elapsed = now - start_time
                total = sum(counts)
                alive = sum(1 for p in processes if p.is_alive())
                sys.stdout.write(
                    _status_line(elapsed, total, alive, NUM_WORKERS)
                )
                sys.stdout.flush()

            try:
                found_by, found_key = result_queue.get(timeout=0.25)
                break
            except Empty:
                if not any(p.is_alive() for p in processes):
                    break
    except KeyboardInterrupt:
        sys.stdout.write("\n  detenido por usuario\n")
        sys.stdout.flush()

    found_event.set()

    for p in processes:
        if p.is_alive():
            p.terminate()
    for p in processes:
        p.join()

    elapsed = time.time() - start_time
    total = sum(counts)
    speed = total / elapsed if elapsed > 0 else 0

    # Clear status line, then final summary
    sys.stdout.write("\r" + " " * 72 + "\r")

    if found_key is not None:
        print(
            f"KEY ENCONTRADA  (worker {found_by})\n"
            f"  hex     {found_key:064x}\n"
            f"  tiempo  {elapsed:.2f}s\n"
            f"  total   {_fmt_keys(total)} keys  ({speed:,.0f} keys/s)\n"
        )
    else:
        print(
            f"No encontrada\n"
            f"  tiempo  {elapsed:.2f}s\n"
            f"  total   {_fmt_keys(total)} keys  ({speed:,.0f} keys/s)\n"
        )


if __name__ == "__main__":
    main()
