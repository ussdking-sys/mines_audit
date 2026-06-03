"""
core/auditor.py — Main audit orchestrator.

Ties together the cryptographic engine, models, and validation logic
into a single high-level interface.

This is the primary entry point for programmatic use of the audit framework.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from core.models import (
    AuditInput, AuditResult, BatchResult,
    CommitmentVerification,
)
from core.crypto import (
    derive_board, verify_commitment, compare_positions,
)
from data.reference_board import ALL_NUMS, VALIDATION as REF_VALIDATION


class Auditor:
    """
    BC.Game Mines provably fair auditor.

    Performs deterministic board derivation and verification using the
    exact BC.Game algorithm.

    Usage:
        auditor = Auditor()
        result  = auditor.audit(AuditInput(
            server_seed      = "...",
            client_seed      = "...",
            nonce            = 0,
            mine_count       = 3,
            server_seed_hash = "...",
        ))
        print(result.board.mine_positions_1b)
    """

    def __init__(
        self,
        reference_array: Optional[list[int]] = None,
        warn_unverified: bool                = True,
    ):
        """
        Args:
            reference_array: Override the default ALL_NUMS array.
                             If None, uses data/reference_board.py.
            warn_unverified: If True, include a warning in results when
                             the reference array is not fully confirmed.
        """
        self._all_nums       = reference_array or list(ALL_NUMS)
        self._warn_unverified = warn_unverified
        self._ref_verified   = REF_VALIDATION["verified"]

        # Validate reference array on construction
        if not REF_VALIDATION["valid"]:
            raise ValueError(
                f"Reference board array is invalid: {REF_VALIDATION['errors']}"
            )

    # ------------------------------------------------------------------
    # Primary audit interface
    # ------------------------------------------------------------------

    def audit(
        self,
        audit_input:    AuditInput,
        claimed_mines:  Optional[list[int]] = None,
    ) -> AuditResult:
        """
        Perform a complete provably fair audit for one round.

        Args:
            audit_input:   All seeds, nonce, and mine count for this round
            claimed_mines: Optional list of 1-based mine positions as shown
                           in-game (for comparison against derived positions)

        Returns:
            AuditResult with full derivation chain and verification status
        """
        # ── Board derivation ──────────────────────────────────────────────
        crypto_chain, pass1, pass2, board = derive_board(
            server_seed = audit_input.server_seed,
            client_seed = audit_input.client_seed,
            nonce       = audit_input.nonce,
            mine_count  = audit_input.mine_count,
            all_nums    = self._all_nums,
        )

        # ── Commitment verification ───────────────────────────────────────
        commitment: Optional[CommitmentVerification] = None
        if audit_input.server_seed_hash:
            commitment = verify_commitment(
                server_seed    = audit_input.server_seed,
                published_hash = audit_input.server_seed_hash,
            )

        # ── Position comparison ───────────────────────────────────────────
        positions_match: Optional[bool] = None
        if claimed_mines is not None:
            positions_match, _ = compare_positions(
                derived = board.mine_positions_1b,
                claimed = claimed_mines,
            )

        return AuditResult(
            audit_input        = audit_input,
            crypto_chain       = crypto_chain,
            pass1              = pass1,
            pass2              = pass2,
            board              = board,
            commitment         = commitment,
            claimed_mines      = claimed_mines,
            positions_match    = positions_match,
            reference_verified = self._ref_verified,
        )

    def audit_from_dict(
        self,
        data:          dict,
        claimed_mines: Optional[list[int]] = None,
    ) -> AuditResult:
        """
        Convenience: audit from a raw dict (e.g. loaded from JSON file).

        Supports both camelCase (BC.Game native) and snake_case keys.
        """
        return self.audit(AuditInput.from_dict(data), claimed_mines)

    # ------------------------------------------------------------------
    # Batch audit
    # ------------------------------------------------------------------

    def audit_batch(
        self,
        rounds: list[dict],
    ) -> BatchResult:
        """
        Audit multiple rounds from a list of dicts.

        Each dict may include a "claimedMines" / "claimed_mines" key
        (list of 1-based ints) for position comparison.

        Args:
            rounds: List of round dicts (same format as sample_batch.json)

        Returns:
            BatchResult with all individual results and aggregate statistics
        """
        results = []
        passed  = 0
        failed  = 0
        errors  = 0

        for i, round_data in enumerate(rounds):
            try:
                claimed = round_data.get("claimedMines") or round_data.get("claimed_mines")
                result  = self.audit_from_dict(round_data, claimed_mines=claimed)
                results.append(result)

                if result.fully_verified:
                    passed += 1
                else:
                    failed += 1

            except Exception as exc:
                errors += 1
                # Create a minimal failed result placeholder
                # (so the batch result is still exportable)
                print(f"  [!] Round {i+1} error: {exc}", file=sys.stderr)

        return BatchResult(
            total   = len(rounds),
            passed  = passed,
            failed  = failed,
            errors  = errors,
            results = results,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_reference_status(self) -> dict:
        """Return the reference board validation status."""
        return REF_VALIDATION

    def derive_mines_only(
        self,
        server_seed: str,
        client_seed: str,
        nonce:       int,
        mine_count:  int,
    ) -> list[int]:
        """
        Minimal interface: just return mine positions (1-based).
        No commitment verification or full audit trail.

        Useful for quick scripted checks.
        """
        _, _, _, board = derive_board(
            server_seed = server_seed,
            client_seed = client_seed,
            nonce       = nonce,
            mine_count  = mine_count,
            all_nums    = self._all_nums,
        )
        return board.mine_positions_1b
