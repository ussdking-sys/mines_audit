# Architecture — bc-mines-lab-v1.0

## Repository Structure

```
bc-mines-lab-v1.0/
│
├── core/
│   ├── auditor.py      High-level orchestrator (primary API)
│   ├── crypto.py       Exact BC.Game cryptographic primitives
│   ├── models.py       All typed dataclasses (input/output/intermediate)
│   ├── renderer.py     Rich terminal rendering
│   └── report.py       JSON + Markdown report generation
│
├── data/
│   └── reference_board.py   ALL_NUMS array + validation
│
├── examples/
│   ├── sample_round.json    Single round template
│   └── sample_batch.json    Batch audit template
│
├── reports/                 Auto-created; stores exported reports
│
├── tests/
│   ├── test_algorithm.py    Core algorithm correctness tests
│   └── test_commitment.py   Commitment + replay tests
│
├── docs/
│   ├── algorithm.md         Exact BC.Game algorithm walkthrough
│   ├── provably_fair.md     Concepts + user guide
│   ├── architecture.md      This file
│   └── replay_mode.md       Replay usage guide
│
├── main.py             CLI entry point
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Data Flow

```
User Input (CLI args / JSON file)
        │
        ▼
  AuditInput (models.py)
        │
        ▼
  Auditor.audit() (auditor.py)
        │
        ├──► derive_board() (crypto.py)
        │         │
        │         ├── hmac_sha256_hex()
        │         ├── create_nums() × 2  ← double pass
        │         │     ├── sha256_hex()
        │         │     ├── rotate_left() × 25
        │         │     └── sorted() descending
        │         └── BoardState
        │
        ├──► verify_commitment() (crypto.py)  [if hash provided]
        │
        └──► compare_positions()  [if claimed mines provided]
                │
                ▼
          AuditResult (models.py)
                │
                ├──► render_full_audit() (renderer.py) → terminal
                └──► export_json() / export_markdown() (report.py) → files
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `crypto.py` | Pure cryptographic functions; no I/O; fully testable |
| `models.py` | Data containers; no business logic; serialisable |
| `auditor.py` | Orchestration; combines crypto + models; primary API |
| `renderer.py` | Display only; no logic; depends on models |
| `report.py` | File I/O; serialisation; depends on models |
| `main.py` | CLI parsing; wires everything together |
| `data/reference_board.py` | Configuration data; separated for easy update |
