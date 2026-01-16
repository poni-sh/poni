"""Lifecycle hook execution for Poni."""

from __future__ import annotations

import asyncio
import fnmatch
from dataclasses import dataclass
from typing import Any

from poni.config.models import Config, LifecycleHook


@dataclass
class LifecycleResult:
    """Result of running a lifecycle hook."""

    hook_name: str
    success: bool
    output: str = ""
    attempts: int = 1


class LifecycleEngine:
    """Engine for executing lifecycle hooks."""

    def __init__(self, config: Config):
        """Initialize the lifecycle engine.

        Args:
            config: The Poni configuration.
        """
        self.config = config
        self.lifecycle = config.lifecycle

    def matches_trigger(self, hook: LifecycleHook, trigger: str) -> bool:
        """Check if a hook matches a trigger pattern.

        Args:
            hook: The lifecycle hook.
            trigger: The trigger string (e.g., "after_tool:filesystem.write_file").

        Returns:
            True if the hook matches the trigger.
        """
        if hook.trigger == trigger:
            return True

        # Wildcard matching: "after_tool:*" matches "after_tool:filesystem.write_file"
        if hook.trigger.endswith(":*"):
            prefix = hook.trigger[:-1]  # "after_tool:"
            return trigger.startswith(prefix)

        return False

    def matches_file(self, hook: LifecycleHook, file_path: str | None) -> bool:
        """Check if a hook's file pattern matches the given file.

        Args:
            hook: The lifecycle hook.
            file_path: The file path to check.

        Returns:
            True if the file matches the hook's pattern.
        """
        if file_path is None:
            return True

        patterns = hook.pattern if isinstance(hook.pattern, list) else [hook.pattern]
        return any(fnmatch.fnmatch(file_path, p) for p in patterns)

    async def run_hooks(
        self,
        trigger: str,
        file_path: str | None = None,
    ) -> list[LifecycleResult]:
        """Run all hooks matching the trigger.

        Args:
            trigger: The trigger type (e.g., "after_tool:filesystem.write_file").
            file_path: Optional file path that triggered the hook.

        Returns:
            List of hook results.
        """
        if not self.lifecycle.enabled:
            return []

        results: list[LifecycleResult] = []

        for hook in self.lifecycle.hooks:
            if not self.matches_trigger(hook, trigger):
                continue
            if not self.matches_file(hook, file_path):
                continue

            result = await self.run_hook(hook, file_path)
            results.append(result)

            # If block_until_pass and failed, stop processing
            if hook.block_until_pass and not result.success:
                break

        return results

    async def run_hook(
        self,
        hook: LifecycleHook,
        file_path: str | None = None,
    ) -> LifecycleResult:
        """Run a single lifecycle hook with retry logic.

        Args:
            hook: The hook to run.
            file_path: Optional file path for substitution.

        Returns:
            The hook result.
        """
        attempts = 0
        max_attempts = hook.max_retries if hook.block_until_pass else 1
        last_output = ""

        while attempts < max_attempts:
            attempts += 1
            success = True
            outputs: list[str] = []

            # Run commands
            for command in hook.commands:
                cmd = self._substitute_file(command, file_path)
                result = await self._run_command(cmd)
                outputs.append(result["output"])
                if not result["success"]:
                    success = False
                    break

            # Run checks
            if success:
                for check in hook.checks:
                    result = await self._run_check(check, file_path)
                    outputs.append(result["output"])
                    if not result["success"]:
                        success = False
                        break

            last_output = "\n".join(outputs)

            if success or not hook.block_until_pass:
                break

            # Wait before retry
            if attempts < max_attempts:
                await asyncio.sleep(1)

        return LifecycleResult(
            hook_name=hook.name,
            success=success,
            output=last_output,
            attempts=attempts,
        )

    def _substitute_file(self, command: str, file_path: str | None) -> str:
        """Substitute ${file} in command.

        Args:
            command: The command string.
            file_path: The file path to substitute.

        Returns:
            Command with substitution applied.
        """
        if file_path and "${file}" in command:
            return command.replace("${file}", file_path)
        return command

    async def _run_command(self, command: str) -> dict[str, Any]:
        """Run a shell command.

        Args:
            command: The command to run.

        Returns:
            Dict with success and output.
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            return {"success": process.returncode == 0, "output": output}
        except Exception as e:
            return {"success": False, "output": str(e)}

    async def _run_check(self, check: str, file_path: str | None) -> dict[str, Any]:
        """Run a check command.

        Args:
            check: The check to run.
            file_path: Optional file path for substitution.

        Returns:
            Dict with success and output.
        """
        # For now, treat checks as commands
        cmd = self._substitute_file(check, file_path)
        return await self._run_command(cmd)
