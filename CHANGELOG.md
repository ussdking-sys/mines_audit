# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.1.0] — 2026-06-03

### Added
- Non-interactive CLI subcommands (`audit`, `verify`, `replay`, `batch`, `info`) so all
  commands documented in the README work without a TTY
- `audit` subcommand: accepts `--server-seed`, `--server-seed-hash`, `--client-seed`,
  `--nonce`, `--mines`, `--claimed-mines`, `--export`, `--export-md`, `--show-passes`
- `verify` subcommand: commitment-only check (`SHA256(serverSeed) == publishedHash`)
- `replay <file>` subcommand: audit a single round from a saved JSON file
- `batch <file>` subcommand: batch-audit a JSON array of rounds
- `info` subcommand: prints system info and reference-board status then exits
- Meaningful CLI exit codes: `0` success · `1` verification failure · `2` bad/missing file
- `simulation.py` — simulation engine and seed generation utilities (Simulation Lab menu)
- Interactive menu options: Simulation Lab (random, deterministic, nonce-sequence runs)
  and Seed Tools (generate seeds, SHA256 calculator, board preview, ALL_NUMS inspector)

### Changed
- `main.py` no-args behaviour unchanged — still launches the interactive Rich menu;
  subcommands are dispatched only when arguments are provided
- Version bumped to `1.1.0` in `pyproject.toml`
- Markdown report generator footer updated from `v1.0` to `v1.1`

### Fixed
- README version header corrected from `v1.0` to `v1.1`
- README project-structure tree updated to include `simulation.py`
- Removed stale placeholder line `[BC.GAME MINES — GAME LINK: TO BE UPDATED]`
- Removed empty `{core,data,reports,examples,tests,docs}` directory (packaging artefact
  caused by failed shell brace expansion during archive creation)

---

## [1.0.0] — 2025-05-13

### Added
- Initial release of the BC.Game Mines Provably Fair Audit Framework
- `core/crypto.py` — exact BC.Game double-pass hash-rotation shuffle algorithm
- `core/auditor.py` — high-level audit orchestrator (`Auditor` class)
- `core/models.py` — typed dataclasses (`AuditInput`, `AuditResult`, `BatchResult`, etc.)
- `core/renderer.py` — Rich terminal display (board grid, crypto chain, batch summary)
- `core/report.py` — JSON and Markdown report export
- `data/reference_board.py` — `ALL_NUMS` reference array (last 6 values unconfirmed)
- `docs/` — algorithm, architecture, and provably-fair documentation
- `examples/` — sample round and batch JSON files
- `tests/` — 73 pytest tests covering algorithm, commitment, and replay
- Interactive terminal menu (`main.py`) with Single Round Audit, Commitment Verifier,
  and Batch Audit
