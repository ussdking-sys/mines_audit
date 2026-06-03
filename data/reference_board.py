"""
data/reference_board.py — BC.Game fixed reference position array.

This is the hardcoded ALL_NUMS array observed in BC.Game's provably fair
frontend source code (bc.game/help/provably-fair, Mines game).

IMPORTANT:
  BC.Game does NOT shuffle [0..24] like a generic Fisher-Yates implementation.
  Instead, this fixed reference array is used as the starting positions
  before the hash-rotation sort mechanism is applied.

  The values represent 1-based cell positions on the 5x5 board.
  Cell 1 = top-left (row 1, col 1), Cell 25 = bottom-right (row 5, col 5).

SOURCE:
  Extracted from bc.game/help/provably-fair frontend code (May 2026).
  The array was observed as:
    [7, 2, 19, 25, 1, 13, 5, 24, 14, 6, 15, 9, 22, 16, 3, 12, 10, 23, 11, ...]
  with the remaining 6 values (positions 20-25) not fully visible in the
  screenshot. The placeholder values below complete the 25-element array
  using the remaining unassigned positions.

  *** VERIFICATION REQUIRED ***
  The last 6 values are marked with # UNCONFIRMED.
  They should be replaced once extracted from the full source.
  To update: edit ALL_NUMS below and set ARRAY_VERIFIED = True.

UPDATING THIS FILE:
  If you have access to the complete BC.Game source or can extract it via
  browser devtools, replace the UNCONFIRMED entries with the actual values
  and set ARRAY_VERIFIED = True.

  The array must contain exactly 25 unique integers, each in range 1-25.
"""

# ---------------------------------------------------------------------------
# Verification flag — set to True once all 25 values are confirmed
# ---------------------------------------------------------------------------
ARRAY_VERIFIED: bool = False

# ---------------------------------------------------------------------------
# The 25-element reference array
# Confirmed values (positions 1-19) from screenshot observation
# UNCONFIRMED values (positions 20-25) are marked
# ---------------------------------------------------------------------------
ALL_NUMS: list[int] = [
    7,   2,  19,  25,   1,   # row 1 of reference  (confirmed)
    13,  5,  24,  14,   6,   # row 2 of reference  (confirmed)
    15,  9,  22,  16,   3,   # row 3 of reference  (confirmed)
    12, 10,  23,  11,        # row 4 partial        (confirmed)
    # --- UNCONFIRMED — replace with actual BC.Game values ---
    4,  8,  17,  20,  18,  21,  # UNCONFIRMED
]

# Trim to exactly 25 (safety guard in case of accidental over-specification)
ALL_NUMS = ALL_NUMS[:25]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_reference_board() -> dict:
    """
    Validate the reference board array for correctness.

    Returns a dict with:
      valid:    bool — True if array passes all checks
      errors:   list of error strings
      warnings: list of warning strings
    """
    errors   = []
    warnings = []

    if len(ALL_NUMS) != 25:
        errors.append(f"Array length is {len(ALL_NUMS)}, expected 25")

    if sorted(ALL_NUMS) != list(range(1, 26)):
        missing  = set(range(1, 26)) - set(ALL_NUMS)
        dupes    = [x for x in ALL_NUMS if ALL_NUMS.count(x) > 1]
        if missing:
            errors.append(f"Missing values: {sorted(missing)}")
        if dupes:
            errors.append(f"Duplicate values: {sorted(set(dupes))}")

    if not ARRAY_VERIFIED:
        warnings.append(
            "Reference array is PARTIALLY UNCONFIRMED. "
            "The last 6 values (indices 19-24) have not been verified "
            "against the live BC.Game source. Audit results may differ "
            "for rounds using those shuffle positions."
        )

    return {
        "valid":    len(errors) == 0,
        "verified": ARRAY_VERIFIED,
        "errors":   errors,
        "warnings": warnings,
        "length":   len(ALL_NUMS),
    }


# Run validation on import and expose result
VALIDATION = validate_reference_board()
