"""Init command for Poni."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomlkit
import typer
from rich.console import Console

from poni.config.detection import DetectedProject, detect_project
from poni.enforcement.hooks import check_existing_hooks, install_hooks
from poni.presets import get_preset

console = Console()

PONI_DIR = ".poni"
MCP_JSON = ".mcp.json"


def init(
    preset: str | None = typer.Option(
        None,
        "--preset",
        "-p",
        help="Use preset: typescript, python, rust, go",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Accept all defaults without prompting",
    ),
    detect_only: bool = typer.Option(
        False,
        "--detect-only",
        help="Only show detection results, don't initialize",
    ),
    no_hooks: bool = typer.Option(
        False,
        "--no-hooks",
        help="Don't install git hooks",
    ),
) -> None:
    """Initialize Poni in the current repository.

    Detects your project setup and creates a configuration file
    with sensible defaults for your stack.
    """
    cwd = Path.cwd()
    poni_dir = cwd / PONI_DIR

    # Check if already initialized
    if poni_dir.exists() and not detect_only:
        console.print(f"[yellow]Warning:[/yellow] {PONI_DIR} already exists")
        if not yes and not typer.confirm("Reinitialize?"):
            raise typer.Exit(0)

    # Detect project
    console.print("[bold]Detecting project setup...[/bold]\n")
    detected = detect_project(cwd)

    if detected.languages:
        console.print(f"  Languages: [cyan]{', '.join(detected.languages)}[/cyan]")
    if detected.tools:
        console.print(f"  Tools: [cyan]{', '.join(detected.tools)}[/cyan]")
    if detected.package_manager:
        console.print(f"  Package manager: [cyan]{detected.package_manager}[/cyan]")
    if detected.existing_hooks:
        console.print(f"  Existing hooks: [yellow]{', '.join(detected.existing_hooks)}[/yellow]")

    if detect_only:
        return

    console.print()

    # Check for existing hook systems
    existing = check_existing_hooks(cwd)
    if existing and not yes:
        console.print("[yellow]Existing hook systems detected:[/yellow]")
        for system, path in existing.items():
            console.print(f"  - {system}: {path}")
        console.print("\nPoni will manage hooks. You can remove the existing systems after setup.")
        if not typer.confirm("Continue?"):
            raise typer.Exit(0)

    # Generate config
    if preset:
        try:
            config = get_preset(preset)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    else:
        config = _generate_config_from_detection(detected)

    # Create directories
    poni_dir.mkdir(exist_ok=True)
    (poni_dir / "prompts").mkdir(exist_ok=True)
    (poni_dir / "memory").mkdir(exist_ok=True)
    (poni_dir / "docs").mkdir(exist_ok=True)

    # Write config.toml
    config_path = poni_dir / "config.toml"
    with open(config_path, "w") as f:
        tomlkit.dump(config, f)
    console.print(f"  [green]✓[/green] Created {config_path}")

    # Write .mcp.json
    mcp_json_path = cwd / MCP_JSON
    mcp_config = {"mcpServers": {"poni": {"command": "poni", "args": ["serve"], "type": "stdio"}}}
    with open(mcp_json_path, "w") as f:
        json.dump(mcp_config, f, indent=2)
    console.print(f"  [green]✓[/green] Created {mcp_json_path}")

    # Create memory files
    for category in ["patterns", "decisions", "gotchas", "glossary"]:
        memory_file = poni_dir / "memory" / f"{category}.toml"
        if not memory_file.exists():
            memory_file.write_text("# Shared team memory\n\n")
    console.print("  [green]✓[/green] Created memory files")

    # Install git hooks
    if not no_hooks:
        installed = install_hooks(cwd)
        if installed:
            console.print(f"  [green]✓[/green] Installed git hooks: {', '.join(installed)}")
        else:
            console.print("  [yellow]![/yellow] No .git directory found, skipping hooks")

    # Update .gitignore
    _update_gitignore(cwd)
    console.print("  [green]✓[/green] Updated .gitignore")

    # Print next steps
    console.print("\n[bold green]Poni initialized![/bold green]\n")
    console.print("Next steps:")
    console.print("  1. Review .poni/config.toml")
    if detected.existing_hooks:
        console.print(f"  2. Remove {', '.join(detected.existing_hooks)} (Poni handles hooks now)")
    console.print("  3. Commit .poni/ and .mcp.json to git")
    console.print("\nConfigure Claude Code:")
    console.print("  Add 'poni' to your MCP servers in Claude Code settings")


def _generate_config_from_detection(detected: DetectedProject) -> dict[str, Any]:
    """Generate config based on detected project setup.

    Args:
        detected: Detection results.

    Returns:
        Configuration dict.
    """
    # Import preset based on detected language
    if "typescript" in detected.languages or "javascript" in detected.languages:
        from poni.presets.typescript import generate_config

        return generate_config(detected)
    elif "python" in detected.languages:
        from poni.presets.python import generate_config

        return generate_config(detected)
    elif "rust" in detected.languages:
        from poni.presets.rust import generate_config

        return generate_config(detected)
    elif "go" in detected.languages:
        from poni.presets.go import generate_config

        return generate_config(detected)
    else:
        # Minimal config
        return {
            "poni": {"version": "0.1.0"},
            "secrets": {"source": "env"},
            "enforcement": {"enabled": True, "rules": []},
            "lifecycle": {"enabled": True, "hooks": []},
            "memory": {"enabled": True},
        }


def _update_gitignore(cwd: Path) -> None:
    """Add Poni entries to .gitignore.

    Args:
        cwd: Current working directory.
    """
    gitignore = cwd / ".gitignore"
    entries = [".poni/.secrets.toml", ".poni/docs/.lock.toml"]

    if gitignore.exists():
        content = gitignore.read_text()
        missing = [e for e in entries if e not in content]
        if missing:
            with open(gitignore, "a") as f:
                f.write("\n# Poni\n")
                for entry in missing:
                    f.write(f"{entry}\n")
    else:
        with open(gitignore, "w") as f:
            f.write("# Poni\n")
            for entry in entries:
                f.write(f"{entry}\n")
