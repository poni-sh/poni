"""Tools management commands for Poni."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from poni.config.loader import load_config
from poni.tools.executor import ToolExecutor

app = typer.Typer(help="Manage and run custom tools")
console = Console()


@app.command("list")
def list_tools() -> None:
    """List available tools."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not config.tools:
        console.print("No tools configured.")
        return

    table = Table(title="Custom Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Command", style="dim")

    for name, tool_config in config.tools.items():
        table.add_row(
            name,
            tool_config.description or "-",
            tool_config.command,
        )

    console.print(table)

    # Also show CLI wrappers
    if config.cli:
        console.print()
        cli_table = Table(title="CLI Wrappers")
        cli_table.add_column("Name", style="cyan")
        cli_table.add_column("Description")
        cli_table.add_column("Command", style="dim")

        for name, cli_config in config.cli.items():
            cli_table.add_row(
                name,
                cli_config.description or "-",
                cli_config.command,
            )

        console.print(cli_table)


@app.command("show")
def show_tool(
    name: str = typer.Argument(..., help="Tool name to show details for"),
) -> None:
    """Show details of a tool."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Check custom tools
    if name in config.tools:
        tool = config.tools[name]
        console.print(f"[bold cyan]{name}[/bold cyan] (custom tool)")
        console.print(f"Description: {tool.description or '-'}")
        console.print(f"Command: {tool.command}")
        if tool.args:
            console.print(f"Args: {' '.join(tool.args)}")
        if tool.optional_args:
            console.print(f"Optional args: {', '.join(tool.optional_args)}")
        if tool.confirm:
            console.print("Requires confirmation: yes")
        if tool.allowed_branches:
            console.print(f"Allowed branches: {', '.join(tool.allowed_branches)}")
        console.print(f"Timeout: {tool.timeout}s")
        return

    # Check CLI wrappers
    if name in config.cli:
        cli = config.cli[name]
        console.print(f"[bold cyan]{name}[/bold cyan] (CLI wrapper)")
        console.print(f"Description: {cli.description or '-'}")
        console.print(f"Command: {cli.command}")
        if cli.args:
            console.print(f"Default args: {' '.join(cli.args)}")
        if cli.policies.allow_subcommands:
            console.print(f"Allowed subcommands: {', '.join(cli.policies.allow_subcommands)}")
        if cli.policies.deny_subcommands:
            console.print(f"Denied subcommands: {', '.join(cli.policies.deny_subcommands)}")
        if cli.policies.deny_patterns:
            console.print(f"Deny patterns: {', '.join(cli.policies.deny_patterns)}")
        return

    console.print(f"[red]Tool '{name}' not found[/red]")
    raise typer.Exit(1)


def run(
    name: str = typer.Argument(..., help="Tool name to run"),
    args: list[str] = typer.Argument(None, help="Arguments to pass to the tool"),
) -> None:
    """Run a custom tool.

    Example: poni run deploy --env staging
    """
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if name not in config.tools:
        console.print(f"[red]Error:[/red] Tool '{name}' not found")
        console.print("\nAvailable tools:")
        for tool_name in config.tools.keys():
            console.print(f"  - {tool_name}")
        raise typer.Exit(1)

    executor = ToolExecutor(config)

    # Parse args into kwargs (simple key=value parsing)
    kwargs: dict[str, str | bool] = {}
    if args:
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                key = arg[2:].replace("-", "_")
                # Check if next arg is a value or another flag
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    kwargs[key] = args[i + 1]
                    i += 2
                else:
                    kwargs[key] = True
                    i += 1
            else:
                i += 1

    console.print(f"Running [cyan]{name}[/cyan]...")

    result = asyncio.run(executor.execute(name, kwargs))

    if result.startswith("Error"):
        console.print(f"[red]{result}[/red]")
        raise typer.Exit(1)
    elif result.startswith("CONFIRMATION_REQUIRED"):
        console.print(f"[yellow]{result}[/yellow]")
        if typer.confirm("Do you want to proceed?"):
            # Re-run without confirmation
            tool_config = config.tools[name]
            original_confirm = tool_config.confirm
            tool_config.confirm = False
            result = asyncio.run(executor.execute(name, kwargs))
            tool_config.confirm = original_confirm
            console.print(result)
        else:
            console.print("Cancelled.")
    else:
        console.print(result)
