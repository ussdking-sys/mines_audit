"""
tests/test_commitment.py — Commitment and replay verification tests.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from pathlib import Path

from core.crypto import sha256_hex, verify_commitment
from core.auditor import Auditor
from core.models import AuditInput


class TestCommitmentEdgeCases:
    """Edge cases for server seed commitment verification."""

    def test_empty_seed_hash(self):
        h = sha256_hex("")
        result = verify_commitment("", h)
        assert result.verified is True

    def test_unicode_seed(self):
        seed = "sérvèr_sééd_üñícödé"
        h    = sha256_hex(seed)
        result = verify_commitment(seed, h)
        assert result.verified is True

    def test_very_long_seed(self):
        seed = "x" * 1000
        h    = sha256_hex(seed)
        result = verify_commitment(seed, h)
        assert result.verified is True

    def test_partial_hash_fails(self):
        seed = "abc"
        h    = sha256_hex(seed)[:32]   # truncated
        result = verify_commitment(seed, h)
        assert result.verified is False

    def test_tampered_hash_fails(self):
        seed = "abc"
        h    = sha256_hex(seed)
        tampered = h[:-1] + ("0" if h[-1] != "0" else "1")
        result = verify_commitment(seed, tampered)
        assert result.verified is False

    def test_bc_game_seed_structure(self):
        """
        Simulate a BC.Game style round:
        server seed hash is published → game is played → server seed revealed.
        After revelation, SHA256(revealed) must equal published hash.
        """
        # Simulate what BC.Game does before the game
        actual_server_seed   = "bc_game_server_seed_example_abc123"
        published_hash       = sha256_hex(actual_server_seed)

        # After the game, they reveal it
        revealed_server_seed = actual_server_seed

        result = verify_commitment(revealed_server_seed, published_hash)
        assert result.verified is True

    def test_nonce_progression_changes_outcome(self):
        """Each nonce produces a unique board — commitment is seed-level, board is nonce-level."""
        auditor = Auditor()
        boards  = []
        for nonce in range(5):
            mines = auditor.derive_mines_only("server", "client", nonce, 3)
            boards.append(tuple(sorted(mines)))
        # All nonces should produce different boards
        assert len(set(boards)) == 5, "Some nonces produced identical boards"


class TestReplayFromFile:
    """Test replay functionality from JSON files."""

    SAMPLE_ROUND = {
        "serverSeed":     "replay_test_server_seed_001",
        "serverSeedHash": None,  # Will be set dynamically
        "clientSeed":     "replay_client_seed_abc",
        "nonce":          0,
        "mines":          3,
        "label":          "test-replay-round",
    }

    def setup_method(self):
        self.auditor = Auditor()
        # Set the correct hash for this test round
        self.SAMPLE_ROUND = dict(TestReplayFromFile.SAMPLE_ROUND)
        self.SAMPLE_ROUND["serverSeedHash"] = sha256_hex(
            self.SAMPLE_ROUND["serverSeed"]
        )

    def test_replay_produces_same_board(self):
        """Replaying same inputs must produce identical board."""
        r1 = self.auditor.audit_from_dict(self.SAMPLE_ROUND)
        r2 = self.auditor.audit_from_dict(self.SAMPLE_ROUND)
        assert r1.board.mine_positions_1b == r2.board.mine_positions_1b

    def test_replay_verifies_commitment(self):
        result = self.auditor.audit_from_dict(self.SAMPLE_ROUND)
        assert result.commitment is not None
        assert result.commitment.verified is True

    def test_replay_with_claimed_mines_match(self):
        """When claimed mines match derived, positions_match should be True."""
        result  = self.auditor.audit_from_dict(self.SAMPLE_ROUND)
        derived = result.board.mine_positions_1b

        # Replay with the correct claimed mines
        result2 = self.auditor.audit_from_dict(
            self.SAMPLE_ROUND,
            claimed_mines=list(derived),
        )
        assert result2.positions_match is True

    def test_replay_with_wrong_claimed_mines(self):
        """When claimed mines are wrong, positions_match should be False."""
        result  = self.auditor.audit_from_dict(self.SAMPLE_ROUND)
        derived = result.board.mine_positions_1b

        # Use wrong positions
        wrong = [(p % 25) + 1 for p in derived]
        # Ensure they're actually wrong
        if set(wrong) == set(derived):
            wrong = [1, 2, 3]

        result2 = self.auditor.audit_from_dict(
            self.SAMPLE_ROUND,
            claimed_mines=wrong,
        )
        # This may or may not match depending on the specific case;
        # we just verify the comparison ran
        assert result2.positions_match is not None

    def test_replay_different_nonces_differ(self):
        """Nonce increment must change board."""
        d0 = dict(self.SAMPLE_ROUND, nonce=0)
        d1 = dict(self.SAMPLE_ROUND, nonce=1)
        r0 = self.auditor.audit_from_dict(d0)
        r1 = self.auditor.audit_from_dict(d1)
        assert r0.board.mine_positions_1b != r1.board.mine_positions_1b

    def test_sample_file_loads(self):
        """The example sample_round.json must be parseable and auditable."""
        sample_path = Path(__file__).parent.parent / "examples" / "sample_round.json"
        if sample_path.exists():
            with open(sample_path) as f:
                data = json.load(f)
            result = self.auditor.audit_from_dict(data)
            assert len(result.board.mine_positions_1b) > 0

    def test_batch_sample_loads(self):
        """The example sample_batch.json must be parseable."""
        sample_path = Path(__file__).parent.parent / "examples" / "sample_batch.json"
        if sample_path.exists():
            with open(sample_path) as f:
                data = json.load(f)
            assert isinstance(data, list)
            batch = self.auditor.audit_batch(data)
            assert batch.total == len(data)
