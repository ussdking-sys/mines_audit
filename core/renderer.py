"""
core/renderer.py — Terminal rendering for audit results.

Renders boards, crypto chains, verification results, and batch summaries
using Rich for colour and structure.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich.columns import Columns
from rich import box

from core.models import AuditResult, BatchResult, ShufflePass, CryptoChain


console = Console()

# ---------------------------------------------------------------------------
# Colour constants
# ---------------------------------------------------------------------------
MINE_STYLE  = "bold red on dark_red"
SAFE_STYLE  = "bold green"
PASS_STYLE  = "bold green"
FAIL_STYLE  = "bold red"
WARN_STYLE  = "bold yellow"
DIM_STYLE   = "dim"
HEAD_STYLE  = "bold cyan"
PANEL_STYLE = "cyan"


DISCLAIMER = (
    "[bold red]⚠  DISCLAIMER[/bold red]  "
    "This tool is for [yellow]educational and auditing purposes only[/yellow]. "
    "It does [bold red]NOT[/bold red] predict future outcomes, automate bets, "
    "or guarantee any advantage. Provably fair systems are verifiable "
    "[italic]after[/italic] the fact — not predictable before."
)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def render_banner() -> None:
    """Print the startup banner with disclaimer."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]bc-mines-lab-v1.0[/bold cyan]  "
            "[dim]BC.Game Mines Provably Fair Audit Framework[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print(
        Panel(DISCLAIMER, border_style="red dim", padding=(0, 1))
    )
    console.print()


# ---------------------------------------------------------------------------
# Board renderer
# ---------------------------------------------------------------------------

def render_board(result: AuditResult, show_safe: bool = True) -> None:
    """
    Render a 5x5 board grid with mine positions highlighted.

    Args:
        result:    The AuditResult to render
        show_safe: If True, show safe cell numbers; else show '·'
    """
    board      = result.board
    mine_set   = set(board.mine_positions_1b)
    grid       = board.board_grid

    table = Table(
        box          = box.HEAVY,
        show_header  = False,
        border_style = "cyan dim",
        padding      = (0, 1),
    )
    for _ in range(5):
        table.add_column(justify="center", width=6)

    for row_idx, row in enumerate(grid):
        row_cells = []
        for col_idx, cell_type in enumerate(row):
            cell_1b = row_idx * 5 + col_idx + 1
            if cell_type == "MINE":
                row_cells.append(f"[{MINE_STYLE}] #{cell_1b:02d} [/{MINE_STYLE}]")
            else:
                if show_safe:
                    row_cells.append(f"[{SAFE_STYLE}]  {cell_1b:02d} [/{SAFE_STYLE}]")
                else:
                    row_cells.append(f"[dim]  ·  [/dim]")
        table.add_row(*row_cells)

    mine_list = ", ".join(str(p) for p in sorted(board.mine_positions_1b))
    console.print(
        Panel(
            table,
            title    = f"[{HEAD_STYLE}]DERIVED BOARD — {board.mine_count} MINE{'S' if board.mine_count != 1 else ''}[/{HEAD_STYLE}]",
            subtitle = f"[dim]Mines at positions: {mine_list}[/dim]",
            border_style = "cyan",
        )
    )


# ---------------------------------------------------------------------------
# Commitment verification panel
# ---------------------------------------------------------------------------

def render_commitment(result: AuditResult) -> None:
    """Render the seed commitment verification result."""
    if not result.commitment:
        console.print("[dim]No server seed hash provided — commitment check skipped.[/dim]")
        return

    c       = result.commitment
    ok      = c.verified
    status  = f"[{PASS_STYLE}]✓  VERIFIED[/{PASS_STYLE}]" if ok else f"[{FAIL_STYLE}]✗  FAILED[/{FAIL_STYLE}]"

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style="green dim" if ok else "red dim")
    table.add_column("Field",  style="dim", width=22)
    table.add_column("Value",  width=68)

    table.add_row("Status",          status)
    table.add_row("Server Seed",     f"[dim]{c.server_seed[:32]}...[/dim]" if len(c.server_seed) > 32 else c.server_seed)
    table.add_row("Published Hash",  f"[dim]{c.published_hash}[/dim]")
    table.add_row("Computed Hash",   f"[{'green' if ok else 'red'}]{c.computed_hash}[/{'green' if ok else 'red'}]")
    table.add_row("Detail",          f"[dim]{c.match_detail}[/dim]")

    console.print(
        Panel(
            table,
            title        = f"[bold]COMMITMENT VERIFICATION[/bold]",
            border_style = "green" if ok else "red",
        )
    )


# ---------------------------------------------------------------------------
# Crypto chain panel
# ---------------------------------------------------------------------------

def render_crypto_chain(result: AuditResult) -> None:
    """Render the full cryptographic derivation chain."""
    cc = result.crypto_chain

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), border_style="magenta dim")
    table.add_column("Step",   style="bold magenta dim", width=26)
    table.add_column("Value",  width=68)

    rows = [
        ("HMAC message",          cc.hmac_input_message),
        ("HMAC-SHA256 result",     cc.hmac_result),
        ("Pass 1 seed",            cc.pass1_seed),
        ("SHA256(pass1_seed)",     cc.pass1_seed_sha256),
        ("Pass 2 seed",            cc.pass2_seed),
        ("SHA256(pass2_seed)",     cc.pass2_seed_sha256),
    ]
    for label, value in rows:
        val_display = f"[dim]{value}[/dim]" if len(value) > 20 else value
        table.add_row(label, val_display)

    console.print(
        Panel(table, title="[bold magenta]CRYPTOGRAPHIC CHAIN[/bold magenta]", border_style="magenta dim")
    )


# ---------------------------------------------------------------------------
# Shuffle pass panel
# ---------------------------------------------------------------------------

def render_shuffle_pass(pass_data: ShufflePass, pass_num: int) -> None:
    """Render the annotated shuffle state for one pass."""
    console.print(f"\n[bold cyan]── SHUFFLE PASS {pass_num} ──[/bold cyan]")
    console.print(f"  [dim]Seed:[/dim] {pass_data.seed_used[:32]}...")
    console.print(f"  [dim]h₀  :[/dim] {pass_data.h_initial[:32]}...")
    console.print(f"  [dim]Input:[/dim]  {pass_data.input_array}")
    console.print(f"  [dim]Output:[/dim] [cyan]{pass_data.sorted_result}[/cyan]")

    if len(pass_data.annotated) <= 25:
        table = Table(
            box          = box.MINIMAL,
            show_header  = True,
            header_style = "bold cyan dim",
            border_style = "cyan dim",
            padding      = (0, 1),
        )
        table.add_column("#",    width=4,  justify="right")
        table.add_column("Num",  width=6,  justify="right")
        table.add_column("Hash (first 20 chars)", width=24)
        table.add_column("Hash (last 20 chars)",  width=24)

        for i, entry in enumerate(pass_data.annotated):
            h = entry.hash
            table.add_row(
                str(i),
                str(entry.num),
                f"[dim]{h[:20]}[/dim]",
                f"[dim]{h[-20:]}[/dim]",
            )
        console.print(table)


# ---------------------------------------------------------------------------
# Summary panel
# ---------------------------------------------------------------------------

def render_summary(result: AuditResult) -> None:
    """Render a concise one-panel audit summary."""
    inp   = result.audit_input
    board = result.board
    ok    = result.fully_verified

    status_str = (
        f"[{PASS_STYLE}]✓ FULLY VERIFIED[/{PASS_STYLE}]"
        if ok else
        f"[{FAIL_STYLE}]✗ VERIFICATION ISSUES[/{FAIL_STYLE}]"
    )

    # Reference board warning
    ref_warn = (
        "\n  [yellow]⚠ Reference array partially unconfirmed (last 6 values).[/yellow]"
        if not result.reference_verified else ""
    )

    mine_str  = ", ".join(str(p) for p in sorted(board.mine_positions_1b))
    label_str = f"  Label:       {inp.label}\n" if inp.label else ""

    body = (
        f"  Status:      {status_str}\n"
        f"{label_str}"
        f"  Client Seed: [dim]{inp.client_seed[:24]}{'...' if len(inp.client_seed) > 24 else ''}[/dim]\n"
        f"  Nonce:       {inp.nonce}\n"
        f"  Mines:       {inp.mine_count}\n"
        f"  Positions:   [bold cyan]{mine_str}[/bold cyan]\n"
        f"  Commitment:  "
        + (
            f"[{PASS_STYLE}]✓ PASS[/{PASS_STYLE}]"
            if result.commitment and result.commitment.verified
            else (f"[{FAIL_STYLE}]✗ FAIL[/{FAIL_STYLE}]" if result.commitment else "[dim]not checked[/dim]")
        )
        + "\n"
        f"  Pos Match:   "
        + (
            f"[{PASS_STYLE}]✓ MATCH[/{PASS_STYLE}]"
            if result.positions_match is True
            else (f"[{FAIL_STYLE}]✗ MISMATCH[/{FAIL_STYLE}]" if result.positions_match is False else "[dim]not checked[/dim]")
        )
        + ref_warn
    )

    console.print(
        Panel(
            body,
            title        = "[bold cyan]AUDIT SUMMARY[/bold cyan]",
            border_style = "green" if ok else "red",
            padding      = (1, 2),
        )
    )


# ---------------------------------------------------------------------------
# Full audit render
# ---------------------------------------------------------------------------

def render_full_audit(
    result:        AuditResult,
    show_chain:    bool = True,
    show_passes:   bool = False,
    show_board:    bool = True,
) -> None:
    """
    Render a complete audit result to the terminal.

    Args:
        result:      The AuditResult to render
        show_chain:  Include the cryptographic chain panel
        show_passes: Include detailed shuffle pass tables
        show_board:  Include the 5x5 board grid
    """
    render_summary(result)

    if result.commitment:
        render_commitment(result)

    if show_chain:
        render_crypto_chain(result)

    if show_passes:
        render_shuffle_pass(result.pass1, 1)
        render_shuffle_pass(result.pass2, 2)

    if show_board:
        render_board(result)

    # Claimed vs derived comparison
    if result.claimed_mines is not None:
        console.print()
        match   = result.positions_match
        col     = "green" if match else "red"
        symbol  = "✓" if match else "✗"
        derived = sorted(result.board.mine_positions_1b)
        claimed = sorted(result.claimed_mines)
        console.print(f"  [{col}]{symbol} Derived:[/{col}]  {derived}")
        console.print(f"  [{col}]{symbol} Claimed:[/{col}]  {claimed}")

    console.print()


# ---------------------------------------------------------------------------
# Batch summary
# ---------------------------------------------------------------------------

def render_batch_summary(batch: BatchResult) -> None:
    """Render a batch verification summary table."""
    console.print(Rule("[bold cyan]BATCH AUDIT SUMMARY[/bold cyan]", style="cyan"))

    pr_col = "green" if batch.pass_rate >= 0.95 else ("yellow" if batch.pass_rate >= 0.7 else "red")

    summary_table = Table(box=box.ROUNDED, show_header=False, border_style="cyan dim", padding=(0, 2))
    summary_table.add_column("Metric", style="dim cyan", width=20)
    summary_table.add_column("Value",  width=16)

    summary_table.add_row("Total Rounds",  str(batch.total))
    summary_table.add_row("Passed",        f"[green]{batch.passed}[/green]")
    summary_table.add_row("Failed",        f"[red]{batch.failed}[/red]")
    summary_table.add_row("Errors",        f"[yellow]{batch.errors}[/yellow]")
    summary_table.add_row("Pass Rate",     f"[{pr_col}]{batch.pass_rate:.1%}[/{pr_col}]")

    console.print(summary_table)

    # Per-round status
    detail_table = Table(
        box          = box.SIMPLE,
        show_header  = True,
        header_style = "bold cyan",
        border_style = "cyan dim",
        padding      = (0, 1),
    )
    detail_table.add_column("#",          width=5,  justify="right")
    detail_table.add_column("Label",      width=18)
    detail_table.add_column("Mines",      width=6,  justify="center")
    detail_table.add_column("Positions",  width=30)
    detail_table.add_column("Commit",     width=10, justify="center")
    detail_table.add_column("Match",      width=10, justify="center")
    detail_table.add_column("Status",     width=12, justify="center")

    for i, r in enumerate(batch.results, 1):
        label     = r.audit_input.label or f"round-{i}"
        mines_str = ", ".join(str(p) for p in sorted(r.board.mine_positions_1b))
        commit    = "✓" if (r.commitment and r.commitment.verified) else ("✗" if r.commitment else "—")
        match     = "✓" if r.positions_match is True else ("✗" if r.positions_match is False else "—")
        status    = f"[green]PASS[/green]" if r.fully_verified else f"[red]FAIL[/red]"
        c_col     = "green" if commit == "✓" else ("red" if commit == "✗" else "dim")
        m_col     = "green" if match == "✓" else ("red" if match == "✗" else "dim")

        detail_table.add_row(
            str(i), label, str(r.audit_input.mine_count),
            f"[dim]{mines_str}[/dim]",
            f"[{c_col}]{commit}[/{c_col}]",
            f"[{m_col}]{match}[/{m_col}]",
            status,
        )

    console.print(detail_table)
    console.print()
