"""FastMCP server implementation for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import FastMCP

from poni.config.loader import load_config
from poni.config.models import CliConfig, ToolConfig
from poni.mcp.policy import PolicyEngine
from poni.mcp.tools import register_builtin_tools

if TYPE_CHECKING:
    from poni.tools.cli_wrapper import CliWrapper
    from poni.tools.executor import ToolExecutor


def create_server() -> FastMCP:
    """Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance.
    """
    config = load_config()
    mcp = FastMCP("poni")

    # Initialize components
    policy_engine = PolicyEngine(config)

    # Import here to avoid circular imports
    from poni.memory.store import MemoryStore
    from poni.tools.cli_wrapper import CliWrapper
    from poni.tools.executor import ToolExecutor

    memory_store = MemoryStore(config)
    tool_executor = ToolExecutor(config)
    cli_wrapper = CliWrapper(config, policy_engine)

    # Register built-in tools
    register_builtin_tools(mcp, memory_store, tool_executor, cli_wrapper)

    # Register CLI wrapper tools
    for cli_name, cli_config in config.cli.items():
        _register_cli_tool(mcp, cli_name, cli_config, cli_wrapper, policy_engine)

    # Register custom tools
    for tool_name, tool_config in config.tools.items():
        _register_custom_tool(mcp, tool_name, tool_config, tool_executor)

    return mcp


def _register_cli_tool(
    mcp: FastMCP,
    name: str,
    config: CliConfig,
    wrapper: CliWrapper,
    policy: PolicyEngine,
) -> None:
    """Register a CLI wrapper tool.

    Args:
        mcp: The FastMCP server instance.
        name: Name of the CLI wrapper.
        config: Configuration for the CLI wrapper.
        wrapper: The CLI wrapper instance.
        policy: The policy engine.
    """
    description = config.description or f"Execute {name} commands"

    @mcp.tool(name=f"poni.cli.{name}", description=description)
    async def cli_tool(args: str = "") -> str:
        """Execute a CLI command.

        Args:
            args: Command arguments.

        Returns:
            Command output or error message.
        """
        # Check policies
        violation = policy.check_cli(name, args)
        if violation:
            return f"Policy violation: {name}\n\n{violation}"

        # Check if interactive confirmation needed
        if policy.check_interactive(name, args):
            return (
                f"CONFIRMATION_REQUIRED: This command requires confirmation.\n"
                f"Command: {name} {args}\n"
                f"Please confirm you want to execute this command."
            )

        # Execute command
        result = await wrapper.execute(name, args)

        # Post-process output
        result = policy.redact_output(name, result)
        result = policy.truncate_output(name, result)

        return result


def _register_custom_tool(
    mcp: FastMCP,
    name: str,
    config: ToolConfig,
    executor: ToolExecutor,
) -> None:
    """Register a custom team tool.

    Args:
        mcp: The FastMCP server instance.
        name: Name of the tool.
        config: Configuration for the tool.
        executor: The tool executor instance.
    """
    # description = config.description or f"Run {name}"

    # For now, skip custom tools until we can implement proper parameter handling
    # FastMCP doesn't support dynamic function generation with **kwargs or *args
    # TODO: Implement proper custom tool registration with explicit parameters
    return
