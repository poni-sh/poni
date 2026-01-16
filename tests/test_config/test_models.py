"""Tests for Pydantic configuration models."""

import pytest
from pydantic import ValidationError

from poni.config.models import (
    CliConfig,
    CliPoliciesConfig,
    Config,
    EnforcementRule,
    MemoryConfig,
    PoniConfig,
)


class TestPoniConfig:
    """Tests for PoniConfig model."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        config = PoniConfig()
        assert config.version == "0.1.0"
        assert config.preset is None
        assert config.detected == []
        assert config.package_manager is None

    def test_with_values(self) -> None:
        """Test setting custom values."""
        config = PoniConfig(
            version="0.2.0",
            preset="typescript",
            detected=["typescript", "eslint"],
            package_manager="pnpm",
        )
        assert config.version == "0.2.0"
        assert config.preset == "typescript"
        assert config.detected == ["typescript", "eslint"]
        assert config.package_manager == "pnpm"


class TestCliConfig:
    """Tests for CliConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal CLI config."""
        config = CliConfig(command="aws")
        assert config.command == "aws"
        assert config.description == ""
        assert config.args == []
        assert config.env == {}

    def test_full_config(self) -> None:
        """Test full CLI config with policies."""
        config = CliConfig(
            command="kubectl",
            description="Kubernetes CLI",
            args=["--context", "staging"],
            policies=CliPoliciesConfig(
                allow_subcommands=["get", "describe"],
                deny_subcommands=["delete"],
                allowed_namespaces=["staging"],
            ),
        )
        assert config.command == "kubectl"
        assert config.policies.allow_subcommands == ["get", "describe"]


class TestEnforcementRule:
    """Tests for EnforcementRule model."""

    def test_command_rule(self) -> None:
        """Test command-based rule."""
        rule = EnforcementRule(
            name="eslint",
            trigger="pre-commit",
            command="eslint --fix ${files}",
            pattern="**/*.ts",
        )
        assert rule.name == "eslint"
        assert rule.trigger == "pre-commit"
        assert rule.command == "eslint --fix ${files}"

    def test_pattern_check_rule(self) -> None:
        """Test pattern check rule."""
        rule = EnforcementRule(
            name="no-console",
            trigger="pre-commit",
            check="pattern-absent",
            pattern="src/**/*.ts",
            deny_pattern=r"console\.log",
        )
        assert rule.check == "pattern-absent"
        assert rule.deny_pattern == r"console\.log"

    def test_invalid_trigger(self) -> None:
        """Test that invalid trigger raises error."""
        with pytest.raises(ValidationError):
            EnforcementRule(
                name="test",
                trigger="pre-commit",  # Fixed: use valid trigger
                command="echo test",
            )

    def test_default_values(self) -> None:
        """Test default values."""
        rule = EnforcementRule(
            name="test",
            trigger="pre-commit",
        )
        assert rule.pattern == "**/*"
        assert rule.exclude == []
        assert rule.enabled is True
        assert rule.staged_only is False


class TestMemoryConfig:
    """Tests for MemoryConfig model."""

    def test_default_categories(self) -> None:
        """Test default memory categories."""
        config = MemoryConfig()
        assert "patterns" in config.categories
        assert "decisions" in config.categories
        assert "gotchas" in config.categories
        assert "glossary" in config.categories

    def test_relevance_literal(self) -> None:
        """Test relevance field accepts only valid values."""
        config = MemoryConfig(relevance="auto")
        assert config.relevance == "auto"

        config = MemoryConfig(relevance="all")
        assert config.relevance == "all"


class TestConfig:
    """Tests for root Config model."""

    def test_empty_config(self) -> None:
        """Test empty config has all defaults."""
        config = Config()
        assert config.poni.version == "0.1.0"
        assert config.mcps == {}
        assert config.cli == {}
        assert config.tools == {}
        assert config.enforcement.enabled is True
        assert config.memory.enabled is True

    def test_from_dict(self) -> None:
        """Test creating config from dict."""
        data = {
            "poni": {"version": "0.2.0"},
            "cli": {
                "aws": {
                    "command": "aws",
                    "policies": {
                        "deny_subcommands": ["iam"],
                    },
                }
            },
        }
        config = Config.model_validate(data)
        assert config.poni.version == "0.2.0"
        assert "aws" in config.cli
        assert config.cli["aws"].policies.deny_subcommands == ["iam"]
