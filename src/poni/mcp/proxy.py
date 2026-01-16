"""MCP proxy for child MCP servers."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from poni.config.models import Config
from poni.mcp.policy import PolicyEngine


@dataclass
class ProxiedTool:
    """A tool from a child MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]


class McpProxy:
    """Proxy for managing child MCP servers."""

    def __init__(self, config: Config, policy: PolicyEngine):
        """Initialize the MCP proxy.

        Args:
            config: The Poni configuration.
            policy: The policy engine for enforcement.
        """
        self.config = config
        self.policy = policy
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self._message_id = 0

    async def start_mcp(self, name: str) -> None:
        """Start a child MCP server.

        Args:
            name: Name of the MCP server to start.
        """
        mcp_config = self.config.mcps.get(name)
        if not mcp_config:
            raise ValueError(f"MCP '{name}' not found in configuration")

        if name in self.processes:
            return  # Already running

        # Build command
        cmd = [mcp_config.command] + mcp_config.args

        # Build environment
        import os

        env = os.environ.copy()
        env.update(mcp_config.env)

        # Start process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        self.processes[name] = process

        # Initialize the MCP connection
        await self._initialize_mcp(name)

    async def stop_mcp(self, name: str) -> None:
        """Stop a child MCP server.

        Args:
            name: Name of the MCP server to stop.
        """
        if name not in self.processes:
            return

        process = self.processes[name]
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()

        del self.processes[name]

    async def stop_all(self) -> None:
        """Stop all child MCP servers."""
        for name in list(self.processes.keys()):
            await self.stop_mcp(name)

    async def get_tools(self, name: str) -> list[ProxiedTool]:
        """Get available tools from a child MCP server.

        Args:
            name: Name of the MCP server.

        Returns:
            List of available tools.
        """
        if name not in self.processes:
            await self.start_mcp(name)

        response = await self._send_request(name, "tools/list", {})

        tools: list[ProxiedTool] = []
        for tool in response.get("tools", []):
            tools.append(
                ProxiedTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
            )

        return tools

    async def call_tool(
        self,
        mcp_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a tool on a child MCP server.

        Args:
            mcp_name: Name of the MCP server.
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            Tool result.

        Raises:
            ValueError: If the call is blocked by policy.
        """
        # Check policy first
        violation = self.policy.check_mcp_tool(mcp_name, tool_name, arguments)
        if violation:
            raise ValueError(f"Policy violation: {violation}")

        if mcp_name not in self.processes:
            await self.start_mcp(mcp_name)

        response = await self._send_request(
            mcp_name,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

        return response.get("content", [])

    async def _initialize_mcp(self, name: str) -> None:
        """Initialize MCP connection with a child server.

        Args:
            name: Name of the MCP server.
        """
        # Send initialize request
        await self._send_request(
            name,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "poni", "version": "0.1.0"},
            },
        )

        # Send initialized notification
        await self._send_notification(name, "notifications/initialized", {})

    async def _send_request(
        self,
        name: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a JSON-RPC request to a child MCP server.

        Args:
            name: Name of the MCP server.
            method: The method to call.
            params: Parameters for the method.

        Returns:
            The response result.
        """
        process = self.processes.get(name)
        if not process or not process.stdin or not process.stdout:
            raise ValueError(f"MCP '{name}' is not running")

        self._message_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": method,
            "params": params,
        }

        # Send request
        request_line = json.dumps(message) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()

        # Read response
        response_line = await process.stdout.readline()
        if not response_line:
            raise ValueError(f"No response from MCP '{name}'")

        response = json.loads(response_line.decode())

        if "error" in response:
            raise ValueError(f"MCP error: {response['error']}")

        result: dict[str, Any] = response.get("result", {})
        return result

    async def _send_notification(
        self,
        name: str,
        method: str,
        params: dict[str, Any],
    ) -> None:
        """Send a JSON-RPC notification to a child MCP server.

        Args:
            name: Name of the MCP server.
            method: The method to call.
            params: Parameters for the method.
        """
        process = self.processes.get(name)
        if not process or not process.stdin:
            raise ValueError(f"MCP '{name}' is not running")

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        # Send notification (no id = notification)
        request_line = json.dumps(message) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()
