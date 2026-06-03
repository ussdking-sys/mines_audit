"""
core/models.py — Typed data models for all audit objects.

All input, intermediate state, and output structures are defined here
as dataclasses to ensure type safety and clean serialisation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

@dataclass
class AuditInput:
    """
    All inputs required for a complete provably fair audit.

    Minimum required for board derivation:
      server_seed, client_seed, nonce, mine_count

    Also required for commitment verification:
      server_seed_hash
    """
    server_seed:       str
    client_seed:       str
    nonce:             int
    mine_count:        int
    server_seed_hash:  Optional[str]  = None
    label:             Optional[str]  = None    # Optional human-readable round label

    def __post_init__(self) -> None:
        if not self.server_seed:
            raise ValueError("server_seed cannot be empty")
        if not self.client_seed:
            raise ValueError("client_seed cannot be empty")
        if self.nonce < 0:
            raise ValueError(f"nonce must be >= 0, got {self.nonce}")
        if not (1 <= self.mine_count <= 24):
            raise ValueError(f"mine_count must be 1-24, got {self.mine_count}")

    @classmethod
    def from_dict(cls, d: dict) -> "AuditInput":
        """Construct from a dict (e.g. loaded from JSON)."""
        return cls(
            server_seed      = d["serverSeed"],
            client_seed      = d["clientSeed"],
            nonce            = int(d["nonce"]),
            mine_count       = int(d.get("mines", d.get("mineCount", d.get("mine_count", 1)))),
            server_seed_hash = d.get("serverSeedHash") or d.get("server_seed_hash"),
            label            = d.get("label"),
        )

    def to_dict(self) -> dict:
        return {
            "serverSeed":      self.server_seed,
            "serverSeedHash":  self.server_seed_hash,
            "clientSeed":      self.client_seed,
            "nonce":           self.nonce,
            "mines":           self.mine_count,
            "label":           self.label,
        }


# ---------------------------------------------------------------------------
# Intermediate cryptographic state
# ---------------------------------------------------------------------------

@dataclass
class CryptoChain:
    """
    Full cryptographic derivation chain — every intermediate hash value
    produced during board generation.

    Stored for full auditability and step-by-step display.
    """
    hmac_input_message:  str    # "{clientSeed}:{nonce}"
    hmac_result:         str    # HMAC-SHA256 hex output (the 'seed' for pass 1)
    pass1_seed:          str    # = hmac_result
    pass1_seed_sha256:   str    # SHA256(hmac_result) — used as h in pass 1
    pass2_seed:          str    # SHA256(pass1_seed) — input to pass 2
    pass2_seed_sha256:   str    # SHA256(pass2_seed) — used as h in pass 2


@dataclass
class ShuffleEntry:
    """One entry in the hash-annotated shuffle array."""
    num:   int    # Cell position value (1-25)
    hash:  str    # 64-char rotated hash string used as sort key


@dataclass
class ShufflePass:
    """
    Result of one complete shuffle pass (createNums + sort).
    """
    input_array:    list[int]          # Array fed into this pass
    seed_used:      str                # The seed (hash) used for this pass
    h_initial:      str                # SHA256(seed) used as starting h
    annotated:      list[ShuffleEntry] # Before sort: [(num, rotated_hash), ...]
    sorted_result:  list[int]          # After descending sort: final ordered array


# ---------------------------------------------------------------------------
# Audit result models
# ---------------------------------------------------------------------------

@dataclass
class CommitmentVerification:
    """Result of verifying server seed against its published hash."""
    server_seed:       str
    published_hash:    str
    computed_hash:     str
    verified:          bool
    match_detail:      str    # Human-readable explanation


@dataclass
class BoardState:
    """
    Fully derived board state after double-shuffle completion.
    """
    final_order:        list[int]   # Full 25-element sorted array (1-based positions)
    mine_positions_1b:  list[int]   # Mine positions — 1-based (as BC.Game shows)
    mine_positions_0b:  list[int]   # Mine positions — 0-based (internal index)
    mine_count:         int
    safe_positions:     list[int]   # All safe cell positions (1-based)

    @property
    def board_grid(self) -> list[list[str]]:
        """Return a 5x5 grid of strings: 'MINE' or 'SAFE'."""
        grid = []
        for row in range(5):
            grid_row = []
            for col in range(5):
                cell_1b = row * 5 + col + 1
                grid_row.append("MINE" if cell_1b in self.mine_positions_1b else "SAFE")
            grid.append(grid_row)
        return grid


@dataclass
class AuditResult:
    """
    Complete audit result for one round.
    Contains all inputs, intermediate state, and final conclusions.
    """
    # Inputs
    audit_input:            AuditInput

    # Cryptographic chain
    crypto_chain:           CryptoChain

    # Shuffle passes
    pass1:                  ShufflePass
    pass2:                  ShufflePass

    # Board
    board:                  BoardState

    # Commitment check (None if no hash provided)
    commitment:             Optional[CommitmentVerification]

    # Claimed positions to compare against (None if not provided)
    claimed_mines:          Optional[list[int]]   # 1-based if provided
    positions_match:        Optional[bool]        # None if not compared

    # Metadata
    timestamp:              str  = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    algorithm_version:      str  = "bc-game-mines-v1"
    reference_verified:     bool = False   # Whether reference board is confirmed

    @property
    def fully_verified(self) -> bool:
        """True only when commitment verified AND positions match (if both checked)."""
        commit_ok  = self.commitment.verified if self.commitment else True
        matches_ok = self.positions_match     if self.positions_match is not None else True
        return commit_ok and matches_ok

    def to_dict(self) -> dict:
        """Serialise the full result to a JSON-compatible dict."""
        def _safe(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return {k: _safe(v) for k, v in asdict(obj).items()}
            if isinstance(obj, list):
                return [_safe(i) for i in obj]
            return obj

        return {
            "timestamp":          self.timestamp,
            "algorithm_version":  self.algorithm_version,
            "reference_verified": self.reference_verified,
            "fully_verified":     self.fully_verified,
            "input": self.audit_input.to_dict(),
            "crypto_chain": {
                "hmac_message":       self.crypto_chain.hmac_input_message,
                "hmac_result":        self.crypto_chain.hmac_result,
                "pass1_seed":         self.crypto_chain.pass1_seed,
                "pass1_seed_sha256":  self.crypto_chain.pass1_seed_sha256,
                "pass2_seed":         self.crypto_chain.pass2_seed,
                "pass2_seed_sha256":  self.crypto_chain.pass2_seed_sha256,
            },
            "pass1": {
                "input_array":    self.pass1.input_array,
                "seed_used":      self.pass1.seed_used,
                "h_initial":      self.pass1.h_initial,
                "sorted_result":  self.pass1.sorted_result,
                "annotated": [
                    {"num": e.num, "hash": e.hash}
                    for e in self.pass1.annotated
                ],
            },
            "pass2": {
                "input_array":    self.pass2.input_array,
                "seed_used":      self.pass2.seed_used,
                "h_initial":      self.pass2.h_initial,
                "sorted_result":  self.pass2.sorted_result,
                "annotated": [
                    {"num": e.num, "hash": e.hash}
                    for e in self.pass2.annotated
                ],
            },
            "board": {
                "final_order":       self.board.final_order,
                "mine_positions_1b": self.board.mine_positions_1b,
                "mine_positions_0b": self.board.mine_positions_0b,
                "safe_positions":    self.board.safe_positions,
                "mine_count":        self.board.mine_count,
                "grid":              self.board.board_grid,
            },
            "commitment": (
                {
                    "server_seed":     self.commitment.server_seed,
                    "published_hash":  self.commitment.published_hash,
                    "computed_hash":   self.commitment.computed_hash,
                    "verified":        self.commitment.verified,
                    "detail":          self.commitment.match_detail,
                }
                if self.commitment else None
            ),
            "claimed_mines":   self.claimed_mines,
            "positions_match": self.positions_match,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Batch models
# ---------------------------------------------------------------------------

@dataclass
class BatchResult:
    """Aggregate result from a batch verification run."""
    total:      int
    passed:     int
    failed:     int
    errors:     int
    results:    list[AuditResult]
    timestamp:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp":  self.timestamp,
            "summary": {
                "total":     self.total,
                "passed":    self.passed,
                "failed":    self.failed,
                "errors":    self.errors,
                "pass_rate": f"{self.pass_rate:.1%}",
            },
            "results": [r.to_dict() for r in self.results],
        }
