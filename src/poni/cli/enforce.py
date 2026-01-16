"""Enforce command for Poni."""

import typer
from rich.console import Console

from poni.config.loader import load_config
from poni.enforcement.rules import RuleExecutor

console = Console()


def enforce(
    hook: str | None = typer.Option(
        None,
        "--hook",
        help="Hook type: pre-commit or pre-push",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Auto-fix issues where possible",
    ),
    staged: bool = typer.Option(
        False,
        "--staged",
        help="Only check staged files",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show verbose output",
    ),
) -> None:
    """Run enforcement checks.

    When run as a git hook, uses the appropriate trigger.
    Otherwise runs all pre-commit rules by default.
    """
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not config.enforcement.enabled:
        if verbose:
            console.print("[dim]Enforcement is disabled[/dim]")
        return

    executor = RuleExecutor(config)

    # Determine files to check
    if staged or hook == "pre-commit":
        files = executor.get_staged_files()
        if not files:
            if verbose:
                console.print("[dim]No staged files to check[/dim]")
            return
    else:
        files = None  # All files

    # Determine trigger
    trigger = hook or "pre-commit"

    # Get rules for this trigger
    rules = [r for r in config.enforcement.rules if r.trigger == trigger and r.enabled]

    if not rules:
        if verbose:
            console.print(f"[dim]No rules configured for {trigger}[/dim]")
        return

    console.print(f"\n[bold]Poni enforcement checks ({trigger}):[/bold]\n")

    # Run rules
    results = executor.run_all(trigger, files)

    failed = []
    for result in results:
        if result.success:
            console.print(f"  [green]✓[/green] {result.rule_name}")
        else:
            console.print(f"  [red]✗[/red] {result.rule_name}")
            if result.output:
                # Show first few lines of output
                lines = result.output.strip().split("\n")[:10]
                for line in lines:
                    console.print(f"    [dim]{line}[/dim]")
                if len(result.output.strip().split("\n")) > 10:
                    console.print("    [dim]...[/dim]")
            failed.append(result)

    console.print()

    if failed:
        console.print(f"[red]Blocked. Fix {len(failed)} issue(s) above.[/red]")
        raise typer.Exit(1)

    console.print("[green]All checks passed.[/green]")
