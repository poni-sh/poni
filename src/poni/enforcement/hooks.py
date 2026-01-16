"""Git hook management for Poni."""

from __future__ import annotations

from pathlib import Path

PRE_COMMIT_HOOK = """#!/bin/sh
# Poni pre-commit hook
exec poni enforce --hook pre-commit
"""

PRE_PUSH_HOOK = """#!/bin/sh
# Poni pre-push hook
exec poni enforce --hook pre-push
"""


def install_hooks(repo_path: Path | None = None) -> list[str]:
    """Install git hooks for Poni enforcement.

    Args:
        repo_path: Path to the repository root. Defaults to current directory.

    Returns:
        List of installed hook names.
    """
    if repo_path is None:
        repo_path = Path.cwd()

    hooks_dir = repo_path / ".git" / "hooks"
    if not hooks_dir.exists():
        return []

    installed = []

    # Install pre-commit hook
    pre_commit = hooks_dir / "pre-commit"
    _install_hook(pre_commit, PRE_COMMIT_HOOK)
    installed.append("pre-commit")

    # Install pre-push hook
    pre_push = hooks_dir / "pre-push"
    _install_hook(pre_push, PRE_PUSH_HOOK)
    installed.append("pre-push")

    return installed


def _install_hook(hook_path: Path, content: str) -> None:
    """Install a single git hook.

    Args:
        hook_path: Path to the hook file.
        content: Content of the hook script.
    """
    # Backup existing hook if it exists and wasn't created by poni
    if hook_path.exists():
        existing = hook_path.read_text()
        if "Poni" not in existing:
            backup_path = hook_path.with_suffix(".backup")
            hook_path.rename(backup_path)

    hook_path.write_text(content)
    hook_path.chmod(0o755)


def uninstall_hooks(repo_path: Path | None = None) -> list[str]:
    """Uninstall Poni git hooks.

    Args:
        repo_path: Path to the repository root. Defaults to current directory.

    Returns:
        List of uninstalled hook names.
    """
    if repo_path is None:
        repo_path = Path.cwd()

    hooks_dir = repo_path / ".git" / "hooks"
    if not hooks_dir.exists():
        return []

    uninstalled = []

    for hook_name in ["pre-commit", "pre-push"]:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            content = hook_path.read_text()
            if "Poni" in content:
                hook_path.unlink()
                uninstalled.append(hook_name)

                # Restore backup if exists
                backup_path = hook_path.with_suffix(".backup")
                if backup_path.exists():
                    backup_path.rename(hook_path)

    return uninstalled


def check_existing_hooks(repo_path: Path | None = None) -> dict[str, str]:
    """Check for existing hook systems.

    Args:
        repo_path: Path to the repository root. Defaults to current directory.

    Returns:
        Dict mapping hook system names to their paths.
    """
    if repo_path is None:
        repo_path = Path.cwd()

    existing = {}

    # Check for husky
    husky_dir = repo_path / ".husky"
    if husky_dir.exists():
        existing["husky"] = str(husky_dir)

    # Check for pre-commit (Python)
    pre_commit_config = repo_path / ".pre-commit-config.yaml"
    if pre_commit_config.exists():
        existing["pre-commit"] = str(pre_commit_config)

    # Check for lefthook
    for name in ["lefthook.yml", ".lefthook.yml", "lefthook.yaml", ".lefthook.yaml"]:
        lefthook = repo_path / name
        if lefthook.exists():
            existing["lefthook"] = str(lefthook)
            break

    # Check for lint-staged (usually in package.json)
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            import json

            with open(package_json) as f:
                pkg = json.load(f)
            if "lint-staged" in pkg:
                existing["lint-staged"] = str(package_json)
        except (json.JSONDecodeError, OSError):
            pass

    return existing


def get_hook_status(repo_path: Path | None = None) -> dict[str, bool]:
    """Check if Poni hooks are installed.

    Args:
        repo_path: Path to the repository root. Defaults to current directory.

    Returns:
        Dict mapping hook names to installation status.
    """
    if repo_path is None:
        repo_path = Path.cwd()

    hooks_dir = repo_path / ".git" / "hooks"
    status = {}

    for hook_name in ["pre-commit", "pre-push"]:
        hook_path = hooks_dir / hook_name
        if hook_path.exists():
            content = hook_path.read_text()
            status[hook_name] = "Poni" in content
        else:
            status[hook_name] = False

    return status
