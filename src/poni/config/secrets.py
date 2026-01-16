"""Secret resolution for Poni configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

SECRET_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Runtime template variables that should NOT be resolved as secrets.
# These are substituted at runtime when commands execute.
RUNTIME_TEMPLATES = frozenset(
    {
        "files",  # List of files (used in enforcement rules)
        "file",  # Single file (used in lifecycle hooks)
    }
)


def load_env_secrets() -> dict[str, str]:
    """Load secrets from .env file and environment variables.

    Environment variables override .env file values.
    """
    env_path = Path.cwd() / ".env"
    secrets: dict[str, str] = {}

    # Load from .env file first
    if env_path.exists():
        env_values = dotenv_values(env_path)
        secrets.update({k: v for k, v in env_values.items() if v is not None})

    # Environment variables override .env
    secrets.update(os.environ)

    return secrets


def resolve_secrets(obj: Any, secrets: dict[str, str] | None = None) -> Any:
    """Recursively resolve ${VAR} patterns in configuration values.

    Args:
        obj: The object to resolve (can be str, dict, list, or other)
        secrets: Optional pre-loaded secrets dict. If None, loads from environment.

    Returns:
        The object with all ${VAR} patterns resolved.

    Raises:
        ValueError: If a referenced secret is not found.
    """
    if secrets is None:
        secrets = load_env_secrets()

    if isinstance(obj, str):

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            # Skip runtime template variables - they're resolved when commands execute
            if key in RUNTIME_TEMPLATES:
                return match.group(0)  # Return original ${key} unchanged
            if key not in secrets:
                raise ValueError(
                    f"Secret '{key}' not found.\n\n"
                    f"Add it to your .env file:\n"
                    f"  {key}=your_value\n\n"
                    f"Or set as environment variable:\n"
                    f"  export {key}=your_value"
                )
            return secrets[key]

        return SECRET_PATTERN.sub(replace, obj)

    elif isinstance(obj, dict):
        return {k: resolve_secrets(v, secrets) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [resolve_secrets(item, secrets) for item in obj]

    return obj
