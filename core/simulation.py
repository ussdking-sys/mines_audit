"""
core/simulation.py — Deterministic simulation engine.

Runs simulations using the exact BC.Game algorithm with either:
  - Fully deterministic inputs (known server seed + client seed + nonce)
  - Randomised inputs (generated server/client seeds + auto-incrementing nonce)

Every simulated board is derived using the same double-pass hash-rotation
algorithm as a real BC.Game round. No pseudo-random shortcuts.

DISCLAIMER:
  Simulations using randomised seeds do not correspond to any real BC.Game round.
  They are statistical experiments using the verified algorithm structure.
  They cannot predict future outcomes on the live platform.
"""

from __future__ import annotations

import secrets
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from core.crypto import derive_board, sha256_hex, hmac_sha256_hex
from core.models import AuditInput, AuditResult, BoardState
from core.auditor import Auditor
from data.reference_board import ALL_NUMS


# ---------------------------------------------------------------------------
# Seed generation utilities
# ---------------------------------------------------------------------------

def generate_server_seed() -> str:
    """Generate a cryptographically random server seed (64 hex chars)."""
    return secrets.token_hex(32)


def generate_client_seed(length: int = 16) -> str:
    """Generate a random client seed (32 hex chars by default)."""
    return secrets.token_hex(length)


def hash_server_seed(server_seed: str) -> str:
    """Return SHA256(server_seed) — the commitment hash."""
    return sha256_hex(server_seed)


# ---------------------------------------------------------------------------
# Single simulation result
# ---------------------------------------------------------------------------

@dataclass
class SimRound:
    """Result of one simulated round."""
    index:            int
    server_seed:      str
    server_seed_hash: str
    client_seed:      str
    nonce:            int
    mine_count:       int
    mine_positions:   list[int]     # 1-based
    final_order:      list[int]     # Full 25-element output
    mode:             str           # "DETERMINISTIC" or "RANDOMISED"
    label:            str           = ""

    @property
    def board_grid(self) -> list[list[str]]:
        mine_set = set(self.mine_positions)
        grid = []
        for row in range(5):
            grid.append([
                "MINE" if (row * 5 + col + 1) in mine_set else "SAFE"
                for col in range(5)
            ])
        return grid


@dataclass
class SimulationRun:
    """
    Results from a full simulation run (N rounds).
    Contains aggregate statistics and all individual round results.
    """
    mode:           str           # "DETERMINISTIC" or "RANDOMISED"
    mine_count:     int
    total_rounds:   int
    rounds:         list[SimRound] = field(default_factory=list)
    timestamp:      str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # --- Aggregate statistics (computed after run) ---
    mine_freq:      list[float]   = field(default_factory=lambda: [0.0] * 25)
    # mine_freq[i] = fraction of rounds where cell (i+1) was a mine

    position_counts: list[int]   = field(default_factory=lambda: [0] * 25)
    # How many times each cell (1-based index i+1) appeared as a mine

    first_mine_positions: list[int] = field(default_factory=list)
    # Position of first mine in final_order across all rounds

    def compute_stats(self) -> None:
        """Compute aggregate statistics from all rounds."""
        counts = [0] * 25
        first_mines = []

        for r in self.rounds:
            for pos in r.mine_positions:
                counts[pos - 1] += 1
            if r.mine_positions:
                first_mines.append(r.mine_positions[0])

        self.position_counts     = counts
        self.first_mine_positions = first_mines

        n = len(self.rounds)
        if n > 0:
            self.mine_freq = [c / n for c in counts]
        else:
            self.mine_freq = [0.0] * 25

    def to_dict(self) -> dict:
        return {
            "mode":        self.mode,
            "mine_count":  self.mine_count,
            "total_rounds": self.total_rounds,
            "timestamp":   self.timestamp,
            "stats": {
                "position_counts": self.position_counts,
                "mine_freq":       [round(f, 4) for f in self.mine_freq],
            },
            "rounds": [
                {
                    "index":         r.index,
                    "server_seed":   r.server_seed,
                    "client_seed":   r.client_seed,
                    "nonce":         r.nonce,
                    "mine_count":    r.mine_count,
                    "mine_positions": r.mine_positions,
                    "mode":          r.mode,
                }
                for r in self.rounds
            ],
        }


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Runs deterministic simulations using the exact BC.Game algorithm.

    Two modes:

    RANDOMISED:
        Generates fresh random server/client seeds for each round
        (or uses one fixed client seed with incrementing nonces).
        Useful for distribution analysis and statistical research.

    DETERMINISTIC:
        Uses a fixed server + client seed with incrementing nonces.
        Replicates exactly what would happen across consecutive bets
        with the same seed pair on BC.Game.
    """

    def __init__(self):
        self._auditor = Auditor()

    # ------------------------------------------------------------------
    # Randomised simulation
    # ------------------------------------------------------------------

    def run_randomised(
        self,
        mine_count:       int,
        num_rounds:       int,
        fixed_client_seed: Optional[str] = None,
        progress_cb:      Optional[callable] = None,
    ) -> SimulationRun:
        """
        Run N rounds with randomly generated seeds.

        Each round uses a fresh random server seed.
        Client seed is either fixed (provided) or freshly generated each round.
        Nonce resets to 0 for each new server seed.

        Args:
            mine_count:        Mines per board (1-24)
            num_rounds:        Number of rounds to simulate
            fixed_client_seed: If provided, reuse this client seed every round
            progress_cb:       Optional callback(current, total) for UI updates

        Returns:
            SimulationRun with all results and aggregate stats
        """
        run = SimulationRun(
            mode        = "RANDOMISED",
            mine_count  = mine_count,
            total_rounds = num_rounds,
        )

        for i in range(num_rounds):
            if progress_cb and i % max(1, num_rounds // 20) == 0:
                progress_cb(i, num_rounds)

            server_seed  = generate_server_seed()
            client_seed  = fixed_client_seed or generate_client_seed()
            nonce        = 0

            _, _, _, board = derive_board(
                server_seed  = server_seed,
                client_seed  = client_seed,
                nonce        = nonce,
                mine_count   = mine_count,
                all_nums     = ALL_NUMS,
            )

            run.rounds.append(SimRound(
                index            = i + 1,
                server_seed      = server_seed,
                server_seed_hash = hash_server_seed(server_seed),
                client_seed      = client_seed,
                nonce            = nonce,
                mine_count       = mine_count,
                mine_positions   = board.mine_positions_1b,
                final_order      = board.final_order,
                mode             = "RANDOMISED",
            ))

        run.compute_stats()
        return run

    # ------------------------------------------------------------------
    # Deterministic simulation (fixed seeds, incrementing nonce)
    # ------------------------------------------------------------------

    def run_deterministic(
        self,
        mine_count:   int,
        num_rounds:   int,
        server_seed:  Optional[str] = None,
        client_seed:  Optional[str] = None,
        start_nonce:  int           = 0,
        progress_cb:  Optional[callable] = None,
    ) -> SimulationRun:
        """
        Run N rounds using fixed seeds with incrementing nonces.

        This replicates what BC.Game does across consecutive bets
        with the same seed pair. Nonce starts at start_nonce and
        increments by 1 for each subsequent round.

        If seeds are not provided, generates them randomly once
        (then keeps them fixed for all N rounds).

        Args:
            mine_count:   Mines per board
            num_rounds:   Number of rounds to simulate
            server_seed:  Fixed server seed (generated if None)
            client_seed:  Fixed client seed (generated if None)
            start_nonce:  Starting nonce value (default 0, BC.Game style)
            progress_cb:  Optional progress callback

        Returns:
            SimulationRun with all results and aggregate stats
        """
        # Generate seeds if not provided
        server_seed = server_seed or generate_server_seed()
        client_seed = client_seed or generate_client_seed()

        run = SimulationRun(
            mode        = "DETERMINISTIC",
            mine_count  = mine_count,
            total_rounds = num_rounds,
        )

        for i in range(num_rounds):
            if progress_cb and i % max(1, num_rounds // 20) == 0:
                progress_cb(i, num_rounds)

            nonce = start_nonce + i

            _, _, _, board = derive_board(
                server_seed  = server_seed,
                client_seed  = client_seed,
                nonce        = nonce,
                mine_count   = mine_count,
                all_nums     = ALL_NUMS,
            )

            run.rounds.append(SimRound(
                index            = i + 1,
                server_seed      = server_seed,
                server_seed_hash = hash_server_seed(server_seed),
                client_seed      = client_seed,
                nonce            = nonce,
                mine_count       = mine_count,
                mine_positions   = board.mine_positions_1b,
                final_order      = board.final_order,
                mode             = "DETERMINISTIC",
                label            = f"nonce-{nonce}",
            ))

        run.compute_stats()
        return run

    # ------------------------------------------------------------------
    # Quick single-round with random seeds
    # ------------------------------------------------------------------

    def quick_random_round(self, mine_count: int) -> SimRound:
        """
        Generate one round with freshly randomised seeds.
        Useful for the 'quick board' menu option.
        """
        server_seed  = generate_server_seed()
        client_seed  = generate_client_seed()
        nonce        = 0

        _, _, _, board = derive_board(
            server_seed  = server_seed,
            client_seed  = client_seed,
            nonce        = nonce,
            mine_count   = mine_count,
            all_nums     = ALL_NUMS,
        )

        return SimRound(
            index            = 1,
            server_seed      = server_seed,
            server_seed_hash = hash_server_seed(server_seed),
            client_seed      = client_seed,
            nonce            = nonce,
            mine_count       = mine_count,
            mine_positions   = board.mine_positions_1b,
            final_order      = board.final_order,
            mode             = "RANDOMISED",
        )

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    @staticmethod
    def hottest_cells(run: SimulationRun, n: int = 5) -> list[tuple[int, float]]:
        """Return the N cells that appeared as mines most frequently."""
        indexed = [(i + 1, run.mine_freq[i]) for i in range(25)]
        return sorted(indexed, key=lambda x: -x[1])[:n]

    @staticmethod
    def coldest_cells(run: SimulationRun, n: int = 5) -> list[tuple[int, float]]:
        """Return the N cells that appeared as mines least frequently."""
        indexed = [(i + 1, run.mine_freq[i]) for i in range(25)]
        return sorted(indexed, key=lambda x: x[1])[:n]

    @staticmethod
    def first_position_distribution(run: SimulationRun) -> dict[int, float]:
        """
        Distribution of which cell position appeared first (index 0)
        in final_order across all rounds. Useful for bias analysis.
        """
        from collections import Counter
        counts = Counter(r.final_order[0] for r in run.rounds if r.final_order)
        total  = len(run.rounds)
        return {pos: count / total for pos, count in sorted(counts.items())}
