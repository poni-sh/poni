"""Rust preset for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from poni.config.detection import DetectedProject


def generate_config(detected: DetectedProject) -> dict[str, Any]:
    """Generate Rust preset configuration.

    Args:
        detected: Detection results from project analysis.

    Returns:
        Configuration dict for Rust projects.
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

    # rustfmt
    rules.append(
        {
            "name": "rustfmt",
            "trigger": "pre-commit",
            "command": "cargo fmt -- --check",
        }
    )
    hooks.append(
        {
            "name": "post-write-rustfmt",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.rs",
            "commands": ["cargo fmt"],
        }
    )

    # clippy
    rules.append(
        {
            "name": "clippy",
            "trigger": "pre-commit",
            "command": "cargo clippy -- -D warnings",
        }
    )
    hooks.append(
        {
            "name": "post-write-clippy",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.rs",
            "commands": ["cargo clippy -- -D warnings"],
            "block_until_pass": True,
            "message": "Fix clippy warnings before continuing",
        }
    )

    # cargo check
    rules.append(
        {
            "name": "check",
            "trigger": "pre-push",
            "command": "cargo check",
        }
    )

    # cargo test
    rules.append(
        {
            "name": "test",
            "trigger": "pre-push",
            "command": "cargo test",
        }
    )

    # No println! in library code (optional, commented out by default)
    # rules.append({
    #     "name": "no-println",
    #     "trigger": "pre-commit",
    #     "check": "pattern-absent",
    #     "pattern": "src/**/*.rs",
    #     "exclude": ["**/main.rs", "**/bin/*.rs"],
    #     "deny_pattern": r"println!\(",
    #     "message": "Use tracing/log instead of println! in library code",
    # })

    # No dbg! macros
    rules.append(
        {
            "name": "no-dbg",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "**/*.rs",
            "deny_pattern": r"dbg!\(",
            "message": "Remove dbg! macros before committing",
        }
    )

    # No todo! macros in commits
    rules.append(
        {
            "name": "no-todo",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "**/*.rs",
            "deny_pattern": r"todo!\(",
            "message": "Resolve todo! macros before committing",
        }
    )

    # Verify before done hook
    hooks.append(
        {
            "name": "verify-before-done",
            "trigger": "before_response",
            "commands": ["cargo check", "cargo clippy -- -D warnings"],
            "block_until_pass": True,
            "message": "All checks must pass before completing",
        }
    )

    return config
