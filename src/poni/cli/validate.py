"""Validate command for Poni."""

from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from poni.config.loader import find_config_path, load_config

console = Console()


def validate(
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (defaults to .poni/config.toml)",
    ),
) -> None:
    """Validate Poni configuration."""
    # Find config
    actual_path: Path | None = None
    if config_path:
        if not config_path.exists():
            console.print(f"[red]Error:[/red] Config file not found: {config_path}")
            raise typer.Exit(1)
        actual_path = config_path
    else:
        actual_path = find_config_path()
        if not actual_path:
            console.print("[red]Error:[/red] No .poni/config.toml found.")
            console.print("Run [cyan]poni init[/cyan] to create one.")
            raise typer.Exit(1)

    console.print(f"Validating [cyan]{actual_path}[/cyan]...\n")

    # Try to load and validate
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        # Secret resolution error
        console.print(f"[red]Secret resolution error:[/red]\n{e}")
        raise typer.Exit(1)
    except ValidationError as e:
        console.print("[red]Validation errors:[/red]\n")
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            console.print(f"  [yellow]{loc}[/yellow]: {msg}")
        raise typer.Exit(1)

    # Print summary
    console.print("[green]✓[/green] Configuration is valid\n")

    # Show what's configured
    if config.mcps:
        console.print(f"  MCPs: {', '.join(config.mcps.keys())}")
    if config.cli:
        console.print(f"  CLI wrappers: {', '.join(config.cli.keys())}")
    if config.tools:
        console.print(f"  Custom tools: {', '.join(config.tools.keys())}")
    if config.enforcement.rules:
        console.print(f"  Enforcement rules: {len(config.enforcement.rules)}")
    if config.lifecycle.hooks:
        console.print(f"  Lifecycle hooks: {len(config.lifecycle.hooks)}")
    if config.memory.enabled:
        console.print(f"  Memory: enabled ({len(config.memory.categories)} categories)")
    if config.docs.enabled:
        console.print(f"  Docs: enabled ({len(config.docs.targets)} targets)")
