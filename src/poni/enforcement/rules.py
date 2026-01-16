"""Rule execution for Poni enforcement."""

from __future__ import annotations

import fnmatch
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from poni.config.models import Config, EnforcementRule


@dataclass
class RuleResult:
    """Result of running an enforcement rule."""

    rule_name: str
    success: bool
    output: str = ""
    files_checked: list[str] = field(default_factory=list)


class RuleExecutor:
    """Executor for enforcement rules."""

    def __init__(self, config: Config):
        """Initialize the rule executor.

        Args:
            config: The Poni configuration.
        """
        self.config = config
        self.enforcement = config.enforcement
        self.package_manager = config.poni.package_manager

    def get_staged_files(self) -> list[str]:
        """Get list of files staged for commit.

        Returns:
            List of staged file paths.
        """
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            # Get staged files
            staged: list[str] = []
            for item in repo.index.diff("HEAD"):
                if item.a_path is not None:
                    staged.append(item.a_path)
            # Also include untracked files that are staged
            for item in repo.index.diff(None):
                if item.a_path is not None and item.a_path not in staged:
                    staged.append(item.a_path)
            return staged
        except Exception:
            return []

    def run_all(
        self,
        trigger: str,
        files: list[str] | None = None,
    ) -> list[RuleResult]:
        """Run all rules for a given trigger.

        Args:
            trigger: The trigger type (pre-commit, pre-push).
            files: Optional list of files to check.

        Returns:
            List of rule results.
        """
        results: list[RuleResult] = []

        for rule in self.enforcement.rules:
            if not rule.enabled:
                continue
            if rule.trigger != trigger:
                continue

            result = self.run_rule(rule, files)
            results.append(result)

        return results

    def run_rule(
        self,
        rule: EnforcementRule,
        files: list[str] | None = None,
    ) -> RuleResult:
        """Run a single enforcement rule.

        Args:
            rule: The rule to run.
            files: Optional list of files to check.

        Returns:
            The rule result.
        """
        if rule.command:
            return self._run_command_rule(rule, files)
        elif rule.check == "pattern-absent":
            return self._run_pattern_absent_rule(rule, files)
        elif rule.check == "pattern-present":
            return self._run_pattern_present_rule(rule, files)
        elif rule.check == "branch-protection":
            return self._run_branch_protection_rule(rule)
        elif rule.check == "test-coverage":
            return self._run_test_coverage_rule(rule, files)
        else:
            return RuleResult(rule_name=rule.name, success=True)

    def _run_command_rule(
        self,
        rule: EnforcementRule,
        files: list[str] | None,
    ) -> RuleResult:
        """Run a command-based rule.

        Args:
            rule: The rule to run.
            files: Optional list of files to check.

        Returns:
            The rule result.
        """
        cmd = rule.command
        if cmd is None:
            return RuleResult(rule_name=rule.name, success=True)

        # Substitute package manager
        if self.package_manager:
            cmd = cmd.replace("npm ", f"{self.package_manager} ")
            if self.package_manager == "pnpm":
                cmd = cmd.replace("npx ", "pnpm exec ")
            elif self.package_manager == "yarn":
                cmd = cmd.replace("npx ", "yarn ")
            elif self.package_manager == "bun":
                cmd = cmd.replace("npx ", "bunx ")

        # Handle ${files} substitution
        matched_files: list[str] = []
        if files and "${files}" in cmd:
            patterns = rule.pattern if isinstance(rule.pattern, list) else [rule.pattern]
            matched_files = [
                f
                for f in files
                if any(fnmatch.fnmatch(f, p) for p in patterns)
                and not any(fnmatch.fnmatch(f, e) for e in rule.exclude)
            ]

            if not matched_files:
                # No files to check, skip rule
                return RuleResult(rule_name=rule.name, success=True)

            # Quote file paths
            quoted_files = " ".join(shlex.quote(f) for f in matched_files)
            cmd = cmd.replace("${files}", quoted_files)

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return RuleResult(
                rule_name=rule.name,
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
                files_checked=matched_files,
            )
        except subprocess.TimeoutExpired:
            return RuleResult(
                rule_name=rule.name,
                success=False,
                output="Command timed out after 5 minutes",
            )
        except Exception as e:
            return RuleResult(
                rule_name=rule.name,
                success=False,
                output=str(e),
            )

    def _run_pattern_absent_rule(
        self,
        rule: EnforcementRule,
        files: list[str] | None,
    ) -> RuleResult:
        """Run a pattern-absent check rule.

        Args:
            rule: The rule to run.
            files: Optional list of files to check.

        Returns:
            The rule result.
        """
        if not rule.deny_pattern:
            return RuleResult(rule_name=rule.name, success=True)

        patterns = rule.pattern if isinstance(rule.pattern, list) else [rule.pattern]
        target_files = files or self._get_all_files()
        violations: list[str] = []

        for f in target_files:
            path = Path(f)
            if not path.is_file():
                continue
            if not any(fnmatch.fnmatch(str(path), p) for p in patterns):
                continue
            if any(fnmatch.fnmatch(str(path), e) for e in rule.exclude):
                continue

            try:
                content = path.read_text()
                if re.search(rule.deny_pattern, content):
                    violations.append(str(path))
            except (OSError, UnicodeDecodeError):
                pass

        if violations:
            msg = rule.message or f"Pattern '{rule.deny_pattern}' found in files"
            return RuleResult(
                rule_name=rule.name,
                success=False,
                output=f"{msg}\n" + "\n".join(violations[:10]),
                files_checked=violations,
            )

        return RuleResult(rule_name=rule.name, success=True)

    def _run_pattern_present_rule(
        self,
        rule: EnforcementRule,
        files: list[str] | None,
    ) -> RuleResult:
        """Run a pattern-present check rule.

        Args:
            rule: The rule to run.
            files: Optional list of files to check.

        Returns:
            The rule result.
        """
        if not rule.require_pattern:
            return RuleResult(rule_name=rule.name, success=True)

        patterns = rule.pattern if isinstance(rule.pattern, list) else [rule.pattern]
        target_files = files or self._get_all_files()
        missing: list[str] = []

        for f in target_files:
            path = Path(f)
            if not path.is_file():
                continue
            if not any(fnmatch.fnmatch(str(path), p) for p in patterns):
                continue
            if any(fnmatch.fnmatch(str(path), e) for e in rule.exclude):
                continue

            try:
                content = path.read_text()
                if not re.search(rule.require_pattern, content):
                    missing.append(str(path))
            except (OSError, UnicodeDecodeError):
                pass

        if missing:
            msg = rule.message or f"Pattern '{rule.require_pattern}' not found in files"
            return RuleResult(
                rule_name=rule.name,
                success=False,
                output=f"{msg}\n" + "\n".join(missing[:10]),
                files_checked=missing,
            )

        return RuleResult(rule_name=rule.name, success=True)

    def _run_branch_protection_rule(self, rule: EnforcementRule) -> RuleResult:
        """Run a branch protection rule.

        Args:
            rule: The rule to run.

        Returns:
            The rule result.
        """
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            branch = repo.active_branch.name
            if branch in rule.protected:
                return RuleResult(
                    rule_name=rule.name,
                    success=False,
                    output=rule.message or f"Cannot push to protected branch '{branch}'",
                )
        except Exception:
            pass

        return RuleResult(rule_name=rule.name, success=True)

    def _run_test_coverage_rule(
        self,
        rule: EnforcementRule,
        files: list[str] | None,
    ) -> RuleResult:
        """Run a test coverage rule.

        Args:
            rule: The rule to run.
            files: Optional list of files to check.

        Returns:
            The rule result.
        """
        # TODO: Implement test coverage checking
        return RuleResult(rule_name=rule.name, success=True)

    def _get_all_files(self) -> list[str]:
        """Get all files in the project.

        Returns:
            List of file paths.
        """
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            return [str(Path(repo.working_dir) / f) for f in repo.git.ls_files().split("\n") if f]
        except Exception:
            # Fallback to walking the directory
            files = []
            for path in Path.cwd().rglob("*"):
                if path.is_file() and ".git" not in path.parts:
                    files.append(str(path))
            return files
