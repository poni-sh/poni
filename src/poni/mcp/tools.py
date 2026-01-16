"""Built-in MCP tools for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from poni.memory.store import MemoryStore
    from poni.tools.cli_wrapper import CliWrapper
    from poni.tools.executor import ToolExecutor


def register_builtin_tools(
    mcp: FastMCP,
    memory_store: MemoryStore,
    tool_executor: ToolExecutor,
    cli_wrapper: CliWrapper,
) -> None:
    """Register built-in Poni tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
        memory_store: The memory store for team memory operations.
        tool_executor: The executor for custom tools.
        cli_wrapper: The CLI wrapper for CLI tools.
    """

    @mcp.tool(name="poni.memory.add")
    async def memory_add(
        content: str,
        category: str = "patterns",
        context: str | None = None,
        files: list[str] | None = None,
    ) -> str:
        """Add a memory entry for the team.

        Args:
            content: The memory content to add.
            category: Category for the memory (patterns, decisions, gotchas, glossary).
            context: Optional additional context.
            files: Optional list of file patterns this memory relates to.

        Returns:
            Confirmation message with the new entry ID.
        """
        entry = memory_store.add(content, category, context, files)
        return f"Added memory {entry.id}: {content}"

    @mcp.tool(name="poni.memory.list")
    async def memory_list(category: str | None = None) -> str:
        """List all memory entries.

        Args:
            category: Optional category filter.

        Returns:
            Formatted list of memory entries.
        """
        entries = memory_store.list_entries(category)
        if not entries:
            return "No memory entries found."

        lines = []
        for entry in entries:
            lines.append(f"[{entry.id}] ({entry.category}) {entry.content}")
            if entry.context:
                lines.append(f"    Context: {entry.context}")
        return "\n".join(lines)

    @mcp.tool(name="poni.memory.search")
    async def memory_search(query: str) -> str:
        """Search memory entries.

        Args:
            query: Search query string.

        Returns:
            Matching memory entries.
        """
        entries = memory_store.search(query)
        if not entries:
            return f"No entries matching '{query}'"

        lines = []
        for entry in entries:
            lines.append(f"[{entry.id}] ({entry.category}) {entry.content}")
            if entry.context:
                lines.append(f"    Context: {entry.context}")
        return "\n".join(lines)

    @mcp.tool(name="poni.memory.remove")
    async def memory_remove(entry_id: str) -> str:
        """Remove a memory entry.

        Args:
            entry_id: The ID of the entry to remove.

        Returns:
            Confirmation or error message.
        """
        if memory_store.remove(entry_id):
            return f"Removed {entry_id}"
        return f"Entry {entry_id} not found"

    @mcp.tool(name="poni.memory.relevant")
    async def memory_relevant(files: list[str] | None = None) -> str:
        """Get relevant memory entries for context.

        Args:
            files: Optional list of files to match against.

        Returns:
            Relevant memory entries for the current context.
        """
        entries = memory_store.get_relevant(files)
        if not entries:
            return "No relevant memory entries found."

        lines = ["Relevant team memory:"]
        for entry in entries:
            lines.append(f"- [{entry.id}] {entry.content}")
        return "\n".join(lines)
