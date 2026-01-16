"""CLI wrapper for Poni."""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import TYPE_CHECKING

from poni.config.loader import get_project_root
from poni.config.models import Config

if TYPE_CHECKING:
    from poni.mcp.policy import PolicyEngine


class CliWrapper:
    """Wrapper for CLI commands with policy enforcement."""

    def __init__(self, config: Config, policy: PolicyEngine):
        """Initialize the CLI wrapper.

        Args:
            config: The Poni configuration.
            policy: The policy engine for enforcement.
        """
        self.config = config
        self.policy = policy
        self.cli_configs = config.cli

    async def execute(self, name: str, args: str) -> str:
        """Execute a CLI command.

        Args:
            name: Name of the CLI wrapper.
            args: Command arguments as a string.

        Returns:
            Command output or error message.
        """
        cli_config = self.cli_configs.get(name)
        if not cli_config:
            return f"Error: CLI wrapper '{name}' not found"

        # Build full command
        cmd_parts = [cli_config.command] + cli_config.args
        if args:
            cmd_parts.extend(shlex.split(args))

        # Set working directory
        try:
            cwd = get_project_root()
        except FileNotFoundError:
            cwd = None

        # Build environment
        env = os.environ.copy()
        env.update(cli_config.env)

        # Execute command
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            stdout, stderr = await process.communicate()

            output = stdout.decode() if stdout else ""
            errors = stderr.decode() if stderr else ""

            if process.returncode != 0:
                # Include both stdout and stderr for error context
                full_output = output + errors
                return f"Error (exit code {process.returncode}):\n{full_output}"

            # Combine output, preferring stdout
            return output or errors or "(no output)"

        except FileNotFoundError:
            return f"Error: Command not found: {cli_config.command}"
        except Exception as e:
            return f"Error executing {name}: {e}"
