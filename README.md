# Bitcoin Puzzle #71 Solver

High-performance Bitcoin Puzzle #71 solver written in Python.

This implementation uses **random block scanning** combined with **incremental elliptic curve point subtraction (`P -= G`)** to avoid performing a full scalar multiplication for every private key tested.

If the `coincurve` library is available, the solver uses the incremental EC optimization. Otherwise, it automatically falls back to standard scalar multiplication using `secp256k1`.

## Features

- Random block scanning
- Immediate global stop when a solution is found
- Multi-core processing using Python's `multiprocessing`
- Incremental public key updates (`P -= G`)
- Automatic fallback to scalar multiplication
- Live statistics:
  - Elapsed time
  - Keys tested
  - Keys per second
  - Active workers

## Requirements

- Python 3.9+
- coincurve (recommended)

or

- secp256k1 (fallback)

Install dependencies:

```bash
pip install coincurve
```

or

```bash
pip install secp256k1
```

## Running

```bash
python solver.py
```

Example output:

```text
Bitcoin Puzzle #71

mode     incremental P-=G
backend  coincurve
address  1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU
range    0x400000000000000000 .. 0x7fffffffffffffffff
workers  16 · block 100,000

  15.2s │ 98.25M keys │ 6,470,000 keys/s │ 16/16 workers
```

If the private key is found:

```text
KEY FOUND (worker 7)

hex     0000000000000000000000000000000000000000000000123456789abcdef0
time    312.48s
total   2.03B keys (6,500,000 keys/s)
```

## Configuration

The following parameters can be modified directly in the source code:

| Variable | Description |
|----------|-------------|
| `PUZZLE_BITS` | Puzzle size in bits |
| `BLOCK_SIZE` | Number of keys scanned per random block |
| `NUM_WORKERS` | Number of worker processes |
| `CHECK_EVERY` | Frequency for checking the global stop flag |
| `LOG_INTERVAL` | Statistics refresh interval |
| `TARGET_ADDRESS` | Target Bitcoin address |
| `TARGET_HASH` | HASH160 of the target public key |

## Algorithm

1. Generate a random starting private key.
2. Scan downward over a fixed-size block.
3. Compute the initial public key only once.
4. Update the public key using:

```
P = P - G
```

instead of recalculating:

```
P = kG
```

for every private key.

5. Compare the HASH160 of the compressed public key against the target.
6. When one worker finds the solution, all remaining workers stop immediately.

## Performance

Using `coincurve` significantly reduces the amount of elliptic curve computations required because only the initial point multiplication is performed for each block.

Performance depends on:

- CPU
- Number of cores
- Block size
- Python version
- coincurve implementation

## Donations

If you find this project useful and would like to support its development, you can donate Bitcoin.

**Bitcoin (BTC)**

```
bc1qlhpleren2hxklzk6r8qj2ap63u2nuczj5cz0wr
```

Or send directly to:

**bc1qlhpleren2hxklzk6r8qj2ap63u2nuczj5cz0wr**

Thank you for your support!
