"""Documentation commands for Poni."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from poni.config.loader import load_config
from poni.docs.generator import DocsGenerator

app = typer.Typer(help="Generate and manage documentation")
console = Console()


@app.command("generate")
def generate(
    target: str | None = typer.Argument(
        None,
        help="Specific target to generate (optional)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force regeneration even if sources haven't changed",
    ),
) -> None:
    """Generate documentation from source files.

    Uses configured prompts to generate documentation for each target.
    Only regenerates if source files have changed (unless --force is used).
    """
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not config.docs.enabled:
        console.print("[yellow]Documentation generation is not enabled.[/yellow]")
        console.print("Enable it in .poni/config.toml:")
        console.print("  [docs]")
        console.print("  enabled = true")
        raise typer.Exit(1)

    if not config.docs.targets:
        console.print("[yellow]No documentation targets configured.[/yellow]")
        console.print("Add targets in .poni/config.toml:")
        console.print("  [[docs.targets]]")
        console.print('  name = "api"')
        console.print('  paths = ["src/api/**/*.py"]')
        console.print('  output = "api.md"')
        raise typer.Exit(1)

    generator = DocsGenerator(config)

    # Filter to specific target if specified
    if target:
        matching = [t for t in config.docs.targets if t.name == target]
        if not matching:
            console.print(f"[red]Error:[/red] Target '{target}' not found")
            console.print("\nAvailable targets:")
            for t in config.docs.targets:
                console.print(f"  - {t.name}")
            raise typer.Exit(1)
        targets = matching
    else:
        targets = config.docs.targets

    console.print("[bold]Generating documentation...[/bold]\n")

    # Generate each target
    for doc_target in targets:
        result = asyncio.run(generator.generate_target(doc_target, force))

        if result.skipped:
            console.print(f"  [dim]○[/dim] {result.target} [dim](unchanged)[/dim]")
        elif result.success:
            console.print(f"  [green]✓[/green] {result.target} → {result.output_path}")
        else:
            console.print(f"  [red]✗[/red] {result.target}")
            if result.error:
                console.print(f"    [dim]{result.error}[/dim]")

    console.print()


@app.command("list")
def list_targets() -> None:
    """List configured documentation targets."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not config.docs.enabled:
        console.print("[yellow]Documentation generation is not enabled.[/yellow]")
        return

    if not config.docs.targets:
        console.print("No documentation targets configured.")
        return

    table = Table(title="Documentation Targets")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Output", style="dim")
    table.add_column("Paths", style="dim")

    for target in config.docs.targets:
        paths = ", ".join(target.paths[:2])
        if len(target.paths) > 2:
            paths += f" (+{len(target.paths) - 2} more)"
        table.add_row(
            target.name,
            target.description or "-",
            target.output,
            paths,
        )

    console.print(table)


@app.command("status")
def status() -> None:
    """Show status of documentation targets."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not config.docs.enabled:
        console.print("[yellow]Documentation generation is not enabled.[/yellow]")
        return

    from poni.docs.lock import DocsLock

    lock = DocsLock()
    entries = lock.load()

    if not config.docs.targets:
        console.print("No documentation targets configured.")
        return

    table = Table(title="Documentation Status")
    table.add_column("Target", style="cyan")
    table.add_column("Status")
    table.add_column("Last Generated", style="dim")

    for target in config.docs.targets:
        entry = entries.get(target.name)
        if entry:
            needs_update = lock.needs_regeneration(target)
            if needs_update:
                status_str = "[yellow]outdated[/yellow]"
            else:
                status_str = "[green]up to date[/green]"
            last_gen = entry.generated_at[:19] if entry.generated_at else "-"
        else:
            status_str = "[dim]not generated[/dim]"
            last_gen = "-"

        table.add_row(target.name, status_str, last_gen)

    console.print(table)
