"""Policy enforcement for Poni."""

from __future__ import annotations

import re

from poni.config.models import Config


class PolicyEngine:
    """Engine for checking and enforcing policies on tool calls."""

    def __init__(self, config: Config):
        """Initialize the policy engine.

        Args:
            config: The Poni configuration.
        """
        self.config = config

    def check_mcp_tool(self, mcp_name: str, tool_name: str, args: dict[str, object]) -> str | None:
        """Check if an MCP tool call is allowed.

        Args:
            mcp_name: Name of the MCP server.
            tool_name: Name of the tool being called.
            args: Arguments to the tool.

        Returns:
            Violation message if blocked, None if allowed.
        """
        mcp_config = self.config.mcps.get(mcp_name)
        if not mcp_config:
            return None

        # Check deny patterns
        args_str = str(args)
        for pattern in mcp_config.policies.deny_patterns:
            if re.search(pattern, args_str, re.IGNORECASE):
                return (
                    f"Blocked by: deny_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Input matched a denied pattern."
                )

        # Check protected paths
        for protected in mcp_config.policies.protected_paths:
            for value in args.values():
                if isinstance(value, str) and protected in value:
                    return (
                        f"Blocked by: protected_paths\n"
                        f"Path: {protected}\n"
                        f"Cannot access protected path."
                    )

        return None

    def check_cli(self, cli_name: str, args: str) -> str | None:
        """Check if a CLI command is allowed.

        Args:
            cli_name: Name of the CLI wrapper.
            args: Command arguments as a string.

        Returns:
            Violation message if blocked, None if allowed.
        """
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return None

        policies = cli_config.policies

        # Check subcommands
        parts = args.split()
        if parts:
            subcommand = parts[0]

            if policies.allow_subcommands and subcommand not in policies.allow_subcommands:
                return (
                    f"Blocked by: allow_subcommands\n"
                    f"Subcommand '{subcommand}' is not in the allow list.\n"
                    f"Allowed: {', '.join(policies.allow_subcommands)}"
                )

            if policies.deny_subcommands and subcommand in policies.deny_subcommands:
                return f"Blocked by: deny_subcommands\nSubcommand '{subcommand}' is blocked."

        # Check deny patterns
        for pattern in policies.deny_patterns:
            if re.search(pattern, args, re.IGNORECASE):
                return (
                    f"Blocked by: deny_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Command matched a denied pattern."
                )

        # Check allow patterns (if specified, command must match at least one)
        if policies.allow_patterns:
            matched = False
            for pattern in policies.allow_patterns:
                if re.search(pattern, args, re.IGNORECASE):
                    matched = True
                    break
            if not matched:
                return (
                    f"Blocked by: allow_patterns\n"
                    f"Command did not match any allowed pattern.\n"
                    f"Allowed patterns: {', '.join(policies.allow_patterns)}"
                )

        # Check require patterns (command must match all)
        for pattern in policies.require_patterns:
            if not re.search(pattern, args, re.IGNORECASE):
                return (
                    f"Blocked by: require_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Command must match this pattern."
                )

        # Check namespaces (for kubectl, etc.)
        if policies.allowed_namespaces or policies.denied_namespaces:
            ns_match = re.search(r"-n\s+(\S+)|--namespace[=\s]+(\S+)", args)
            if ns_match:
                namespace = ns_match.group(1) or ns_match.group(2)

                if policies.allowed_namespaces and namespace not in policies.allowed_namespaces:
                    return (
                        f"Blocked by: allowed_namespaces\n"
                        f"Namespace '{namespace}' is not allowed.\n"
                        f"Allowed: {', '.join(policies.allowed_namespaces)}"
                    )

                if policies.denied_namespaces and namespace in policies.denied_namespaces:
                    return f"Blocked by: denied_namespaces\nNamespace '{namespace}' is blocked."

        return None

    def check_interactive(self, cli_name: str, args: str) -> bool:
        """Check if a command requires interactive confirmation.

        Args:
            cli_name: Name of the CLI wrapper.
            args: Command arguments as a string.

        Returns:
            True if confirmation is required, False otherwise.
        """
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return False

        for pattern in cli_config.policies.interactive_patterns:
            if re.search(pattern, args, re.IGNORECASE):
                return True

        return False

    def redact_output(self, cli_name: str, output: str) -> str:
        """Redact sensitive patterns from command output.

        Args:
            cli_name: Name of the CLI wrapper.
            output: The command output to redact.

        Returns:
            Output with sensitive values redacted.
        """
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return output

        for pattern in cli_config.policies.redact_patterns:
            output = re.sub(
                f"({pattern})\\s*[=:]?\\s*\\S+",
                r"\1=[REDACTED]",
                output,
                flags=re.IGNORECASE,
            )

        return output

    def truncate_output(self, cli_name: str, output: str) -> str:
        """Truncate output to max lines if configured.

        Args:
            cli_name: Name of the CLI wrapper.
            output: The command output to truncate.

        Returns:
            Truncated output if over limit, original otherwise.
        """
        cli_config = self.config.cli.get(cli_name)
        if not cli_config or not cli_config.policies.max_output_lines:
            return output

        lines = output.split("\n")
        max_lines = cli_config.policies.max_output_lines
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n\n... ({len(lines) - max_lines} more lines)"

        return output
