#!/usr/bin/env python3
"""
main.py — BC.Game Mines Provably Fair Audit Framework v1.1
Interactive terminal menu interface.

DISCLAIMER:
  This tool is for educational and auditing purposes only.
  It does NOT predict outcomes, automate bets, or guarantee any advantage.
  Simulations use the verified BC.Game algorithm structure but do not
  correspond to any real live round.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.prompt import Prompt, Confirm
from rich import box

from core.auditor import Auditor
from core.models import AuditInput
from core.simulation import (
    SimulationEngine, SimulationRun, SimRound,
    generate_server_seed, generate_client_seed, hash_server_seed,
)
from core.renderer import render_full_audit, render_batch_summary
from core.report import export_json, export_markdown, export_batch_markdown
from data.reference_board import VALIDATION as REF_VALIDATION, ALL_NUMS

console = Console()
auditor = Auditor()
sim_eng = SimulationEngine()

DISCLAIMER = (
    "[bold red]WARNING[/bold red]  "
    "[dim]Educational/auditing use only. Does NOT predict outcomes "
    "or automate bets. Post-game verification only.[/dim]"
)

BANNER = """[bold cyan]
 ██████╗  ██████╗    ███╗   ███╗██╗███╗   ██╗███████╗███████╗
 ██╔══██╗██╔════╝    ████╗ ████║██║████╗  ██║██╔════╝██╔════╝
 ██████╔╝██║         ██╔████╔██║██║██╔██╗ ██║█████╗  ███████╗
 ██╔══██╗██║         ██║╚██╔╝██║██║██║╚██╗██║██╔══╝  ╚════██║
 ██████╔╝╚██████╗    ██║ ╚═╝ ██║██║██║ ╚████║███████╗███████║
 ╚═════╝  ╚═════╝    ╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
[/bold cyan][dim cyan] BC.Game Mines  Provably Fair Audit Framework  v1.1[/dim cyan]"""

VALID_MINE_COUNTS = [1, 3, 5, 7]

# ---------------------------------------------------------------------------
# Low-level UI helpers
# ---------------------------------------------------------------------------

def clear():
    console.clear()

def header(title, subtitle=""):
    sub = f"\n[dim]{subtitle}[/dim]" if subtitle else ""
    console.print(Panel(
        f"[bold cyan]{title}[/bold cyan]{sub}",
        border_style="cyan dim", padding=(0, 2),
    ))

def print_menu(options):
    console.print()
    for key, label in options.items():
        key_col = "bold cyan" if key not in ("B", "Q") else "dim"
        console.print(f"  [{key_col}][{key}][/{key_col}]  {label}")
    console.print()

def prompt_choice(valid):
    while True:
        raw = Prompt.ask("  Choice").strip().upper()
        if raw in [v.upper() for v in valid]:
            return raw.upper()
        console.print(f"  [red]Invalid. Options: {', '.join(valid)}[/red]")

def prompt_int(label, lo, hi, default=None):
    default_str = str(default) if default is not None else None
    while True:
        raw = Prompt.ask(f"  {label} ({lo}-{hi})", default=default_str)
        if raw and raw.isdigit() and lo <= int(raw) <= hi:
            return int(raw)
        console.print(f"  [red]Enter an integer between {lo} and {hi}.[/red]")

def prompt_str(label, default=""):
    return Prompt.ask(f"  {label}", default=default).strip()

def pause():
    console.print("\n  [dim]Press Enter to continue...[/dim]", end="")
    input()

def progress_bar(value, width=24):
    filled = int(round(value * width))
    return "█" * filled + "░" * (width - filled)

def mine_colour(count):
    return {1: "green", 3: "yellow", 5: "orange1", 7: "red"}.get(count, "white")

def prompt_mine_count():
    console.print("\n  [cyan]Mine count (1/3/5/7):[/cyan]")
    for tc in VALID_MINE_COUNTS:
        col = mine_colour(tc)
        console.print(f"    [{col}]{tc}[/{col}]  mines")
    while True:
        raw = Prompt.ask("  Select", default="3")
        if raw.isdigit() and int(raw) in VALID_MINE_COUNTS:
            return int(raw)
        console.print(f"  [red]Must be one of {VALID_MINE_COUNTS}[/red]")

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def collect_seeds_manual():
    console.print("\n  [dim]Press Enter on any field to auto-generate.[/dim]\n")
    server_seed = prompt_str("Server seed (revealed post-game)")
    if not server_seed:
        server_seed = generate_server_seed()
        console.print(f"  [dim]Generated: {server_seed}[/dim]")
    server_seed_hash = prompt_str("Server seed hash (optional)") or None
    client_seed = prompt_str("Client seed")
    if not client_seed:
        client_seed = generate_client_seed()
        console.print(f"  [dim]Generated: {client_seed}[/dim]")
    nonce_str = prompt_str("Nonce", "0")
    nonce = int(nonce_str) if nonce_str.isdigit() else 0
    return server_seed, server_seed_hash, client_seed, nonce

def collect_seeds_randomised():
    server_seed      = generate_server_seed()
    server_seed_hash = hash_server_seed(server_seed)
    client_seed      = generate_client_seed()
    return server_seed, server_seed_hash, client_seed, 0

def show_seeds_panel(server_seed, server_seed_hash, client_seed, nonce, mode="MANUAL"):
    col = "green" if mode == "DETERMINISTIC" else ("yellow" if mode == "MANUAL" else "cyan")
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="dim", width=22)
    table.add_column("Value", width=60)
    table.add_row("Mode",             f"[{col}]{mode}[/{col}]")
    table.add_row("Server Seed",      f"[dim]{server_seed}[/dim]")
    table.add_row("Server Seed Hash", f"[dim]{server_seed_hash or '(not provided)'}[/dim]")
    table.add_row("Client Seed",      f"[dim]{client_seed}[/dim]")
    table.add_row("Nonce",            str(nonce))
    console.print(Panel(table, title="[bold]SEEDS[/bold]", border_style="cyan dim"))

# ---------------------------------------------------------------------------
# MENU 1 — SINGLE ROUND AUDIT
# ---------------------------------------------------------------------------

def menu_audit():
    while True:
        clear()
        header("SINGLE ROUND AUDIT", "Verify one round using the BC.Game algorithm")
        console.print(f"  {DISCLAIMER}\n")
        options = {
            "1": "Manual seed entry",
            "2": "Randomise all seeds",
            "3": "Load from JSON file",
            "B": "Back",
        }
        print_menu(options)
        choice = prompt_choice(list(options.keys()))
        if choice == "B":
            return
        elif choice == "1":
            _audit_manual()
        elif choice == "2":
            _audit_randomised()
        elif choice == "3":
            _audit_from_file()

def _audit_manual():
    clear()
    header("MANUAL AUDIT")
    server_seed, server_seed_hash, client_seed, nonce = collect_seeds_manual()
    mine_count = prompt_mine_count()
    claimed_str = prompt_str("Claimed mine positions (comma-separated 1-25, optional)")
    claimed_mines = None
    if claimed_str:
        try:
            claimed_mines = [int(x.strip()) for x in claimed_str.split(",") if x.strip()]
        except ValueError:
            pass
    show_seeds_panel(server_seed, server_seed_hash, client_seed, nonce, "MANUAL")
    console.print("  [cyan]Running audit...[/cyan]")
    time.sleep(0.3)
    inp    = AuditInput(server_seed=server_seed, client_seed=client_seed,
                        nonce=nonce, mine_count=mine_count, server_seed_hash=server_seed_hash)
    result = auditor.audit(inp, claimed_mines=claimed_mines)
    render_full_audit(result, show_chain=True, show_passes=False, show_board=True)
    _offer_export(result)
    pause()

def _audit_randomised():
    clear()
    header("RANDOMISED SEED AUDIT")
    console.print(
        "  [dim]Random seeds are generated. This produces a valid deterministic\n"
        "  board but does NOT correspond to any real BC.Game round.[/dim]\n"
    )
    mine_count = prompt_mine_count()
    server_seed, server_seed_hash, client_seed, nonce = collect_seeds_randomised()
    show_seeds_panel(server_seed, server_seed_hash, client_seed, nonce, "RANDOMISED")
    console.print("  [cyan]Generating board...[/cyan]")
    time.sleep(0.3)
    inp    = AuditInput(server_seed=server_seed, client_seed=client_seed,
                        nonce=nonce, mine_count=mine_count, server_seed_hash=server_seed_hash)
    result = auditor.audit(inp)
    render_full_audit(result, show_chain=True, show_passes=False, show_board=True)
    _offer_export(result)
    pause()

def _audit_from_file():
    clear()
    header("AUDIT FROM FILE")
    file_path = prompt_str("Path to JSON file", "examples/sample_round.json")
    p = Path(file_path)
    if not p.exists():
        console.print(f"  [red]File not found: {p}[/red]")
        pause()
        return
    with open(p) as f:
        data = json.load(f)
    claimed = data.get("claimedMines") or data.get("claimed_mines")
    result  = auditor.audit_from_dict(data, claimed_mines=claimed)
    render_full_audit(result, show_chain=True, show_board=True)
    _offer_export(result)
    pause()

# ---------------------------------------------------------------------------
# MENU 2 — COMMITMENT VERIFIER
# ---------------------------------------------------------------------------

def menu_verify():
    clear()
    header("COMMITMENT VERIFIER", "Check SHA256(serverSeed) matches published hash")
    server_seed = prompt_str("Revealed server seed")
    if not server_seed:
        console.print("  [red]Server seed required.[/red]")
        pause()
        return
    published_hash = prompt_str("Published server seed hash")
    if not published_hash:
        console.print("  [red]Published hash required.[/red]")
        pause()
        return
    from core.crypto import verify_commitment
    result = verify_commitment(server_seed, published_hash)
    ok  = result.verified
    col = "green" if ok else "red"
    console.print(Panel(
        f"  [{col}]{'VERIFIED' if ok else 'FAILED'}[/{col}]\n\n"
        f"  Server Seed:    [dim]{result.server_seed[:48]}...[/dim]\n"
        f"  Published Hash: [dim]{result.published_hash}[/dim]\n"
        f"  Computed Hash:  [{col}]{result.computed_hash}[/{col}]\n\n"
        f"  [dim]{result.match_detail}[/dim]",
        title=f"[bold]COMMITMENT {'VERIFIED' if ok else 'FAILED'}[/bold]",
        border_style=col, padding=(1, 2),
    ))
    pause()

# ---------------------------------------------------------------------------
# MENU 3 — BATCH AUDIT
# ---------------------------------------------------------------------------

def menu_batch():
    clear()
    header("BATCH AUDIT", "Verify multiple rounds from a JSON array")
    file_path = prompt_str("Path to batch JSON file", "examples/sample_batch.json")
    p = Path(file_path)
    if not p.exists():
        console.print(f"  [red]File not found: {p}[/red]")
        pause()
        return
    with open(p) as f:
        data = json.load(f)
    if not isinstance(data, list):
        console.print("  [red]File must be a JSON array.[/red]")
        pause()
        return
    console.print(f"  [cyan]Auditing {len(data)} rounds...[/cyan]\n")
    time.sleep(0.3)
    batch = auditor.audit_batch(data)
    render_batch_summary(batch)
    if Confirm.ask("  Export JSON?", default=False):
        console.print(f"  [green]Saved -> {export_json(batch)}[/green]")
    if Confirm.ask("  Export Markdown?", default=False):
        console.print(f"  [green]Saved -> {export_batch_markdown(batch)}[/green]")
    pause()

# ---------------------------------------------------------------------------
# MENU 4 — SIMULATION LAB
# ---------------------------------------------------------------------------

def menu_simulation():
    while True:
        clear()
        header("SIMULATION LAB", "Run boards using the exact BC.Game algorithm")
        console.print(f"  {DISCLAIMER}\n")
        console.print("  [dim]All simulations use the verified double-pass algorithm.\n"
                      "  Random-seed runs do not correspond to real platform rounds.[/dim]\n")
        options = {
            "1": "Quick random board    (1 round, random seeds)",
            "2": "Randomised run        (N rounds, new seeds each round)",
            "3": "Deterministic run     (N rounds, fixed seeds + nonce sequence)",
            "4": "Nonce sequence viewer (fixed seeds, N consecutive nonces)",
            "B": "Back",
        }
        print_menu(options)
        choice = prompt_choice(list(options.keys()))
        if choice == "B":
            return
        elif choice == "1": _sim_quick_random()
        elif choice == "2": _sim_randomised_run()
        elif choice == "3": _sim_deterministic_run()
        elif choice == "4": _sim_nonce_sequence()

def _sim_quick_random():
    clear()
    header("QUICK RANDOM BOARD")
    mine_count = prompt_mine_count()
    console.print("  [cyan]Generating...[/cyan]")
    time.sleep(0.2)
    sim = sim_eng.quick_random_round(mine_count)
    _render_sim_round(sim, show_seeds=True)
    pause()

def _sim_randomised_run():
    clear()
    header("RANDOMISED SIMULATION RUN")
    console.print(f"  {DISCLAIMER}\n")
    mine_count = prompt_mine_count()
    num_rounds = prompt_int("Number of rounds", 1, 10000, default=100)
    fix_client = Confirm.ask("  Fix one client seed for all rounds?", default=False)
    client_seed = generate_client_seed() if fix_client else None
    if fix_client:
        console.print(f"  [dim]Client seed: {client_seed}[/dim]")
    console.print(f"\n  [cyan]Running {num_rounds} randomised rounds...[/cyan]")

    def prog(cur, tot):
        pct = cur / tot
        console.print(f"  [cyan]{progress_bar(pct)}[/cyan] {cur}/{tot}", end="\r")

    run = sim_eng.run_randomised(mine_count=mine_count, num_rounds=num_rounds,
                                  fixed_client_seed=client_seed, progress_cb=prog)
    console.print()
    _render_sim_run_summary(run)
    if num_rounds <= 10 and Confirm.ask("  Show individual boards?", default=True):
        for r in run.rounds:
            _render_sim_round(r, show_seeds=(num_rounds <= 5))
    _offer_sim_export(run)
    pause()

def _sim_deterministic_run():
    clear()
    header("DETERMINISTIC SIMULATION RUN")
    console.print(
        "  [dim]Fixed seeds, incrementing nonce — exactly how BC.Game\n"
        "  processes consecutive bets with the same seed pair.[/dim]\n"
    )
    mine_count = prompt_mine_count()
    num_rounds = prompt_int("Number of rounds", 1, 10000, default=50)
    use_random = Confirm.ask("  Randomise seeds?", default=True)
    if use_random:
        server_seed = generate_server_seed()
        client_seed = generate_client_seed()
        console.print(f"  [dim]Server: {server_seed[:32]}...[/dim]")
        console.print(f"  [dim]Client: {client_seed}[/dim]")
    else:
        server_seed = prompt_str("Server seed") or generate_server_seed()
        client_seed = prompt_str("Client seed") or generate_client_seed()
    start_nonce = prompt_int("Start nonce", 0, 9999, default=0)
    console.print(f"\n  [cyan]Running {num_rounds} deterministic rounds...[/cyan]")

    def prog(cur, tot):
        pct = cur / tot
        console.print(f"  [cyan]{progress_bar(pct)}[/cyan] {cur}/{tot}", end="\r")

    run = sim_eng.run_deterministic(mine_count=mine_count, num_rounds=num_rounds,
                                     server_seed=server_seed, client_seed=client_seed,
                                     start_nonce=start_nonce, progress_cb=prog)
    console.print()
    _render_sim_run_summary(run)
    if num_rounds <= 10 and Confirm.ask("  Show individual boards?", default=True):
        for r in run.rounds:
            _render_sim_round(r, show_seeds=True)
    _offer_sim_export(run)
    pause()

def _sim_nonce_sequence():
    clear()
    header("NONCE SEQUENCE VIEWER")
    console.print("  [dim]View how boards change across consecutive nonces.[/dim]\n")
    mine_count  = prompt_mine_count()
    num_nonces  = prompt_int("Number of nonces to display", 1, 25, default=5)
    use_random  = Confirm.ask("  Randomise seeds?", default=True)
    if use_random:
        server_seed = generate_server_seed()
        client_seed = generate_client_seed()
    else:
        server_seed = prompt_str("Server seed") or generate_server_seed()
        client_seed = prompt_str("Client seed") or generate_client_seed()
    start_nonce = prompt_int("Start nonce", 0, 9999, default=0)

    console.print(f"\n  [dim]Server: {server_seed[:32]}...[/dim]")
    console.print(f"  [dim]Client: {client_seed}[/dim]\n")

    from core.crypto import derive_board as _db
    for i in range(num_nonces):
        nonce = start_nonce + i
        _, _, _, board = _db(server_seed, client_seed, nonce, mine_count, ALL_NUMS)
        mines_str = ", ".join(str(p) for p in sorted(board.mine_positions_1b))
        col = mine_colour(mine_count)
        console.print(f"  [bold cyan]Nonce {nonce:>4}[/bold cyan]  [{col}]Mines: {mines_str}[/{col}]")
        grid = ""
        for row in range(5):
            for c in range(5):
                cell = row * 5 + c + 1
                grid += "[red]#[/red]" if cell in board.mine_positions_1b else "[dim].[/dim]"
            grid += "  "
        console.print(f"             {grid}\n")
    pause()

# ---------------------------------------------------------------------------
# MENU 5 — SEED TOOLS
# ---------------------------------------------------------------------------

def menu_seed_tools():
    while True:
        clear()
        header("SEED TOOLS", "Generate, hash, and inspect seed values")
        options = {
            "1": "Generate random seeds",
            "2": "Compute SHA256 of a string",
            "3": "Board preview from seeds",
            "4": "Show reference board (ALL_NUMS)",
            "B": "Back",
        }
        print_menu(options)
        choice = prompt_choice(list(options.keys()))
        if choice == "B":
            return
        elif choice == "1":
            clear()
            header("GENERATE RANDOM SEEDS")
            ss  = generate_server_seed()
            ssh = hash_server_seed(ss)
            cs  = generate_client_seed()
            console.print(Panel(
                f"  [bold]Server Seed:[/bold]       [green]{ss}[/green]\n"
                f"  [bold]Server Seed Hash:[/bold]  [dim]{ssh}[/dim]\n"
                f"  [bold]Client Seed:[/bold]       [cyan]{cs}[/cyan]\n"
                f"  [bold]Nonce:[/bold]             0",
                title="[bold]GENERATED[/bold]", border_style="green", padding=(1, 2),
            ))
            pause()
        elif choice == "2":
            clear()
            header("SHA256 CALCULATOR")
            data   = prompt_str("Input string")
            result = hash_server_seed(data)
            console.print(f"\n  [dim]{data[:40]}[/dim]\n  -> [green]{result}[/green]\n")
            pause()
        elif choice == "3":
            clear()
            header("BOARD PREVIEW")
            server_seed, _, client_seed, nonce = collect_seeds_manual()
            mine_count = prompt_mine_count()
            mines = auditor.derive_mines_only(server_seed, client_seed, nonce, mine_count)
            col   = mine_colour(mine_count)
            console.print(f"\n  [{col}]Mine positions: {sorted(mines)}[/{col}]\n")
            for row in range(5):
                row_str = "  "
                for c in range(5):
                    cell = row * 5 + c + 1
                    row_str += f"[bold red] #{cell:02d}[/bold red]" if cell in mines else f"[dim]  {cell:02d}[/dim]"
                console.print(row_str)
            console.print()
            pause()
        elif choice == "4":
            clear()
            header("REFERENCE BOARD (ALL_NUMS)")
            v   = REF_VALIDATION
            col = "green" if v["verified"] else "yellow"
            console.print(f"  Status: [{col}]{'VERIFIED' if v['verified'] else 'PARTIALLY UNCONFIRMED'}[/{col}]  Length: {v['length']}/25\n")
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style="cyan dim")
            for _ in range(5):
                table.add_column(justify="center", width=5)
            for row in range(5):
                table.add_row(*[str(ALL_NUMS[row * 5 + c]) for c in range(5)])
            console.print(Panel(table, title="[bold]ALL_NUMS (5x5)[/bold]", border_style="cyan dim"))
            for w in v.get("warnings", []):
                console.print(f"  [yellow]{w}[/yellow]")
            pause()

# ---------------------------------------------------------------------------
# MENU 6 — SYSTEM INFO
# ---------------------------------------------------------------------------

def menu_info():
    clear()
    header("SYSTEM INFO")
    v   = REF_VALIDATION
    col = "green" if v["verified"] else "yellow"
    console.print(Panel(
        f"  [bold]bc-mines-lab[/bold]  v1.1\n\n"
        f"  Algorithm:     BC.Game double-pass hash-rotation shuffle\n"
        f"  Reference:     ALL_NUMS [{col}]{'VERIFIED' if v['verified'] else 'PARTIALLY UNCONFIRMED'}[/{col}]\n"
        f"  Python:        {sys.version.split()[0]}\n"
        f"  Reports dir:   reports/\n"
        f"  Examples dir:  examples/\n"
        + ("\n  [yellow]Warnings:[/yellow]\n" + "\n".join(f"  - {w}" for w in v.get("warnings",[])) if v.get("warnings") else ""),
        title="[bold cyan]SYSTEM INFO[/bold cyan]", border_style="cyan", padding=(1, 2),
    ))
    pause()

# ---------------------------------------------------------------------------
# Simulation rendering helpers
# ---------------------------------------------------------------------------

def _render_sim_round(sim, show_seeds=False):
    mine_set = set(sim.mine_positions)
    col      = mine_colour(sim.mine_count)
    rows     = []
    for row in range(5):
        row_str = ""
        for c in range(5):
            cell = row * 5 + c + 1
            row_str += f"[bold red] #{cell:02d}[/bold red] " if cell in mine_set else f"[dim] {cell:02d} [/dim] "
        rows.append(row_str)
    mines_str = ", ".join(str(p) for p in sorted(sim.mine_positions))
    body = "\n".join(rows) + f"\n\n  [{col}]Mines:[/{col}]  {mines_str}"
    if show_seeds:
        body += (f"\n  [dim]Server: {sim.server_seed[:24]}...[/dim]"
                 f"\n  [dim]Client: {sim.client_seed}  Nonce: {sim.nonce}  Mode: {sim.mode}[/dim]")
    console.print(Panel(body, title=f"[bold cyan]{sim.label or f'Round {sim.index}'}[/bold cyan]",
                        border_style="cyan dim", padding=(0, 2)))

def _render_sim_run_summary(run):
    col = mine_colour(run.mine_count)
    console.print(Rule(f"[bold cyan]SIMULATION RESULTS — {run.mode}[/bold cyan]", style="cyan"))
    console.print(f"\n  Rounds:  [bold]{run.total_rounds}[/bold]   "
                  f"Mines/board: [{col}]{run.mine_count}[/{col}]   "
                  f"Mode: [dim]{run.mode}[/dim]\n")
    _render_frequency_heatmap(run)
    hot  = SimulationEngine.hottest_cells(run, 5)
    cold = SimulationEngine.coldest_cells(run, 5)
    console.print("  [bold red]Hottest:[/bold red]   " +
                  "  ".join(f"[red]{p}[/red]({f:.1%})" for p, f in hot))
    console.print("  [bold green]Coldest:[/bold green]  " +
                  "  ".join(f"[green]{p}[/green]({f:.1%})" for p, f in cold))
    expected = run.mine_count / 25
    max_dev  = max(abs(f - expected) for f in run.mine_freq)
    dev_col  = "green" if max_dev < 0.05 else ("yellow" if max_dev < 0.15 else "red")
    console.print(f"\n  Expected per cell: [dim]{expected:.1%}[/dim]   "
                  f"Max deviation: [{dev_col}]{max_dev:.4f}[/{dev_col}]\n")

def _render_frequency_heatmap(run):
    console.print("  [bold]Mine frequency heatmap[/bold]  [dim](brighter = more frequent)[/dim]\n")
    max_freq = max(run.mine_freq) if run.mine_freq else 1.0
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan dim",
                  border_style="cyan dim", padding=(0, 1))
    table.add_column("  ", width=3, style="dim cyan")
    for c in range(5):
        table.add_column(f"C{c+1}", width=9, justify="center")
    for row in range(5):
        row_cells = [str(row + 1)]
        for col_i in range(5):
            cell = row * 5 + col_i + 1
            freq = run.mine_freq[cell - 1]
            norm = freq / max_freq if max_freq > 0 else 0
            if norm >= 0.8:   colour = "bold bright_red"
            elif norm >= 0.6: colour = "red"
            elif norm >= 0.4: colour = "yellow"
            elif norm >= 0.2: colour = "green"
            else:             colour = "dim"
            row_cells.append(f"[{colour}]{freq:.1%}\n{'█' * int(norm*4):<4}[/{colour}]")
        table.add_row(*row_cells)
    console.print(table)
    console.print()

def _offer_sim_export(run):
    if Confirm.ask("  Export simulation results to JSON?", default=False):
        ts   = int(time.time())
        path = Path("reports") / f"sim_{run.mode.lower()}_{run.mine_count}m_{ts}.json"
        path.parent.mkdir(exist_ok=True)
        with open(path, "w") as f:
            json.dump(run.to_dict(), f, indent=2)
        console.print(f"  [green]Saved -> {path}[/green]")

def _offer_export(result):
    if Confirm.ask("\n  Export JSON report?", default=False):
        console.print(f"  [green]Saved -> {export_json(result)}[/green]")
    if Confirm.ask("  Export Markdown report?", default=False):
        console.print(f"  [green]Saved -> {export_markdown(result)}[/green]")

# ---------------------------------------------------------------------------
# NON-INTERACTIVE CLI (subcommands)
# ---------------------------------------------------------------------------

def _parse_claimed(raw: Optional[str]) -> Optional[list]:
    """Parse a comma-separated '7,14,21' string into [7, 14, 21]."""
    if not raw:
        return None
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"Error: --claimed-mines must be comma-separated integers, got: {raw!r}")

def cmd_audit(args) -> int:
    """Audit a single round from command-line seed arguments."""
    inp = AuditInput(
        server_seed      = args.server_seed,
        client_seed      = args.client_seed,
        nonce            = args.nonce,
        mine_count       = args.mines,
        server_seed_hash = args.server_seed_hash,
    )
    result = auditor.audit(inp, claimed_mines=_parse_claimed(args.claimed_mines))
    render_full_audit(result, show_chain=True, show_passes=args.show_passes, show_board=True)
    if args.export:
        console.print(f"  [green]Saved JSON     -> {export_json(result, path=args.export)}[/green]")
    if args.export_md:
        console.print(f"  [green]Saved Markdown -> {export_markdown(result, path=args.export_md)}[/green]")
    # Exit non-zero if a commitment or position check failed
    return 0 if result.fully_verified else 1

def cmd_verify(args) -> int:
    """Verify a commitment only: SHA256(serverSeed) == publishedHash."""
    from core.crypto import verify_commitment
    result = verify_commitment(args.server_seed, args.server_seed_hash)
    ok  = result.verified
    col = "green" if ok else "red"
    console.print(Panel(
        f"  [{col}]{'VERIFIED' if ok else 'FAILED'}[/{col}]\n\n"
        f"  Server Seed:    [dim]{result.server_seed[:48]}...[/dim]\n"
        f"  Published Hash: [dim]{result.published_hash}[/dim]\n"
        f"  Computed Hash:  [{col}]{result.computed_hash}[/{col}]\n\n"
        f"  [dim]{result.match_detail}[/dim]",
        title=f"[bold]COMMITMENT {'VERIFIED' if ok else 'FAILED'}[/bold]",
        border_style=col, padding=(1, 2),
    ))
    return 0 if ok else 1

def cmd_replay(args) -> int:
    """Replay (audit) a single round from a saved JSON file."""
    p = Path(args.file)
    if not p.exists():
        console.print(f"  [red]File not found: {p}[/red]")
        return 2
    with open(p) as f:
        data = json.load(f)
    claimed = data.get("claimedMines") or data.get("claimed_mines")
    result  = auditor.audit_from_dict(data, claimed_mines=claimed)
    render_full_audit(result, show_chain=True, show_passes=args.show_passes, show_board=True)
    if args.export:
        console.print(f"  [green]Saved JSON     -> {export_json(result, path=args.export)}[/green]")
    if args.export_md:
        console.print(f"  [green]Saved Markdown -> {export_markdown(result, path=args.export_md)}[/green]")
    return 0 if result.fully_verified else 1

def cmd_batch(args) -> int:
    """Batch-audit multiple rounds from a JSON array file."""
    p = Path(args.file)
    if not p.exists():
        console.print(f"  [red]File not found: {p}[/red]")
        return 2
    with open(p) as f:
        data = json.load(f)
    if not isinstance(data, list):
        console.print("  [red]File must be a JSON array.[/red]")
        return 2
    batch = auditor.audit_batch(data)
    render_batch_summary(batch)
    if args.export:
        console.print(f"  [green]Saved JSON     -> {export_json(batch, path=args.export)}[/green]")
    if args.export_md:
        console.print(f"  [green]Saved Markdown -> {export_batch_markdown(batch, path=args.export_md)}[/green]")
    return 0 if batch.errors == 0 and batch.failed == 0 else 1

def cmd_info(args) -> int:
    """Print system info and reference-board status non-interactively."""
    v   = REF_VALIDATION
    col = "green" if v["verified"] else "yellow"
    console.print(Panel(
        f"  [bold]bc-mines-lab[/bold]  v1.1\n\n"
        f"  Algorithm:     BC.Game double-pass hash-rotation shuffle\n"
        f"  Reference:     ALL_NUMS [{col}]{'VERIFIED' if v['verified'] else 'PARTIALLY UNCONFIRMED'}[/{col}]\n"
        f"  Python:        {sys.version.split()[0]}\n"
        f"  Reports dir:   reports/\n"
        f"  Examples dir:  examples/\n"
        + ("\n  [yellow]Warnings:[/yellow]\n" + "\n".join(f"  - {w}" for w in v.get("warnings",[])) if v.get("warnings") else ""),
        title="[bold cyan]SYSTEM INFO[/bold cyan]", border_style="cyan", padding=(1, 2),
    ))
    return 0

def build_parser():
    import argparse
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="BC.Game Mines Provably Fair Audit Framework v1.1. "
                    "Run with no arguments to launch the interactive menu.",
    )
    sub = parser.add_subparsers(dest="command")

    # audit
    pa = sub.add_parser("audit", help="Audit a single round from seed arguments")
    pa.add_argument("--server-seed",      required=True,  help="Revealed server seed")
    pa.add_argument("--server-seed-hash", default=None,   help="Published SHA256 hash (enables commitment check)")
    pa.add_argument("--client-seed",      required=True,  help="Client seed")
    pa.add_argument("--nonce",            type=int, default=0, help="Nonce (default 0)")
    pa.add_argument("--mines",            type=int, required=True, help="Mine count")
    pa.add_argument("--claimed-mines",    default=None,   help="Comma-separated 1-based positions, e.g. 7,14,21")
    pa.add_argument("--export",           default=None,   help="Write JSON report to this path")
    pa.add_argument("--export-md",        default=None,   help="Write Markdown report to this path")
    pa.add_argument("--show-passes",      action="store_true", help="Show detailed shuffle pass tables")
    pa.set_defaults(func=cmd_audit)

    # verify
    pv = sub.add_parser("verify", help="Verify a commitment (SHA256 of server seed) only")
    pv.add_argument("--server-seed",      required=True,  help="Revealed server seed")
    pv.add_argument("--server-seed-hash", required=True,  help="Published SHA256 hash")
    pv.set_defaults(func=cmd_verify)

    # replay
    pr = sub.add_parser("replay", help="Replay/audit a round from a JSON file")
    pr.add_argument("file",               help="Path to round JSON file")
    pr.add_argument("--export",           default=None,   help="Write JSON report to this path")
    pr.add_argument("--export-md",        default=None,   help="Write Markdown report to this path")
    pr.add_argument("--show-passes",      action="store_true", help="Show detailed shuffle pass tables")
    pr.set_defaults(func=cmd_replay)

    # batch
    pb = sub.add_parser("batch", help="Batch-audit multiple rounds from a JSON array file")
    pb.add_argument("file",               help="Path to batch JSON file (array of rounds)")
    pb.add_argument("--export",           default=None,   help="Write JSON report to this path")
    pb.add_argument("--export-md",        default=None,   help="Write Markdown summary to this path")
    pb.set_defaults(func=cmd_batch)

    # info
    pi = sub.add_parser("info", help="Show system info and reference-board status")
    pi.set_defaults(func=cmd_info)

    # menu (explicit)
    pm = sub.add_parser("menu", help="Launch the interactive menu (default with no args)")
    pm.set_defaults(func=None)

    return parser

# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------

def main_menu():
    while True:
        clear()
        console.print(BANNER)
        console.print()
        console.print(Panel(DISCLAIMER, border_style="red dim", padding=(0, 1)))
        console.print()
        options = {
            "1": "Single Round Audit",
            "2": "Commitment Verifier",
            "3": "Batch Audit",
            "4": "Simulation Lab",
            "5": "Seed Tools",
            "6": "System Info",
            "Q": "Quit",
        }
        print_menu(options)
        choice = prompt_choice(list(options.keys()))
        if choice == "Q":
            console.print("\n[dim cyan]Goodbye.[/dim cyan]\n")
            return
        elif choice == "1": menu_audit()
        elif choice == "2": menu_verify()
        elif choice == "3": menu_batch()
        elif choice == "4": menu_simulation()
        elif choice == "5": menu_seed_tools()
        elif choice == "6": menu_info()

def main():
    parser = build_parser()
    args   = parser.parse_args()

    # No subcommand (or explicit "menu") -> interactive menu, preserving v1.1 behaviour.
    if getattr(args, "func", None) is None:
        try:
            main_menu()
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]\n")
            sys.exit(0)
        except Exception as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")
            import traceback; traceback.print_exc()
            sys.exit(1)
        return

    # Non-interactive subcommand dispatch.
    try:
        sys.exit(args.func(args))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]\n")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"\n[bold red]Error:[/bold red] {exc}")
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
