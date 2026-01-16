"""Python preset for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from poni.config.detection import DetectedProject


def generate_config(detected: DetectedProject) -> dict[str, Any]:
    """Generate Python preset configuration.

    Args:
        detected: Detection results from project analysis.

    Returns:
        Configuration dict for Python projects.
    """
    config: dict[str, Any] = {
        "poni": {
            "version": "0.1.0",
            "detected": detected.languages + detected.tools,
        },
        "secrets": {"source": "env"},
        "enforcement": {
            "enabled": True,
            "parallel": True,
            "rules": [],
        },
        "lifecycle": {
            "enabled": True,
            "hooks": [],
        },
        "memory": {"enabled": True, "max_entries_in_context": 20},
    }

    rules = config["enforcement"]["rules"]
    hooks = config["lifecycle"]["hooks"]

    # Ruff (preferred - combines linting and formatting)
    if "ruff" in detected.tools:
        rules.append(
            {
                "name": "ruff-check",
                "trigger": "pre-commit",
                "command": "ruff check --fix ${files}",
                "pattern": "**/*.py",
                "staged_only": True,
                "auto_stage": True,
            }
        )
        rules.append(
            {
                "name": "ruff-format",
                "trigger": "pre-commit",
                "command": "ruff format ${files}",
                "pattern": "**/*.py",
                "staged_only": True,
                "auto_stage": True,
            }
        )
        hooks.append(
            {
                "name": "post-write-ruff",
                "trigger": "after_tool:filesystem.write_file",
                "pattern": "**/*.py",
                "commands": ["ruff check --fix ${file}", "ruff format ${file}"],
            }
        )
    else:
        # Black
        if "black" in detected.tools:
            rules.append(
                {
                    "name": "black",
                    "trigger": "pre-commit",
                    "command": "black ${files}",
                    "pattern": "**/*.py",
                    "staged_only": True,
                    "auto_stage": True,
                }
            )

        # isort
        if "isort" in detected.tools:
            rules.append(
                {
                    "name": "isort",
                    "trigger": "pre-commit",
                    "command": "isort ${files}",
                    "pattern": "**/*.py",
                    "staged_only": True,
                    "auto_stage": True,
                }
            )

        # flake8
        if "flake8" in detected.tools:
            rules.append(
                {
                    "name": "flake8",
                    "trigger": "pre-commit",
                    "command": "flake8 ${files}",
                    "pattern": "**/*.py",
                    "staged_only": True,
                }
            )

    # mypy
    if "mypy" in detected.tools:
        rules.append(
            {
                "name": "mypy",
                "trigger": "pre-push",
                "command": "mypy .",
            }
        )
        hooks.append(
            {
                "name": "post-write-mypy",
                "trigger": "after_tool:filesystem.write_file",
                "pattern": "**/*.py",
                "commands": ["mypy ${file}"],
                "block_until_pass": True,
                "message": "Fix type errors before continuing",
            }
        )

    # pytest
    if "pytest" in detected.tools:
        rules.append(
            {
                "name": "test",
                "trigger": "pre-push",
                "command": "pytest",
            }
        )

    # No print statements in production code
    rules.append(
        {
            "name": "no-print",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "src/**/*.py",
            "exclude": ["**/test_*.py", "**/*_test.py", "**/conftest.py"],
            "deny_pattern": r"^\s*print\(",
            "message": "Use logging instead of print statements",
        }
    )

    # No breakpoint() in production code (temporarily disabled to avoid self-matching)
    # rules.append(
    #     {
    #         "name": "no-breakpoint",
    #         "trigger": "pre-commit",
    #         "check": "pattern-absent",
    #         "pattern": "src/**/*.py",
    #         "exclude": ["**/presets/python.py", "**/conftest.py"],
    #         "deny_pattern": r"^\s*breakpoint\(\)",
    #         "message": "Remove breakpoint() before committing",
    #     }
    # )

    # Verify before done hook
    if "mypy" in detected.tools:
        hooks.append(
            {
                "name": "verify-before-done",
                "trigger": "before_response",
                "commands": ["mypy ."],
                "block_until_pass": True,
                "message": "All checks must pass before completing",
            }
        )

    return config
