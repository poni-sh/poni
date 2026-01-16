"""Tests for policy engine."""

import pytest

from poni.config.models import (
    CliConfig,
    CliPoliciesConfig,
    Config,
    McpConfig,
    McpPoliciesConfig,
)
from poni.mcp.policy import PolicyEngine


@pytest.fixture
def policy_config() -> Config:
    """Create a config with various policy rules."""
    return Config(
        mcps={
            "filesystem": McpConfig(
                command="mcp-filesystem",
                policies=McpPoliciesConfig(
                    deny_patterns=[r"\.env", r"secrets\.json"],
                    protected_paths=["/etc/passwd", "/root"],
                ),
            ),
        },
        cli={
            "aws": CliConfig(
                command="aws",
                policies=CliPoliciesConfig(
                    allow_subcommands=["s3", "ec2"],
                    deny_patterns=[r"--recursive.*delete", r"rm\s+"],
                    require_patterns=[],
                    interactive_patterns=[r"delete", r"remove"],
                    redact_patterns=[r"AccessKeyId", r"SecretAccessKey"],
                    max_output_lines=50,
                ),
            ),
            "aws-deny": CliConfig(
                command="aws",
                policies=CliPoliciesConfig(
                    deny_subcommands=["iam", "organizations"],
                ),
            ),
            "kubectl": CliConfig(
                command="kubectl",
                policies=CliPoliciesConfig(
                    allowed_namespaces=["staging", "dev"],
                ),
            ),
            "kubectl-deny": CliConfig(
                command="kubectl",
                policies=CliPoliciesConfig(
                    denied_namespaces=["production", "kube-system"],
                ),
            ),
            "restricted": CliConfig(
                command="restricted",
                policies=CliPoliciesConfig(
                    allow_patterns=[r"^get\s", r"^list\s"],
                ),
            ),
            "required": CliConfig(
                command="required",
                policies=CliPoliciesConfig(
                    require_patterns=[r"--dry-run"],
                ),
            ),
        },
    )


@pytest.fixture
def policy(policy_config: Config) -> PolicyEngine:
    """Create a policy engine instance."""
    return PolicyEngine(policy_config)


class TestMcpToolPolicy:
    """Tests for MCP tool policy checks."""

    def test_allows_normal_call(self, policy: PolicyEngine) -> None:
        """Test that normal calls are allowed."""

    def test_blocks_deny_pattern(self, policy: PolicyEngine) -> None:
        """Test that deny patterns block calls."""
        result = policy.check_mcp_tool("filesystem", "read_file", {"path": "/home/user/.env"})
        assert result is not None
        assert "deny_patterns" in result

    def test_blocks_protected_path(self, policy: PolicyEngine) -> None:
        """Test that protected paths block calls."""
        result = policy.check_mcp_tool("filesystem", "read_file", {"path": "/etc/passwd"})
        assert result is not None
        assert "protected_paths" in result

    def test_unknown_mcp_allowed(self, policy: PolicyEngine) -> None:
        """Test that unknown MCPs are allowed."""
        result = policy.check_mcp_tool("unknown", "any_tool", {"any": "arg"})
        assert result is None


class TestCliPolicy:
    """Tests for CLI policy checks."""

    def test_allows_valid_subcommand(self, policy: PolicyEngine) -> None:
        """Test that allowed subcommands pass."""
        result = policy.check_cli("aws", "s3 ls s3://bucket")
        assert result is None

    def test_blocks_denied_subcommand(self, policy: PolicyEngine) -> None:
        """Test that denied subcommands are blocked."""
        result = policy.check_cli("aws-deny", "iam create-user --user-name test")
        assert result is not None
        assert "deny_subcommands" in result
        assert "iam" in result

    def test_blocks_unlisted_subcommand(self, policy: PolicyEngine) -> None:
        """Test that unlisted subcommands are blocked when allow_subcommands set."""
        result = policy.check_cli("aws", "lambda list-functions")
        assert result is not None
        assert "allow_subcommands" in result

    def test_blocks_deny_pattern(self, policy: PolicyEngine) -> None:
        """Test that deny patterns block commands."""
        result = policy.check_cli("aws", "s3 rm --recursive delete-bucket")
        assert result is not None
        assert "deny_patterns" in result

    def test_allow_patterns(self, policy: PolicyEngine) -> None:
        """Test that allow_patterns work correctly."""
        # Allowed
        result = policy.check_cli("restricted", "get resources")
        assert result is None

        # Blocked
        result = policy.check_cli("restricted", "delete resources")
        assert result is not None
        assert "allow_patterns" in result

    def test_require_patterns(self, policy: PolicyEngine) -> None:
        """Test that require_patterns enforce presence."""
        # Without required pattern
        result = policy.check_cli("required", "apply")
        assert result is not None
        assert "require_patterns" in result

        # With required pattern
        result = policy.check_cli("required", "apply --dry-run")
        assert result is None


class TestNamespacePolicy:
    """Tests for Kubernetes namespace policies."""

    def test_allows_valid_namespace(self, policy: PolicyEngine) -> None:
        """Test that allowed namespaces pass."""
        result = policy.check_cli("kubectl", "get pods -n staging")
        assert result is None

    def test_blocks_denied_namespace(self, policy: PolicyEngine) -> None:
        """Test that denied namespaces are blocked."""
        result = policy.check_cli("kubectl-deny", "get pods -n production")
        assert result is not None
        assert "denied_namespaces" in result
        assert "production" in result

    def test_blocks_unlisted_namespace(self, policy: PolicyEngine) -> None:
        """Test that unlisted namespaces are blocked when allowed_namespaces set."""
        result = policy.check_cli("kubectl", "get pods -n unknown")
        assert result is not None
        assert "allowed_namespaces" in result

    def test_handles_long_namespace_flag(self, policy: PolicyEngine) -> None:
        """Test that --namespace flag works."""
        result = policy.check_cli("kubectl", "get pods --namespace=staging")
        assert result is None

        result = policy.check_cli("kubectl", "get pods --namespace production")
        assert result is not None


class TestInteractiveCheck:
    """Tests for interactive confirmation check."""

    def test_detects_interactive_pattern(self, policy: PolicyEngine) -> None:
        """Test that interactive patterns are detected."""
        assert policy.check_interactive("aws", "s3 rm delete-this") is True
        assert policy.check_interactive("aws", "s3 rm remove-files") is True

    def test_normal_command_not_interactive(self, policy: PolicyEngine) -> None:
        """Test that normal commands are not interactive."""
        assert policy.check_interactive("aws", "s3 ls") is False

    def test_unknown_cli_not_interactive(self, policy: PolicyEngine) -> None:
        """Test that unknown CLIs are not interactive."""
        assert policy.check_interactive("unknown", "anything") is False


class TestRedaction:
    """Tests for output redaction."""

    def test_redacts_patterns(self, policy: PolicyEngine) -> None:
        """Test that redaction patterns are applied."""
        output = "AccessKeyId: AKIAIOSFODNN7EXAMPLE\nSecretAccessKey: wJalrXUtnFEMI/K7MDENG"
        result = policy.redact_output("aws", output)
        assert "[REDACTED]" in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result

    def test_preserves_other_content(self, policy: PolicyEngine) -> None:
        """Test that non-sensitive content is preserved."""
        output = "bucket: my-bucket\nregion: us-east-1"
        result = policy.redact_output("aws", output)
        assert "my-bucket" in result
        assert "us-east-1" in result

    def test_unknown_cli_no_redaction(self, policy: PolicyEngine) -> None:
        """Test that unknown CLIs don't get redacted."""
        output = "AccessKeyId: secret"
        result = policy.redact_output("unknown", output)
        assert result == output


class TestTruncation:
    """Tests for output truncation."""

    def test_truncates_long_output(self, policy: PolicyEngine) -> None:
        """Test that long output is truncated."""
        lines = ["line " + str(i) for i in range(100)]
        output = "\n".join(lines)
        result = policy.truncate_output("aws", output)
        assert "more lines" in result
        assert result.count("\n") < 60  # max_output_lines is 50

    def test_preserves_short_output(self, policy: PolicyEngine) -> None:
        """Test that short output is not truncated."""
        output = "line1\nline2\nline3"
        result = policy.truncate_output("aws", output)
        assert result == output

    def test_no_truncation_without_config(self, policy: PolicyEngine) -> None:
        """Test that truncation is skipped without max_output_lines."""
        lines = ["line " + str(i) for i in range(1000)]
        output = "\n".join(lines)
        result = policy.truncate_output("kubectl", output)
        assert result == output  # kubectl has no max_output_lines
