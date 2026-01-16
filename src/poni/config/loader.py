"""Configuration loading for Poni."""

from __future__ import annotations

from pathlib import Path

import tomlkit

from poni.config.models import Config
from poni.config.secrets import resolve_secrets

PONI_DIR = ".poni"
CONFIG_FILE = "config.toml"


def find_config_path() -> Path | None:
    """Find .poni/config.toml in current or parent directories.

    Searches from the current directory upward through parent directories
    until a .poni/config.toml file is found.

    Returns:
        Path to the config file if found, None otherwise.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        config_path = parent / PONI_DIR / CONFIG_FILE
        if config_path.exists():
            return config_path
    return None


def load_config() -> Config:
    """Load and parse configuration, resolving secrets.

    Returns:
        Parsed and validated Config object.

    Raises:
        FileNotFoundError: If no .poni/config.toml is found.
        ValueError: If secrets cannot be resolved.
        ValidationError: If configuration is invalid.
    """
    config_path = find_config_path()
    if not config_path:
        raise FileNotFoundError("No .poni/config.toml found. Run 'poni init' first.")

    with open(config_path) as f:
        raw = tomlkit.load(f)

    # Convert tomlkit document to dict and resolve secrets
    config_dict = resolve_secrets(dict(raw))

    return Config.model_validate(config_dict)


def get_poni_dir() -> Path:
    """Get the .poni directory path.

    If a config file exists, returns its parent directory.
    Otherwise, returns .poni in the current directory.

    Returns:
        Path to the .poni directory.
    """
    config_path = find_config_path()
    if config_path:
        return config_path.parent
    return Path.cwd() / PONI_DIR


def get_project_root() -> Path:
    """Get the project root directory (parent of .poni).

    Returns:
        Path to the project root.

    Raises:
        FileNotFoundError: If no .poni directory is found.
    """
    config_path = find_config_path()
    if config_path:
        return config_path.parent.parent
    raise FileNotFoundError("No .poni directory found. Run 'poni init' first.")
