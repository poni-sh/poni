"""Tests for enforcement rules."""

from pathlib import Path

import pytest

from poni.config.models import Config, EnforcementConfig, EnforcementRule, PoniConfig
from poni.enforcement.rules import RuleExecutor, RuleResult


@pytest.fixture
def rule_config(tmp_path: Path) -> Config:
    """Create a config for rule testing."""
    return Config(
        poni=PoniConfig(package_manager="npm"),
        enforcement=EnforcementConfig(
            enabled=True,
            rules=[
                EnforcementRule(
                    name="echo-test",
                    trigger="pre-commit",
                    command="echo 'test'",
                ),
                EnforcementRule(
                    name="false-test",
                    trigger="pre-commit",
                    command="false",
                ),
                EnforcementRule(
                    name="pattern-check",
                    trigger="pre-commit",
                    check="pattern-absent",
                    pattern="**/*.py",
                    deny_pattern=r"print\(",
                    message="No print statements",
                ),
            ],
        ),
    )


@pytest.fixture
def executor(rule_config: Config) -> RuleExecutor:
    """Create a rule executor instance."""
    return RuleExecutor(rule_config)


class TestRuleResult:
    """Tests for RuleResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = RuleResult(rule_name="test", success=True)
        assert result.success
        assert result.rule_name == "test"

    def test_failure_result(self):
        """Test failure result with output."""
        result = RuleResult(
            rule_name="test",
            success=False,
            output="Error message",
        )
        assert not result.success
        assert result.output == "Error message"


class TestCommandRules:
    """Tests for command-based rules."""

    def test_successful_command(self, executor: RuleExecutor):
        """Test successful command execution."""
        rule = EnforcementRule(
            name="echo",
            trigger="pre-commit",
            command="echo 'hello'",
        )
        result = executor.run_rule(rule)
        assert result.success
        assert "hello" in result.output

    def test_failing_command(self, executor: RuleExecutor):
        """Test failing command execution."""
        rule = EnforcementRule(
            name="fail",
            trigger="pre-commit",
            command="false",
        )
        result = executor.run_rule(rule)
        assert not result.success

    def test_file_substitution(self, executor: RuleExecutor, tmp_path: Path):
        """Test ${files} substitution."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')")

        rule = EnforcementRule(
            name="check",
            trigger="pre-commit",
            command="cat ${files}",
            pattern="**/*.py",
        )
        result = executor.run_rule(rule, files=[str(test_file)])
        assert result.success
        assert "print" in result.output

    def test_skip_when_no_matching_files(self, executor: RuleExecutor):
        """Test that rule is skipped when no files match pattern."""
        rule = EnforcementRule(
            name="check",
            trigger="pre-commit",
            command="cat ${files}",
            pattern="**/*.py",
        )
        result = executor.run_rule(rule, files=["test.js"])
        assert result.success  # Skipped, not failed


class TestPatternRules:
    """Tests for pattern-based rules."""

    def test_pattern_absent_pass(self, executor: RuleExecutor, tmp_path: Path):
        """Test pattern-absent passes when pattern not found."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        rule = EnforcementRule(
            name="no-print",
            trigger="pre-commit",
            check="pattern-absent",
            pattern="**/*.py",
            deny_pattern=r"print\(",
        )
        result = executor.run_rule(rule, files=[str(test_file)])
        assert result.success

    def test_pattern_absent_fail(self, executor: RuleExecutor, tmp_path: Path):
        """Test pattern-absent fails when pattern found."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        rule = EnforcementRule(
            name="no-print",
            trigger="pre-commit",
            check="pattern-absent",
            pattern="**/*.py",
            deny_pattern=r"print\(",
            message="No print statements",
        )
        result = executor.run_rule(rule, files=[str(test_file)])
        assert not result.success
        assert "No print statements" in result.output

    def test_pattern_respects_exclude(self, executor: RuleExecutor, tmp_path: Path):
        """Test that exclude patterns are respected."""
        test_file = tmp_path / "test_foo.py"
        test_file.write_text("print('test')")  # Would normally fail

        rule = EnforcementRule(
            name="no-print",
            trigger="pre-commit",
            check="pattern-absent",
            pattern="**/*.py",
            exclude=["**/test_*.py"],
            deny_pattern=r"print\(",
        )
        result = executor.run_rule(rule, files=[str(test_file)])
        assert result.success  # Excluded


class TestRunAll:
    """Tests for running all rules."""

    def test_run_all_for_trigger(self, executor: RuleExecutor):
        """Test running all rules for a trigger."""
        results = executor.run_all("pre-commit")
        assert len(results) == 3  # All pre-commit rules

    def test_filters_by_trigger(self, executor: RuleExecutor):
        """Test that rules are filtered by trigger."""
        # Add a pre-push rule to config
        executor.enforcement.rules.append(
            EnforcementRule(
                name="push-only",
                trigger="pre-push",
                command="echo 'push'",
            )
        )

        pre_push = executor.run_all("pre-push")

        assert len(pre_push) == 1
        assert pre_push[0].rule_name == "push-only"

    def test_skips_disabled_rules(self, executor: RuleExecutor):
        """Test that disabled rules are skipped."""
        executor.enforcement.rules[0].enabled = False
        results = executor.run_all("pre-commit")
        assert len(results) == 2


class TestPackageManagerSubstitution:
    """Tests for package manager substitution."""

    def test_npm_substitution(self):
        """Test npm commands are substituted."""
        config = Config(
            poni=PoniConfig(package_manager="pnpm"),
            enforcement=EnforcementConfig(
                rules=[
                    EnforcementRule(
                        name="lint",
                        trigger="pre-commit",
                        command="npm run lint",
                    )
                ]
            ),
        )
        executor = RuleExecutor(config)

        # The substitution happens in _run_command_rule
        # We just verify the executor has the right package_manager
        assert executor.package_manager == "pnpm"
