# bc-mines-lab-v1.1

**BC.Game Mines Provably Fair Audit Framework**

A deterministic cryptographic auditing toolkit for verifying BC.Game Mines
provably fair round outcomes. For educational, research, and auditing use only.

> **[BC.GAME MINES — GAME LINK: TO BE UPDATED]**

---

## ⚠ Disclaimer

> This tool is strictly for **educational and auditing purposes**.
> It does NOT predict future game outcomes, automate bets, interact with
> any account, or provide any gambling advantage.
>
> Provably fair verification is a *post-game* operation. Without the revealed
> server seed (only available after seed rotation), outcomes cannot be derived.
> This tool cannot tell you where mines are in an active, unplayed round.

---

## What This Does

- **Verifies** that a revealed server seed matches its pre-published hash
- **Derives** the exact board BC.Game would generate from known seeds
- **Compares** derived mine positions against claimed positions
- **Exports** full audit reports in JSON and Markdown
- **Replays** historical rounds from saved JSON files
- **Batch-audits** multiple rounds from a CSV/JSON list
- **Simulates** boards with the exact algorithm to study distribution (menu: Simulation Lab)

---

## What This Does NOT Do

- Predict mine positions in active rounds
- Automate any gameplay or betting
- Interact with BC.Game's servers
- Guarantee any financial outcome

---

## Algorithm

BC.Game Mines uses a two-pass hash-rotation shuffle:

```
hash = HMAC_SHA256(key=serverSeed, message=f"{clientSeed}:{nonce}")

Pass 1: createNums(ALL_NUMS, hash)
  → h = SHA256(hash)
  → For each position: annotate with h, rotate h left by 1 char
  → Sort descending by hash string

Pass 2: createNums(pass1_output, SHA256(hash))
  → Same process, using pass 1 output as input array

Mine positions = first N values of final array (N = mine count)
```

See [`docs/algorithm.md`](docs/algorithm.md) for full details.

---

## Installation

```bash
# Clone
git clone <repo-url>
cd bc-mines-lab-v1.1

# Install
pip install -r requirements.txt

# Termux (Android)
pip install -r requirements.txt --break-system-packages

# Verify
python main.py info
```

---

## Interactive Menu

Run with **no arguments** to launch the interactive terminal UI:

```bash
python main.py
```

Menu options:

| # | Option | Description |
|---|--------|-------------|
| 1 | Single Round Audit | Audit one round (manual entry, randomised seeds, or load from JSON) |
| 2 | Commitment Verifier | Check `SHA256(serverSeed)` matches a published hash |
| 3 | Batch Audit | Verify multiple rounds from a JSON array file |
| 4 | Simulation Lab | Run boards with the exact algorithm (random / deterministic / nonce sweep) |
| 5 | Seed Tools | Generate seeds, hash strings, preview boards, inspect `ALL_NUMS` |
| 6 | System Info | Reference-board status and environment details |
| Q | Quit | Exit |

---

## CLI Usage

All operations are also available non-interactively as subcommands.
Subcommands exit `0` on success, `1` on a verification failure
(bad commitment or mismatched positions), and `2` on a bad/missing input file.

### Audit a single round

```bash
python main.py audit \
  --server-seed      "your_revealed_server_seed" \
  --server-seed-hash "the_published_sha256_hash" \
  --client-seed      "your_client_seed" \
  --nonce            0 \
  --mines            3
```

With position comparison and JSON export:
```bash
python main.py audit \
  --server-seed      "abc123..." \
  --server-seed-hash "def456..." \
  --client-seed      "ghi789..." \
  --nonce            0 \
  --mines            3 \
  --claimed-mines    "7,14,21" \
  --export           reports/myround.json \
  --export-md        reports/myround.md
```

### Verify commitment only

```bash
python main.py verify \
  --server-seed      "revealed_seed" \
  --server-seed-hash "published_hash"
```

### Replay from JSON file

```bash
python main.py replay examples/sample_round.json
python main.py replay myround.json --export reports/result.json
```

### Batch audit

```bash
python main.py batch examples/sample_batch.json
python main.py batch myrounds.json --export-md reports/batch_summary.md
```

### Show detailed shuffle passes

```bash
python main.py audit ... --show-passes
```

### System info

```bash
python main.py info
```

---

## Round JSON Format

```json
{
  "serverSeed":     "your_revealed_server_seed",
  "serverSeedHash": "sha256_of_server_seed",
  "clientSeed":     "your_client_seed",
  "nonce":          0,
  "mines":          3,
  "claimedMines":   [7, 14, 21],
  "label":          "my-round-label"
}
```

- `serverSeedHash` — optional; enables commitment verification
- `claimedMines` — optional; enables position comparison (1-based, 1-25)
- `label` — optional; used in reports

---

## How to Get Your Seeds from BC.Game

1. Go to `bc.game/game/mines`
2. Open the **Seed Setting** panel
3. Note your **Client Seed** and **Nonce**
4. The **Server Seed Hash** is shown as "Server Seed (hash)"
5. To get the actual server seed: **rotate your seeds**
   - The previous server seed is then revealed in your history
6. Use the revealed seed + the hash that was shown before rotation

---

## Running Tests

```bash
pytest
pytest -v                    # verbose
pytest tests/test_algorithm.py  # single file
pytest --tb=short            # compact output
```

---

## Project Structure

```
bc-mines-lab-v1.1/
├── core/
│   ├── auditor.py       High-level audit orchestrator
│   ├── crypto.py        Exact BC.Game algorithm
│   ├── models.py        Typed data structures
│   ├── simulation.py    Simulation engine + seed generation
│   ├── renderer.py      Terminal display
│   └── report.py        JSON + Markdown export
├── data/
│   └── reference_board.py   ALL_NUMS array
├── examples/            Sample round and batch files
├── reports/             Generated reports (auto-created)
├── tests/               pytest test suite
├── docs/                Full documentation
├── main.py              Interactive menu + CLI entry point
└── requirements.txt
```

---

## Reference Board Status

The `ALL_NUMS` array (BC.Game's fixed reference positions) was observed from
`bc.game/help/provably-fair`. **The last 6 values are unconfirmed** — see
`data/reference_board.py` for details and update instructions.

Run `python main.py info` to check current verification status.

---

## Roadmap

- [ ] Confirm and verify complete ALL_NUMS array
- [ ] Add entropy analysis utilities
- [ ] Add nonce progression inspector
- [ ] Add SHA chain visualiser
- [ ] Add audit diff mode (compare two rounds)
- [ ] Add board distribution statistics over batch runs

---

## License

MIT License. See `LICENSE`.

Educational use only. No warranty. No gambling advice.
