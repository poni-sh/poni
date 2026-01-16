"""Project setup detection for Poni."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectedProject:
    """Results of project detection."""

    languages: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    package_manager: str | None = None
    existing_hooks: list[str] = field(default_factory=list)


def detect_project(cwd: Path | None = None) -> DetectedProject:
    """Detect project setup from existing config files.

    Args:
        cwd: Directory to scan. Defaults to current working directory.

    Returns:
        DetectedProject with detected languages, tools, package manager, and hooks.
    """
    result = DetectedProject()
    if cwd is None:
        cwd = Path.cwd()

    # JavaScript/TypeScript detection
    _detect_js_project(cwd, result)

    # Python detection
    _detect_python_project(cwd, result)

    # Rust detection
    _detect_rust_project(cwd, result)

    # Go detection
    _detect_go_project(cwd, result)

    # Detect existing hooks
    _detect_existing_hooks(cwd, result)

    return result


def _detect_js_project(cwd: Path, result: DetectedProject) -> None:
    """Detect JavaScript/TypeScript project setup."""
    package_json = cwd / "package.json"
    if not package_json.exists():
        return

    try:
        with open(package_json) as f:
            pkg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    all_deps: dict[str, str] = {
        **pkg.get("dependencies", {}),
        **pkg.get("devDependencies", {}),
    }

    # Detect language
    if "typescript" in all_deps:
        result.languages.append("typescript")
    else:
        result.languages.append("javascript")

    # Detect tools
    if "eslint" in all_deps:
        result.tools.append("eslint")
    if "prettier" in all_deps:
        result.tools.append("prettier")
    if "biome" in all_deps or "@biomejs/biome" in all_deps:
        result.tools.append("biome")
    if "jest" in all_deps:
        result.tools.append("jest")
    if "vitest" in all_deps:
        result.tools.append("vitest")
    if "mocha" in all_deps:
        result.tools.append("mocha")

    # Detect package manager
    if (cwd / "pnpm-lock.yaml").exists():
        result.package_manager = "pnpm"
    elif (cwd / "yarn.lock").exists():
        result.package_manager = "yarn"
    elif (cwd / "bun.lockb").exists():
        result.package_manager = "bun"
    elif (cwd / "package-lock.json").exists():
        result.package_manager = "npm"
    else:
        result.package_manager = "npm"


def _detect_python_project(cwd: Path, result: DetectedProject) -> None:
    """Detect Python project setup."""
    pyproject = cwd / "pyproject.toml"
    if not pyproject.exists():
        return

    result.languages.append("python")

    try:
        content = pyproject.read_text()
    except OSError:
        return

    # Detect tools from pyproject.toml content
    if "ruff" in content:
        result.tools.append("ruff")
    if "black" in content:
        result.tools.append("black")
    if "mypy" in content:
        result.tools.append("mypy")
    if "pytest" in content:
        result.tools.append("pytest")
    if "flake8" in content:
        result.tools.append("flake8")
    if "isort" in content:
        result.tools.append("isort")


def _detect_rust_project(cwd: Path, result: DetectedProject) -> None:
    """Detect Rust project setup."""
    if (cwd / "Cargo.toml").exists():
        result.languages.append("rust")
        result.tools.extend(["rustfmt", "clippy"])


def _detect_go_project(cwd: Path, result: DetectedProject) -> None:
    """Detect Go project setup."""
    if not (cwd / "go.mod").exists():
        return

    result.languages.append("go")

    if (cwd / ".golangci.yml").exists() or (cwd / ".golangci.yaml").exists():
        result.tools.append("golangci-lint")


def _detect_existing_hooks(cwd: Path, result: DetectedProject) -> None:
    """Detect existing git hook systems."""
    if (cwd / ".husky").exists():
        result.existing_hooks.append("husky")
    if (cwd / ".pre-commit-config.yaml").exists():
        result.existing_hooks.append("pre-commit")
    if (cwd / "lefthook.yml").exists() or (cwd / ".lefthook.yml").exists():
        result.existing_hooks.append("lefthook")
