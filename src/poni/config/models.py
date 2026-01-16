"""Pydantic models for Poni configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SecretsConfig(BaseModel):
    """Configuration for secret resolution."""

    source: Literal["env"] = "env"


class McpToolsConfig(BaseModel):
    """Tool filtering for MCP servers."""

    allow: list[str] | None = None
    deny: list[str] | None = None


class McpPoliciesConfig(BaseModel):
    """Policy configuration for MCP servers."""

    deny_patterns: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)


class McpConfig(BaseModel):
    """Configuration for a child MCP server."""

    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    tools: McpToolsConfig = Field(default_factory=McpToolsConfig)
    policies: McpPoliciesConfig = Field(default_factory=McpPoliciesConfig)


class CliPoliciesConfig(BaseModel):
    """Policy configuration for CLI wrappers."""

    allow_subcommands: list[str] = Field(default_factory=list)
    deny_subcommands: list[str] = Field(default_factory=list)
    allow_patterns: list[str] = Field(default_factory=list)
    deny_patterns: list[str] = Field(default_factory=list)
    require_patterns: list[str] = Field(default_factory=list)
    interactive_patterns: list[str] = Field(default_factory=list)
    redact_patterns: list[str] = Field(default_factory=list)
    allowed_namespaces: list[str] = Field(default_factory=list)
    denied_namespaces: list[str] = Field(default_factory=list)
    max_output_lines: int | None = None


class CliConfig(BaseModel):
    """Configuration for a CLI wrapper."""

    description: str = ""
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    policies: CliPoliciesConfig = Field(default_factory=CliPoliciesConfig)


class ToolConfig(BaseModel):
    """Configuration for a custom team tool."""

    description: str = ""
    command: str
    args: list[str] = Field(default_factory=list)
    optional_args: list[str] = Field(default_factory=list)
    working_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    confirm: bool = False
    confirm_message: str | None = None
    allowed_branches: list[str] = Field(default_factory=list)
    timeout: int = 60


class EnforcementRule(BaseModel):
    """Configuration for an enforcement rule."""

    name: str
    trigger: Literal["pre-commit", "pre-push"]
    command: str | None = None
    check: str | None = None  # "pattern-absent", "pattern-present", "test-coverage", etc.
    pattern: str | list[str] = "**/*"
    exclude: list[str] = Field(default_factory=list)
    deny_pattern: str | None = None
    require_pattern: str | None = None
    test_pattern: str | None = None
    target: str | None = None  # "commit-messages" for checking commits
    protected: list[str] = Field(default_factory=list)  # for branch-protection
    staged_only: bool = False
    auto_stage: bool = False
    message: str | None = None
    enabled: bool = True


class EnforcementConfig(BaseModel):
    """Configuration for enforcement."""

    enabled: bool = True
    parallel: bool = True
    rules: list[EnforcementRule] = Field(default_factory=list)


class LifecycleHook(BaseModel):
    """Configuration for a lifecycle hook."""

    name: str
    trigger: str  # "after_tool:*", "before_response", etc.
    pattern: str | list[str] = "**/*"
    commands: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    block_until_pass: bool = False
    max_retries: int = 3
    message: str | None = None


class LifecycleConfig(BaseModel):
    """Configuration for lifecycle hooks."""

    enabled: bool = True
    hooks: list[LifecycleHook] = Field(default_factory=list)


class MemoryConfig(BaseModel):
    """Configuration for shared team memory."""

    enabled: bool = True
    max_entries_in_context: int = 20
    relevance: Literal["auto", "all"] = "auto"
    categories: list[str] = Field(
        default_factory=lambda: ["patterns", "decisions", "gotchas", "glossary"]
    )


class DocsTarget(BaseModel):
    """Configuration for a documentation target."""

    name: str
    description: str = ""
    paths: list[str]
    output: str
    prompt: str | None = None
    prompt_file: str | None = None
    per_directory: bool = False


class DocsConfig(BaseModel):
    """Configuration for documentation generation."""

    enabled: bool = False
    output_dir: str = "docs/"
    targets: list[DocsTarget] = Field(default_factory=list)


class PoniConfig(BaseModel):
    """Core Poni configuration."""

    version: str = "0.1.0"
    preset: str | None = None
    detected: list[str] = Field(default_factory=list)
    package_manager: str | None = None


class Config(BaseModel):
    """Root configuration model for Poni."""

    poni: PoniConfig = Field(default_factory=PoniConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    mcps: dict[str, McpConfig] = Field(default_factory=dict)
    cli: dict[str, CliConfig] = Field(default_factory=dict)
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
    enforcement: EnforcementConfig = Field(default_factory=EnforcementConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    docs: DocsConfig = Field(default_factory=DocsConfig)
