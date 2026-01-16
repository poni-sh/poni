"""Tool execution for Poni."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from poni.config.loader import get_project_root
from poni.config.models import Config


class ToolExecutor:
    """Executor for custom team tools."""

    def __init__(self, config: Config):
        """Initialize the tool executor.

        Args:
            config: The Poni configuration.
        """
        self.config = config
        self.tools = config.tools

    async def execute(self, name: str, kwargs: dict[str, Any]) -> str:
        """Execute a custom tool.

        Args:
            name: Name of the tool.
            kwargs: Tool arguments.

        Returns:
            Tool output or error message.
        """
        tool_config = self.tools.get(name)
        if not tool_config:
            return f"Error: Tool '{name}' not found"

        # Check branch restrictions
        if tool_config.allowed_branches:
            current_branch = self._get_current_branch()
            if current_branch and current_branch not in tool_config.allowed_branches:
                return (
                    f"Error: Tool '{name}' is only allowed on branches: "
                    f"{', '.join(tool_config.allowed_branches)}\n"
                    f"Current branch: {current_branch}"
                )

        # Check confirmation requirement
        if tool_config.confirm:
            message = tool_config.confirm_message or f"Execute {name}?"
            return f"CONFIRMATION_REQUIRED: {message}"

        # Build command
        cmd_parts = [tool_config.command] + tool_config.args

        # Add optional args if provided
        for opt_arg in tool_config.optional_args:
            # Check if arg name (without --) is in kwargs
            arg_name = opt_arg.lstrip("-").replace("-", "_")
            if arg_name in kwargs:
                value = kwargs[arg_name]
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append(opt_arg)
                else:
                    cmd_parts.append(opt_arg)
                    cmd_parts.append(str(value))

        # Set working directory
        if tool_config.working_dir:
            try:
                cwd = get_project_root() / tool_config.working_dir
            except FileNotFoundError:
                cwd = None
        else:
            try:
                cwd = get_project_root()
            except FileNotFoundError:
                cwd = None

        # Build environment
        env = os.environ.copy()
        env.update(tool_config.env)

        # Execute command
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=tool_config.timeout,
                )
            except TimeoutError:
                process.kill()
                return f"Error: Tool '{name}' timed out after {tool_config.timeout} seconds"

            output = stdout.decode() if stdout else ""
            errors = stderr.decode() if stderr else ""

            if process.returncode != 0:
                return f"Error (exit code {process.returncode}):\n{errors or output}"

            return output or "(no output)"

        except FileNotFoundError:
            return f"Error: Command not found: {tool_config.command}"
        except Exception as e:
            return f"Error executing {name}: {e}"

    def _get_current_branch(self) -> str | None:
        """Get the current git branch.

        Returns:
            Branch name or None if not in a git repo.
        """
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            return repo.active_branch.name
        except Exception:
            return None
