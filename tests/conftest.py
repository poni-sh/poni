"""Shared test fixtures for Poni tests."""

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomlkit

if TYPE_CHECKING:
    import git

from poni.config.models import (
    CliConfig,
    CliPoliciesConfig,
    Config,
    EnforcementConfig,
    EnforcementRule,
    McpConfig,
    McpPoliciesConfig,
    MemoryConfig,
    PoniConfig,
    ToolConfig,
)


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def poni_dir(tmp_path: Path) -> Path:
    """Create a .poni directory structure."""
    poni = tmp_path / ".poni"
    poni.mkdir()
    (poni / "memory").mkdir()
    (poni / "prompts").mkdir()
    (poni / "docs").mkdir()
    return poni


@pytest.fixture
def sample_config() -> Config:
    """Create a sample configuration for testing."""
    return Config(
        poni=PoniConfig(
            version="0.1.0",
            detected=["python", "ruff", "pytest"],
            package_manager="pip",
        ),
        mcps={
            "filesystem": McpConfig(
                command="mcp-filesystem",
                args=["--root", "/project"],
                policies=McpPoliciesConfig(
                    deny_patterns=[r"\.env", r"secrets"],
                    protected_paths=["/etc", "/var"],
                ),
            ),
        },
        cli={
            "aws": CliConfig(
                description="AWS CLI",
                command="aws",
                policies=CliPoliciesConfig(
                    deny_subcommands=["iam", "organizations"],
                    allow_subcommands=["s3", "ec2", "lambda"],
                    deny_patterns=[r"--recursive.*delete"],
                    interactive_patterns=[r"delete", r"remove"],
                    redact_patterns=[r"AccessKeyId", r"SecretAccessKey"],
                    max_output_lines=100,
                ),
            ),
            "kubectl": CliConfig(
                description="Kubernetes CLI",
                command="kubectl",
                policies=CliPoliciesConfig(
                    allowed_namespaces=["staging", "dev"],
                    denied_namespaces=["production", "kube-system"],
                ),
            ),
        },
        tools={
            "deploy": ToolConfig(
                description="Deploy to staging",
                command="deploy.sh",
                args=["--env", "staging"],
                confirm=True,
                confirm_message="Deploy to staging?",
                allowed_branches=["main", "release/*"],
                timeout=300,
            ),
        },
        enforcement=EnforcementConfig(
            enabled=True,
            parallel=True,
            rules=[
                EnforcementRule(
                    name="ruff",
                    trigger="pre-commit",
                    command="ruff check --fix ${files}",
                    pattern="**/*.py",
                    staged_only=True,
                ),
                EnforcementRule(
                    name="no-print",
                    trigger="pre-commit",
                    check="pattern-absent",
                    pattern="src/**/*.py",
                    deny_pattern=r"print\(",
                    message="Use logging instead",
                ),
                EnforcementRule(
                    name="branch-protection",
                    trigger="pre-push",
                    check="branch-protection",
                    protected=["main", "production"],
                ),
            ],
        ),
        memory=MemoryConfig(
            enabled=True,
            max_entries_in_context=20,
            categories=["patterns", "decisions", "gotchas"],
        ),
    )


@pytest.fixture
def config_file(poni_dir: Path, sample_config: Config) -> Path:
    """Create a config.toml file."""
    config_path = poni_dir / "config.toml"
    config_dict = sample_config.model_dump()
    with open(config_path, "w") as f:
        tomlkit.dump(config_dict, f)
    return config_path


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[tuple[Path, "git.Repo"], None, None]:
    """Create a temporary git repository."""
    import git

    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    yield tmp_path, repo


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    """Create a .env file with test secrets."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "API_KEY=test_api_key\n"
        "SECRET_TOKEN=test_secret_token\n"
        "DATABASE_URL=postgres://localhost/test\n"
    )
    return env_path
