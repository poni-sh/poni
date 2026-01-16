"""TypeScript preset for Poni."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from poni.config.detection import DetectedProject


def generate_config(detected: DetectedProject) -> dict[str, Any]:
    """Generate TypeScript preset configuration.

    Args:
        detected: Detection results from project analysis.

    Returns:
        Configuration dict for TypeScript projects.
    """
    pm = detected.package_manager or "npm"
    exec_cmd = f"{pm} exec" if pm == "pnpm" else "npx"

    if pm == "bun":
        exec_cmd = "bunx"

    config: dict[str, Any] = {
        "poni": {
            "version": "0.1.0",
            "detected": detected.languages + detected.tools,
            "package_manager": pm,
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

    # Add rules based on detected tools

    # ESLint
    if "eslint" in detected.tools:
        rules.append(
            {
                "name": "eslint",
                "trigger": "pre-commit",
                "command": f"{exec_cmd} eslint --fix ${{files}}",
                "pattern": "**/*.{ts,tsx,js,jsx}",
                "staged_only": True,
                "auto_stage": True,
            }
        )
        hooks.append(
            {
                "name": "post-write-eslint",
                "trigger": "after_tool:filesystem.write_file",
                "pattern": "**/*.{ts,tsx}",
                "commands": [f"{exec_cmd} eslint --fix ${{file}}"],
            }
        )

    # Prettier
    if "prettier" in detected.tools:
        rules.append(
            {
                "name": "prettier",
                "trigger": "pre-commit",
                "command": f"{exec_cmd} prettier --write ${{files}}",
                "pattern": "**/*.{ts,tsx,js,jsx,json,md}",
                "staged_only": True,
                "auto_stage": True,
            }
        )

    # Biome
    if "biome" in detected.tools:
        rules.append(
            {
                "name": "biome",
                "trigger": "pre-commit",
                "command": f"{exec_cmd} biome check --apply ${{files}}",
                "pattern": "**/*.{ts,tsx,js,jsx,json}",
                "staged_only": True,
                "auto_stage": True,
            }
        )

    # TypeScript check
    if "typescript" in detected.languages:
        rules.append(
            {
                "name": "typecheck",
                "trigger": "pre-push",
                "command": f"{exec_cmd} tsc --noEmit",
            }
        )
        hooks.append(
            {
                "name": "post-write-typecheck",
                "trigger": "after_tool:filesystem.write_file",
                "pattern": "**/*.{ts,tsx}",
                "commands": [f"{exec_cmd} tsc --noEmit"],
                "block_until_pass": True,
                "message": "Fix type errors before continuing",
            }
        )

    # Test runner
    if "vitest" in detected.tools:
        rules.append(
            {
                "name": "test",
                "trigger": "pre-push",
                "command": f"{exec_cmd} vitest run",
            }
        )
    elif "jest" in detected.tools:
        rules.append(
            {
                "name": "test",
                "trigger": "pre-push",
                "command": f"{exec_cmd} jest",
            }
        )

    # No console.log rule
    rules.append(
        {
            "name": "no-console",
            "trigger": "pre-commit",
            "check": "pattern-absent",
            "pattern": "src/**/*.{ts,tsx}",
            "exclude": ["**/*.test.*", "**/*.spec.*"],
            "deny_pattern": r"console\.(log|debug|info)\(",
            "message": "Use logger instead of console methods",
        }
    )

    # Verify before done hook
    hooks.append(
        {
            "name": "verify-before-done",
            "trigger": "before_response",
            "commands": [f"{exec_cmd} tsc --noEmit"],
            "block_until_pass": True,
            "message": "All checks must pass before completing",
        }
    )

    return config
