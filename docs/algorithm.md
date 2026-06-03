# Algorithm Documentation — BC.Game Mines Provably Fair

> Source: Observed from `bc.game/help/provably-fair` frontend code (May 2026).
> This document describes the exact algorithm implemented in `core/crypto.py`.

---

## Overview

BC.Game Mines uses a double-pass hash-rotation shuffle to derive mine positions
deterministically from three inputs: a server seed, a client seed, and a nonce.

The algorithm is verifiable by anyone who knows all three inputs.

---

## Step 1 — HMAC-SHA256

```
hash = HMAC_SHA256(key=serverSeed, message="{clientSeed}:{nonce}")
```

- **Key:** The server seed (kept secret until after the game)
- **Message:** The client seed and nonce joined with a colon
- **Nonce:** Starts at **0** on BC.Game (not 1)
- **Output:** 64-character lowercase hexadecimal string

Python:
```python
import hmac, hashlib
result = hmac.new(
    server_seed.encode(),
    f"{client_seed}:{nonce}".encode(),
    hashlib.sha256
).hexdigest()
```

---

## Step 2 — Reference Array

BC.Game does **not** shuffle `[0..24]`. It uses a fixed hardcoded reference array:

```python
ALL_NUMS = [7, 2, 19, 25, 1, 13, 5, 24, 14, 6, 15, 9, 22, 16, 3, 12, 10, 23, 11, ...]
```

This 25-element array is the starting point for both shuffle passes.
Values are **1-based cell positions** (1 = top-left, 25 = bottom-right).

See `data/reference_board.py` for the full array and verification status.

---

## Step 3 — Hash Rotation (createNums)

JavaScript equivalent:
```javascript
function createNums(allNums, seed) {
    let nums = []
    let h = crypto.createHash("SHA256").update(seed).digest("hex")
    allNums.forEach(c => {
        nums.push({ num: c, hash: h })
        h = h.substring(1) + h.charAt(0)   // rotate left by 1
    })
    // ... sort and return
}
```

Python equivalent:
```python
def create_nums(all_nums, seed):
    h = sha256(seed)           # SHA256 of seed, NOT seed itself
    annotated = []
    for num in all_nums:
        annotated.append({"num": num, "hash": h})
        h = h[1:] + h[0]      # rotate left: "abcdef" → "bcdefa"
    # Sort descending by hash string...
```

**Critical details:**
- `h` is initialised as `SHA256(seed)`, not the seed itself
- Rotation is **left rotation** by 1 character
- After each element is annotated, `h` rotates to its next value
- This produces 25 unique hash keys tied to the seed

---

## Step 4 — Descending Lexicographic Sort

The annotated array is sorted in **descending** lexicographic order by hash:

```javascript
nums.sort(function(o1, o2) {
    if (o1.hash < o2.hash) return 1      // descending: smaller hash goes later
    else if (o1.hash === o2.hash) return 0
    else return -1
})
```

Python:
```python
sorted(annotated, key=lambda x: x["hash"], reverse=True)
```

---

## Step 5 — Double Pass

This is the most important structural feature of the BC.Game algorithm.
**Two passes** are performed, not one.

```javascript
function getResult(hash) {
    let seed = hash
    let finalNums = createNums(allNums, seed)       // Pass 1: original array
    seed = SHA256(seed)                             // Re-hash the seed
    finalNums = createNums(finalNums, seed)         // Pass 2: output of pass 1
    return finalNums.map(m => m.num)
}
```

Pass 1:
- Input: `ALL_NUMS` (original reference array)
- Seed: `hmac_result`

Pass 2:
- Input: **output of Pass 1** (not the original ALL_NUMS)
- Seed: `SHA256(hmac_result)`

The second pass shuffles an already-shuffled array with a derived seed.
This increases the effective mixing of the shuffle.

---

## Step 6 — Mine Extraction

The first `mineCount` values of the final array are the mine positions:

```
finalNums = [7, 19, 3, 12, ...]
mines_3   = [7, 19, 3]            # for 3 mines
mines_5   = [7, 19, 3, 12, ...]   # for 5 mines
```

Positions are **1-based** (1 = cell in row 1, col 1).

---

## Full Flow Diagram

```
serverSeed + clientSeed + nonce
        │
        ▼
HMAC-SHA256(key=serverSeed, msg="clientSeed:nonce")
        │
        ├──── hmac_result ─────────────────────────────────────┐
        │                                                       │
        ▼                                                       ▼
  Pass 1: createNums(ALL_NUMS, hmac_result)            SHA256(hmac_result)
        │                                                       │
        ├── sorted_result (Pass 1 output) ────┐                │
                                              ▼                ▼
                               Pass 2: createNums(pass1_output, SHA256(hmac_result))
                                              │
                                              ▼
                                    final_order (25 values)
                                              │
                                              ▼
                                  first N values = mine positions
```

---

## Key Differences from Generic Implementations

| Aspect | Generic Fisher-Yates | BC.Game Algorithm |
|--------|---------------------|-------------------|
| Starting array | `[0..24]` | Fixed `ALL_NUMS` (1-based) |
| Nonce base | 1 | **0** |
| Shuffle mechanism | Fisher-Yates (float-driven) | Hash rotation + lexicographic sort |
| Number of passes | 1 | **2** |
| Pass 2 input | Same array | **Output of pass 1** |
| Pass 2 seed | Same or next | `SHA256(hmac_result)` |
| Position base | 0-based | **1-based** |

---

## Reference Array Status

The `ALL_NUMS` array in `data/reference_board.py` was observed from BC.Game's
provably fair documentation. **The last 6 values are not fully confirmed** from
the screenshot — they are marked as `UNCONFIRMED`.

To verify them yourself:
1. Visit `bc.game/help/provably-fair`
2. Select "Mines" from the game dropdown
3. The full `allNums` array is shown in the code block

Once confirmed, update `data/reference_board.py` and set `ARRAY_VERIFIED = True`.
