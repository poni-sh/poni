"""Serve command for Poni MCP server."""

import typer
from rich.console import Console

console = Console()


def serve(
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="Transport type: stdio or sse",
    ),
    host: str = typer.Option(
        "localhost",
        "--host",
        help="Host for SSE transport",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port for SSE transport",
    ),
) -> None:
    """Run Poni as an MCP server.

    By default, runs on stdio for use with Claude Code and other MCP clients.
    Use --transport sse for HTTP-based connections.
    """
    from poni.mcp.server import create_server

    try:
        server = create_server()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

    if transport == "stdio":
        server.run()
    elif transport == "sse":
        server.run(transport="sse", host=host, port=port)
    else:
        console.print(f"[red]Error:[/red] Unknown transport: {transport}")
        raise typer.Exit(1)
