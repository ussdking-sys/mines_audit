"""
core/crypto.py — Exact BC.Game cryptographic primitives.

Implements the PRECISE algorithm observed from BC.Game's provably fair
frontend source code. No substitutions, no approximations.

Algorithm summary:
  1. HMAC-SHA256(key=serverSeed, message="{clientSeed}:{nonce}")
  2. SHA256(hmac_result) → initial h for pass 1
  3. For each element in reference array:
       annotate with current h, then rotate h left by 1 char
  4. Sort annotated array DESCENDING by hash string (lexicographic)
  5. SHA256(hmac_result) → pass 2 seed
  6. Repeat steps 2-4 using pass 1 output as input array
  7. First mine_count values of final array = mine positions

CRITICAL IMPLEMENTATION NOTES:
  - Nonce starts at 0 (not 1 as in generic implementations)
  - Hash rotation is LEFT rotation: h = h[1:] + h[0]
  - Sort direction is DESCENDING (reverse=True)
  - Double-pass is MANDATORY — single pass is incorrect
  - Uses SHA256 of hmac result, NOT raw hmac bytes, as the sort seed
"""

import hmac
import hashlib
from typing import Optional

from core.models import (
    CryptoChain, ShuffleEntry, ShufflePass,
    BoardState, CommitmentVerification,
)


# ---------------------------------------------------------------------------
# Low-level hash primitives
# ---------------------------------------------------------------------------

def sha256_hex(data: str) -> str:
    """
    Return the SHA256 hex digest of a UTF-8 encoded string.

    Args:
        data: Input string

    Returns:
        64-character lowercase hexadecimal string
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hmac_sha256_hex(key: str, message: str) -> str:
    """
    Return the HMAC-SHA256 hex digest.

    BC.Game formula:
        HMAC_SHA256(key=serverSeed, message="{clientSeed}:{nonce}")

    Args:
        key:     The server seed string
        message: The message string (f"{clientSeed}:{nonce}")

    Returns:
        64-character lowercase hexadecimal string
    """
    return hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def rotate_left(h: str) -> str:
    """
    Rotate a string LEFT by one character.

    BC.Game JavaScript equivalent:
        h = h.substring(1) + h.charAt(0)

    Example:
        "abcdef" → "bcdefa"

    Args:
        h: Input string (typically a 64-char hex hash)

    Returns:
        String with first character moved to the end
    """
    if not h:
        return h
    return h[1:] + h[0]


# ---------------------------------------------------------------------------
# Core shuffle step
# ---------------------------------------------------------------------------

def create_nums(all_nums: list[int], seed: str) -> ShufflePass:
    """
    BC.Game createNums() function — annotate array with rotated hashes,
    then sort descending.

    Exact BC.Game logic:
        let h = SHA256(seed)
        allNums.forEach(c => {
            nums.push({ num: c, hash: h })
            h = h.substring(1) + h.charAt(0)
        })
        nums.sort((o1, o2) => {
            if (o1.hash < o2.hash) return 1      // descending
            else if (o1.hash === o2.hash) return 0
            else return -1
        })

    Args:
        all_nums: Input array of cell positions (25 integers)
        seed:     Hash string used to initialise h

    Returns:
        ShufflePass with full annotated and sorted state
    """
    # Step 1: SHA256 the seed to get initial h
    h = sha256_hex(seed)
    h_initial = h

    # Step 2: Annotate each number with its current h, then rotate
    annotated: list[ShuffleEntry] = []
    for num in all_nums:
        annotated.append(ShuffleEntry(num=num, hash=h))
        h = rotate_left(h)

    # Step 3: Stable descending sort on hash string (lexicographic)
    # Python's sort is stable, matching JS Array.prototype.sort stability
    sorted_annotated = sorted(annotated, key=lambda x: x.hash, reverse=True)
    sorted_result    = [entry.num for entry in sorted_annotated]

    return ShufflePass(
        input_array   = list(all_nums),
        seed_used     = seed,
        h_initial     = h_initial,
        annotated     = annotated,          # Pre-sort order
        sorted_result = sorted_result,      # Post-sort order
    )


# ---------------------------------------------------------------------------
# Full board derivation
# ---------------------------------------------------------------------------

def derive_board(
    server_seed:  str,
    client_seed:  str,
    nonce:        int,
    mine_count:   int,
    all_nums:     list[int],
) -> tuple[CryptoChain, ShufflePass, ShufflePass, BoardState]:
    """
    Full BC.Game board derivation — double-pass shuffle.

    Implements the exact main() function from BC.Game's provably fair code:

        function main(serverSeed, clientSeed, nonce) {
            let resultArr = [clientSeed, nonce]
            let hmacSha256Result = crypto.createHmac("sha256", serverSeed)
                                         .update(resultArr.join(":"))
                                         .digest("hex")
            let resultList = getResult(hmacSha256Result)
            console.log(resultList)
        }

        function getResult(hash) {
            let seed = hash
            let finalNums = createNums(allNums, seed)
            seed = SHA256(seed)
            finalNums = createNums(finalNums, seed)   ← second pass uses output of first
            return finalNums.map(m => m.num)
        }

    Args:
        server_seed: Revealed server seed string
        client_seed: Player client seed string
        nonce:       Round nonce (starts at 0 on BC.Game)
        mine_count:  Number of mines (1-24)
        all_nums:    The 25-element reference array from data/reference_board.py

    Returns:
        Tuple of (CryptoChain, ShufflePass1, ShufflePass2, BoardState)
    """
    # ── Step 1: HMAC ──────────────────────────────────────────────────────
    message     = f"{client_seed}:{nonce}"
    hmac_result = hmac_sha256_hex(key=server_seed, message=message)

    # ── Step 2: First pass ────────────────────────────────────────────────
    # seed for pass 1 = hmac_result directly
    pass1_seed = hmac_result
    pass1      = create_nums(all_nums, pass1_seed)

    # SHA256 of pass1_seed (for CryptoChain record)
    pass1_seed_sha256 = sha256_hex(pass1_seed)

    # ── Step 3: Second pass ───────────────────────────────────────────────
    # seed for pass 2 = SHA256(hmac_result)  ← this is the crucial BC.Game step
    pass2_seed        = sha256_hex(hmac_result)
    pass2_seed_sha256 = sha256_hex(pass2_seed)

    # Second pass uses the SORTED OUTPUT of pass 1 as its input array
    pass2 = create_nums(pass1.sorted_result, pass2_seed)

    # ── Step 4: Extract mines ─────────────────────────────────────────────
    final_order      = pass2.sorted_result
    mine_positions_1b = final_order[:mine_count]          # 1-based positions
    mine_positions_0b = [p - 1 for p in mine_positions_1b]  # 0-based indices
    safe_positions   = [p for p in final_order if p not in mine_positions_1b]

    # Build output objects
    crypto_chain = CryptoChain(
        hmac_input_message = message,
        hmac_result        = hmac_result,
        pass1_seed         = pass1_seed,
        pass1_seed_sha256  = pass1_seed_sha256,
        pass2_seed         = pass2_seed,
        pass2_seed_sha256  = pass2_seed_sha256,
    )

    board = BoardState(
        final_order       = final_order,
        mine_positions_1b = mine_positions_1b,
        mine_positions_0b = mine_positions_0b,
        mine_count        = mine_count,
        safe_positions    = safe_positions,
    )

    return crypto_chain, pass1, pass2, board


# ---------------------------------------------------------------------------
# Commitment verification
# ---------------------------------------------------------------------------

def verify_commitment(
    server_seed:      str,
    published_hash:   str,
) -> CommitmentVerification:
    """
    Verify that the revealed server seed matches the pre-published hash.

    BC.Game publishes SHA256(serverSeed) before the game starts.
    After the game, they reveal serverSeed.
    You verify: SHA256(serverSeed) == publishedHash.

    Args:
        server_seed:    The server seed revealed after the game
        published_hash: The hash shown in the Seed Setting panel before play

    Returns:
        CommitmentVerification with result details
    """
    computed   = sha256_hex(server_seed)
    verified   = computed.lower() == published_hash.lower()

    if verified:
        detail = "SHA256(serverSeed) matches the published hash. Commitment is valid."
    else:
        detail = (
            f"MISMATCH. Computed: {computed[:16]}...  "
            f"Published: {published_hash[:16]}...  "
            "The server seed does not match its pre-game commitment."
        )

    return CommitmentVerification(
        server_seed    = server_seed,
        published_hash = published_hash,
        computed_hash  = computed,
        verified       = verified,
        match_detail   = detail,
    )


# ---------------------------------------------------------------------------
# Position comparison
# ---------------------------------------------------------------------------

def compare_positions(
    derived:  list[int],
    claimed:  list[int],
) -> tuple[bool, str]:
    """
    Compare derived mine positions against claimed (observed) positions.

    Args:
        derived: Mine positions from cryptographic derivation (1-based)
        claimed: Mine positions as shown in the game (1-based)

    Returns:
        Tuple of (match: bool, detail: str)
    """
    derived_set = set(derived)
    claimed_set = set(claimed)

    if derived_set == claimed_set:
        return True, "Derived positions exactly match claimed positions."

    missing_from_claimed = derived_set - claimed_set
    extra_in_claimed     = claimed_set - derived_set

    parts = ["MISMATCH."]
    if missing_from_claimed:
        parts.append(f"In derived but not claimed: {sorted(missing_from_claimed)}")
    if extra_in_claimed:
        parts.append(f"In claimed but not derived: {sorted(extra_in_claimed)}")

    return False, "  ".join(parts)
