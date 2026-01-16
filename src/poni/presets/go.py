"""Go preset for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from poni.config.detection import DetectedProject


def generate_config(detected: DetectedProject) -> dict[str, Any]:
    """Generate Go preset configuration.

    Args:
        detected: Detection results from project analysis.

    Returns:
        Configuration dict for Go projects.
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

    # go fmt
    rules.append(
        {
            "name": "gofmt",
            "trigger": "pre-commit",
            "command": "gofmt -w ${files}",
            "pattern": "**/*.go",
            "staged_only": True,
            "auto_stage": True,
        }
    )
    hooks.append(
        {
            "name": "post-write-gofmt",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.go",
            "commands": ["gofmt -w ${file}"],
        }
    )

    # go vet
    rules.append(
        {
            "name": "govet",
            "trigger": "pre-commit",
            "command": "go vet ./...",
        }
    )
    hooks.append(
        {
            "name": "post-write-govet",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.go",
            "commands": ["go vet ./..."],
            "block_until_pass": True,
            "message": "Fix go vet warnings before continuing",
        }
    )

    # golangci-lint (if detected)
    if "golangci-lint" in detected.tools:
        rules.append(
            {
                "name": "golangci-lint",
                "trigger": "pre-commit",
                "command": "golangci-lint run",
            }
        )
        hooks.append(
            {
                "name": "post-write-golangci",
                "trigger": "after_tool:filesystem.write_file",
                "pattern": "**/*.go",
                "commands": ["golangci-lint run"],
                "block_until_pass": True,
                "message": "Fix linter warnings before continuing",
            }
        )

    # go build
    rules.append(
        {
            "name": "build",
            "trigger": "pre-push",
            "command": "go build ./...",
        }
    )

    # go test
    rules.append(
        {
            "name": "test",
            "trigger": "pre-push",
            "command": "go test ./...",
        }
    )

    # No fmt.Print in production code
    rules.append(
        {
            "name": "no-fmt-print",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "**/*.go",
            "exclude": ["**/*_test.go", "**/main.go"],
            "deny_pattern": r"fmt\.Print",
            "message": "Use logging instead of fmt.Print",
        }
    )

    # No panic in library code
    rules.append(
        {
            "name": "no-panic",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "**/*.go",
            "exclude": ["**/*_test.go", "**/main.go"],
            "deny_pattern": r"\bpanic\(",
            "message": "Return errors instead of panicking in library code",
        }
    )

    # Verify before done hook
    hooks.append(
        {
            "name": "verify-before-done",
            "trigger": "before_response",
            "commands": ["go build ./...", "go vet ./..."],
            "block_until_pass": True,
            "message": "All checks must pass before completing",
        }
    )

    return config
