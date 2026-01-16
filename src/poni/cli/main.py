"""Main CLI application for Poni."""

import typer
from rich.console import Console

from poni import __version__

app = typer.Typer(
    name="poni",
    help="The control plane for agentic development",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"poni version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Poni - The control plane for agentic development."""
    pass


# Import and register commands (E402 intentional - lazy loading after app setup)
from poni.cli.docs import app as docs_app  # noqa: E402
from poni.cli.enforce import enforce  # noqa: E402
from poni.cli.init import init  # noqa: E402
from poni.cli.memory import app as memory_app  # noqa: E402
from poni.cli.serve import serve  # noqa: E402
from poni.cli.tools import app as tools_app  # noqa: E402
from poni.cli.tools import run  # noqa: E402
from poni.cli.validate import validate  # noqa: E402

app.command()(init)
app.command()(validate)
app.command()(serve)
app.command()(enforce)
app.command()(run)
app.add_typer(memory_app, name="memory")
app.add_typer(tools_app, name="tools")
app.add_typer(docs_app, name="docs")
