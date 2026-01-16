"""Memory management commands for Poni."""

import typer
from rich.console import Console
from rich.table import Table

from poni.config.loader import load_config
from poni.memory.store import MemoryStore

app = typer.Typer(help="Manage shared team memory")
console = Console()


@app.command("list")
def list_memories(
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category",
    ),
) -> None:
    """List memory entries."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    store = MemoryStore(config)
    entries = store.list_entries(category)

    if not entries:
        console.print("No memory entries found.")
        return

    table = Table(title="Memory Entries")
    table.add_column("ID", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Content")
    table.add_column("Added By", style="dim")

    for entry in entries:
        content = entry.content[:60] + "..." if len(entry.content) > 60 else entry.content
        table.add_row(entry.id, entry.category, content, entry.added_by)

    console.print(table)


@app.command("add")
def add_memory(
    content: str = typer.Argument(..., help="Memory content"),
    category: str = typer.Option(
        "patterns",
        "--category",
        "-c",
        help="Category (patterns, decisions, gotchas, glossary)",
    ),
    files: str | None = typer.Option(
        None,
        "--files",
        "-f",
        help="File glob pattern this relates to",
    ),
    context: str | None = typer.Option(
        None,
        "--context",
        help="Additional context",
    ),
) -> None:
    """Add a memory entry."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    store = MemoryStore(config)

    files_list = [files] if files else None
    entry = store.add(content, category, context, files_list)

    console.print(f"[green]✓[/green] Added memory {entry.id}: {content}")


@app.command("remove")
def remove_memory(
    entry_id: str = typer.Argument(..., help="Entry ID to remove"),
) -> None:
    """Remove a memory entry."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    store = MemoryStore(config)

    if store.remove(entry_id):
        console.print(f"[green]✓[/green] Removed {entry_id}")
    else:
        console.print(f"[red]✗[/red] Entry {entry_id} not found")
        raise typer.Exit(1)


@app.command("search")
def search_memories(
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Search memory entries."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    store = MemoryStore(config)
    entries = store.search(query)

    if not entries:
        console.print("No matching entries found.")
        return

    for entry in entries:
        console.print(f"[cyan]{entry.id}[/cyan] [{entry.category}]")
        console.print(f"  {entry.content}")
        if entry.context:
            console.print(f"  [dim]{entry.context}[/dim]")
        console.print()


@app.command("show")
def show_memory(
    entry_id: str = typer.Argument(..., help="Entry ID to show"),
) -> None:
    """Show details of a memory entry."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    store = MemoryStore(config)
    entries = store.list_entries()

    for entry in entries:
        if entry.id == entry_id:
            console.print(f"[bold cyan]{entry.id}[/bold cyan]")
            console.print(f"Category: {entry.category}")
            console.print(f"Added by: {entry.added_by}")
            console.print(f"Added at: {entry.added_at}")
            console.print(f"\n{entry.content}")
            if entry.context:
                console.print(f"\n[dim]Context: {entry.context}[/dim]")
            if entry.files:
                console.print(f"\n[dim]Files: {', '.join(entry.files)}[/dim]")
            return

    console.print(f"[red]Entry {entry_id} not found[/red]")
    raise typer.Exit(1)
