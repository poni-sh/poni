# Poni - Implementation Specification

## Tech Stack

- **Python 3.12+**
- **uv** - Package management and virtual environments
- **Typer** - CLI framework
- **FastMCP** - MCP server implementation
- **Pydantic** - Configuration validation
- **Rich** - Terminal output formatting

## Project Setup

```bash
# Initialize project
uv init poni
cd poni

# Add dependencies
uv add typer[all] fastmcp pydantic pydantic-settings python-dotenv rich tomlkit gitpython glob2 watchfiles
uv add --dev pytest pytest-asyncio ruff mypy
```

## Project Structure

```
poni/
├── pyproject.toml
├── README.md
├── src/
│   └── poni/
│       ├── __init__.py
│       ├── __main__.py           # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py           # Typer app, all commands
│       │   ├── init.py           # poni init
│       │   ├── serve.py          # poni serve
│       │   ├── validate.py       # poni validate
│       │   ├── memory.py         # poni memory *
│       │   ├── docs.py           # poni docs *
│       │   ├── tools.py          # poni tools *, poni run
│       │   └── enforce.py        # poni enforce
│       ├── config/
│       │   ├── __init__.py
│       │   ├── models.py         # Pydantic models for config
│       │   ├── loader.py         # Load and parse config
│       │   ├── secrets.py        # Secret resolution
│       │   └── detection.py      # Project setup detection
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py         # FastMCP server
│       │   ├── proxy.py          # Proxy to child MCPs
│       │   ├── tools.py          # Built-in poni tools
│       │   └── policy.py         # Policy enforcement
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── store.py          # Memory storage
│       │   └── relevance.py      # Relevance matching
│       ├── docs/
│       │   ├── __init__.py
│       │   ├── generator.py      # Doc generation
│       │   └── lock.py           # Lock file management
│       ├── enforcement/
│       │   ├── __init__.py
│       │   ├── hooks.py          # Git hook management
│       │   ├── rules.py          # Rule execution
│       │   └── lifecycle.py      # Lifecycle hooks
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── executor.py       # Tool execution
│       │   └── cli_wrapper.py    # CLI tool wrapping
│       └── presets/
│           ├── __init__.py
│           ├── typescript.py
│           ├── python.py
│           ├── rust.py
│           └── go.py
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_policy.py
    ├── test_memory.py
    └── test_enforcement.py
```

## pyproject.toml

```toml
[project]
name = "poni"
version = "0.1.0"
description = "The control plane for agentic development"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "typer[all]>=0.9.0",
    "fastmcp>=0.1.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "tomlkit>=0.12.0",
    "gitpython>=3.1.0",
    "watchfiles>=0.21.0",
]

[project.scripts]
poni = "poni.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/poni"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
```

---

## Implementation Details

### 1. Entry Point (`src/poni/__main__.py`)

```python
from poni.cli.main import app

if __name__ == "__main__":
    app()
```

### 2. CLI Main (`src/poni/cli/main.py`)

```python
import typer
from rich.console import Console

from poni.cli import init, serve, validate, memory, docs, tools, enforce

app = typer.Typer(
    name="poni",
    help="The control plane for agentic development",
    no_args_is_help=True,
)
console = Console()

# Register subcommands
app.command()(init.init)
app.command()(serve.serve)
app.command()(validate.validate)
app.add_typer(memory.app, name="memory")
app.add_typer(docs.app, name="docs")
app.add_typer(tools.app, name="tools")
app.command()(tools.run)
app.command()(enforce.enforce)
```

### 3. Config Models (`src/poni/config/models.py`)

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class SecretsConfig(BaseModel):
    source: Literal["env"] = "env"


class McpToolsConfig(BaseModel):
    allow: list[str] | None = None
    deny: list[str] | None = None


class McpPoliciesConfig(BaseModel):
    deny_patterns: list[str] = Field(default_factory=list)
    protected_paths: list[str] = Field(default_factory=list)


class McpConfig(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    tools: McpToolsConfig = Field(default_factory=McpToolsConfig)
    policies: McpPoliciesConfig = Field(default_factory=McpPoliciesConfig)


class CliPoliciesConfig(BaseModel):
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
    description: str = ""
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    policies: CliPoliciesConfig = Field(default_factory=CliPoliciesConfig)


class ToolConfig(BaseModel):
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
    enabled: bool = True
    parallel: bool = True
    rules: list[EnforcementRule] = Field(default_factory=list)


class LifecycleHook(BaseModel):
    name: str
    trigger: str  # "after_tool:*", "before_response", etc.
    pattern: str | list[str] = "**/*"
    commands: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    block_until_pass: bool = False
    max_retries: int = 3
    message: str | None = None


class LifecycleConfig(BaseModel):
    enabled: bool = True
    hooks: list[LifecycleHook] = Field(default_factory=list)


class MemoryConfig(BaseModel):
    enabled: bool = True
    max_entries_in_context: int = 20
    relevance: Literal["auto", "all"] = "auto"
    categories: list[str] = Field(
        default_factory=lambda: ["patterns", "decisions", "gotchas", "glossary"]
    )


class DocsTarget(BaseModel):
    name: str
    description: str = ""
    paths: list[str]
    output: str
    prompt: str | None = None
    prompt_file: str | None = None
    per_directory: bool = False


class DocsConfig(BaseModel):
    enabled: bool = False
    output_dir: str = "docs/"
    targets: list[DocsTarget] = Field(default_factory=list)


class PoniConfig(BaseModel):
    version: str = "0.1.0"
    preset: str | None = None
    detected: list[str] = Field(default_factory=list)
    package_manager: str | None = None


class Config(BaseModel):
    poni: PoniConfig = Field(default_factory=PoniConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    mcps: dict[str, McpConfig] = Field(default_factory=dict)
    cli: dict[str, CliConfig] = Field(default_factory=dict)
    tools: dict[str, ToolConfig] = Field(default_factory=dict)
    enforcement: EnforcementConfig = Field(default_factory=EnforcementConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    docs: DocsConfig = Field(default_factory=DocsConfig)
```

### 4. Config Loader (`src/poni/config/loader.py`)

```python
from pathlib import Path
import tomlkit
from poni.config.models import Config
from poni.config.secrets import resolve_secrets

PONI_DIR = ".poni"
CONFIG_FILE = "config.toml"


def find_config_path() -> Path | None:
    """Find .poni/config.toml in current or parent directories."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        config_path = parent / PONI_DIR / CONFIG_FILE
        if config_path.exists():
            return config_path
    return None


def load_config() -> Config:
    """Load and parse config, resolving secrets."""
    config_path = find_config_path()
    if not config_path:
        raise FileNotFoundError(
            "No .poni/config.toml found. Run 'poni init' first."
        )
    
    with open(config_path) as f:
        raw = tomlkit.load(f)
    
    # Convert tomlkit to dict and resolve secrets
    config_dict = resolve_secrets(dict(raw))
    
    return Config.model_validate(config_dict)


def get_poni_dir() -> Path:
    """Get the .poni directory path."""
    config_path = find_config_path()
    if config_path:
        return config_path.parent
    return Path.cwd() / PONI_DIR
```

### 5. Secret Resolution (`src/poni/config/secrets.py`)

```python
import os
import re
from pathlib import Path
from dotenv import dotenv_values

SECRET_PATTERN = re.compile(r"\$\{([^}]+)\}")


def load_env_secrets() -> dict[str, str]:
    """Load secrets from .env file and environment."""
    env_path = Path.cwd() / ".env"
    secrets = {}
    
    # Load from .env file
    if env_path.exists():
        secrets.update(dotenv_values(env_path))
    
    # Environment variables override .env
    secrets.update(os.environ)
    
    return secrets


def resolve_secrets(obj: any, secrets: dict[str, str] | None = None) -> any:
    """Recursively resolve ${VAR} patterns in config."""
    if secrets is None:
        secrets = load_env_secrets()
    
    if isinstance(obj, str):
        def replace(match: re.Match) -> str:
            key = match.group(1)
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
```

### 6. Project Detection (`src/poni/config/detection.py`)

```python
from pathlib import Path
import json
from dataclasses import dataclass, field


@dataclass
class DetectedProject:
    languages: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    package_manager: str | None = None
    existing_hooks: list[str] = field(default_factory=list)


def detect_project() -> DetectedProject:
    """Detect project setup from existing config files."""
    result = DetectedProject()
    cwd = Path.cwd()
    
    # JavaScript/TypeScript
    package_json = cwd / "package.json"
    if package_json.exists():
        with open(package_json) as f:
            pkg = json.load(f)
        
        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }
        
        if "typescript" in all_deps:
            result.languages.append("typescript")
        else:
            result.languages.append("javascript")
        
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
        else:
            result.package_manager = "npm"
    
    # Python
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        result.languages.append("python")
        content = pyproject.read_text()
        
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
    
    # Rust
    if (cwd / "Cargo.toml").exists():
        result.languages.append("rust")
        result.tools.extend(["rustfmt", "clippy"])
    
    # Go
    if (cwd / "go.mod").exists():
        result.languages.append("go")
        if (cwd / ".golangci.yml").exists() or (cwd / ".golangci.yaml").exists():
            result.tools.append("golangci-lint")
    
    # Existing hooks
    if (cwd / ".husky").exists():
        result.existing_hooks.append("husky")
    if (cwd / ".pre-commit-config.yaml").exists():
        result.existing_hooks.append("pre-commit")
    
    return result
```

### 7. Init Command (`src/poni/cli/init.py`)

```python
from pathlib import Path
import typer
from rich.console import Console
from rich.prompt import Confirm
import tomlkit

from poni.config.detection import detect_project
from poni.presets import get_preset

console = Console()

PONI_DIR = ".poni"
MCP_JSON = ".mcp.json"


def init(
    preset: str | None = typer.Option(None, help="Use preset: typescript, python, rust, go"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Accept all defaults"),
    detect_only: bool = typer.Option(False, "--detect-only", help="Only show detection results"),
):
    """Initialize Poni in the current repository."""
    cwd = Path.cwd()
    poni_dir = cwd / PONI_DIR
    
    # Detect project
    console.print("[bold]Detecting project setup...[/bold]\n")
    detected = detect_project()
    
    if detected.languages:
        console.print(f"  Languages: {', '.join(detected.languages)}")
    if detected.tools:
        console.print(f"  Tools: {', '.join(detected.tools)}")
    if detected.package_manager:
        console.print(f"  Package manager: {detected.package_manager}")
    if detected.existing_hooks:
        console.print(f"  Existing hooks: {', '.join(detected.existing_hooks)}")
    
    if detect_only:
        return
    
    console.print()
    
    # Generate config
    if preset:
        config = get_preset(preset)
    else:
        config = generate_config_from_detection(detected)
    
    # Create directories
    poni_dir.mkdir(exist_ok=True)
    (poni_dir / "prompts").mkdir(exist_ok=True)
    (poni_dir / "memory").mkdir(exist_ok=True)
    (poni_dir / "docs").mkdir(exist_ok=True)
    
    # Write config.toml
    config_path = poni_dir / "config.toml"
    with open(config_path, "w") as f:
        tomlkit.dump(config, f)
    console.print(f"  [green]✓[/green] Created {config_path}")
    
    # Write .mcp.json
    mcp_json_path = cwd / MCP_JSON
    mcp_config = {
        "mcpServers": {
            "poni": {
                "command": "poni",
                "args": ["serve"],
                "type": "stdio"
            }
        }
    }
    import json
    with open(mcp_json_path, "w") as f:
        json.dump(mcp_config, f, indent=2)
    console.print(f"  [green]✓[/green] Created {mcp_json_path}")
    
    # Create memory files
    for category in ["patterns", "decisions", "gotchas", "glossary"]:
        memory_file = poni_dir / "memory" / f"{category}.toml"
        if not memory_file.exists():
            memory_file.write_text("# Shared team memory\n\n")
    console.print(f"  [green]✓[/green] Created memory files")
    
    # Install git hooks
    install_git_hooks(cwd)
    console.print(f"  [green]✓[/green] Installed git hooks")
    
    # Update .gitignore
    update_gitignore(cwd)
    console.print(f"  [green]✓[/green] Updated .gitignore")
    
    # Print next steps
    console.print("\n[bold green]Poni initialized![/bold green]\n")
    console.print("Next steps:")
    console.print("  1. Review .poni/config.toml")
    if detected.existing_hooks:
        console.print(f"  2. Remove {', '.join(detected.existing_hooks)} (Poni handles hooks now)")
    console.print("  3. Commit .poni/ and .mcp.json to git")
    console.print("\nConfigure Claude Code:")
    console.print("  Deny all tools except 'poni'")


def generate_config_from_detection(detected) -> dict:
    """Generate config based on detected project setup."""
    # Import preset based on detected language
    if "typescript" in detected.languages or "javascript" in detected.languages:
        from poni.presets.typescript import generate_config
        return generate_config(detected)
    elif "python" in detected.languages:
        from poni.presets.python import generate_config
        return generate_config(detected)
    elif "rust" in detected.languages:
        from poni.presets.rust import generate_config
        return generate_config(detected)
    elif "go" in detected.languages:
        from poni.presets.go import generate_config
        return generate_config(detected)
    else:
        # Minimal config
        return {
            "poni": {"version": "0.1.0"},
            "secrets": {"source": "env"},
            "memory": {"enabled": True},
        }


def install_git_hooks(cwd: Path):
    """Install git hooks."""
    hooks_dir = cwd / ".git" / "hooks"
    if not hooks_dir.exists():
        return
    
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text("#!/bin/sh\nexec poni enforce --hook pre-commit\n")
    pre_commit.chmod(0o755)
    
    pre_push = hooks_dir / "pre-push"
    pre_push.write_text("#!/bin/sh\nexec poni enforce --hook pre-push\n")
    pre_push.chmod(0o755)


def update_gitignore(cwd: Path):
    """Add .poni/.secrets.toml to .gitignore."""
    gitignore = cwd / ".gitignore"
    entry = ".poni/.secrets.toml"
    
    if gitignore.exists():
        content = gitignore.read_text()
        if entry not in content:
            with open(gitignore, "a") as f:
                f.write(f"\n# Poni\n{entry}\n")
    else:
        gitignore.write_text(f"# Poni\n{entry}\n")
```

### 8. MCP Server (`src/poni/mcp/server.py`)

```python
from fastmcp import FastMCP
from poni.config.loader import load_config
from poni.mcp.proxy import McpProxy
from poni.mcp.policy import PolicyEngine
from poni.mcp.tools import register_builtin_tools
from poni.memory.store import MemoryStore
from poni.tools.executor import ToolExecutor
from poni.tools.cli_wrapper import CliWrapper

mcp = FastMCP("poni")


def create_server():
    """Create and configure the MCP server."""
    config = load_config()
    
    # Initialize components
    policy_engine = PolicyEngine(config)
    memory_store = MemoryStore(config)
    tool_executor = ToolExecutor(config)
    cli_wrapper = CliWrapper(config)
    mcp_proxy = McpProxy(config, policy_engine)
    
    # Register built-in tools
    register_builtin_tools(mcp, memory_store, tool_executor, cli_wrapper)
    
    # Register proxied MCP tools
    for mcp_name, mcp_config in config.mcps.items():
        register_proxied_tools(mcp, mcp_name, mcp_config, mcp_proxy)
    
    # Register CLI wrapper tools
    for cli_name, cli_config in config.cli.items():
        register_cli_tool(mcp, cli_name, cli_config, cli_wrapper, policy_engine)
    
    # Register custom tools
    for tool_name, tool_config in config.tools.items():
        register_custom_tool(mcp, tool_name, tool_config, tool_executor)
    
    return mcp


def register_proxied_tools(mcp: FastMCP, mcp_name: str, mcp_config, proxy: McpProxy):
    """Register tools from a child MCP."""
    # Get available tools from child MCP
    tools = proxy.get_tools(mcp_name)
    
    for tool in tools:
        # Check allow/deny lists
        if mcp_config.tools.allow and tool.name not in mcp_config.tools.allow:
            continue
        if mcp_config.tools.deny and tool.name in mcp_config.tools.deny:
            continue
        
        # Register with prefixed name
        full_name = f"{mcp_name}.{tool.name}"
        
        @mcp.tool(name=full_name, description=tool.description)
        async def proxied_tool(**kwargs):
            return await proxy.call_tool(mcp_name, tool.name, kwargs)


def register_cli_tool(mcp: FastMCP, name: str, config, wrapper: CliWrapper, policy: PolicyEngine):
    """Register a CLI wrapper tool."""
    
    @mcp.tool(name=f"poni.cli.{name}", description=config.description)
    async def cli_tool(args: str) -> str:
        # Check policies
        violation = policy.check_cli(name, args)
        if violation:
            return f"⛔ Policy violation: {name}\n\n{violation}"
        
        return await wrapper.execute(name, args)


def register_custom_tool(mcp: FastMCP, name: str, config, executor: ToolExecutor):
    """Register a custom team tool."""
    
    @mcp.tool(name=f"poni.{name}", description=config.description)
    async def custom_tool(**kwargs) -> str:
        return await executor.execute(name, kwargs)
```

### 9. Serve Command (`src/poni/cli/serve.py`)

```python
import typer
from poni.mcp.server import create_server


def serve():
    """Run Poni as an MCP server."""
    server = create_server()
    server.run()
```

### 10. Policy Engine (`src/poni/mcp/policy.py`)

```python
import re
from poni.config.models import Config, McpConfig, CliConfig


class PolicyEngine:
    def __init__(self, config: Config):
        self.config = config
    
    def check_mcp_tool(self, mcp_name: str, tool_name: str, args: dict) -> str | None:
        """Check if MCP tool call is allowed. Returns violation message or None."""
        mcp_config = self.config.mcps.get(mcp_name)
        if not mcp_config:
            return None
        
        # Check deny patterns
        args_str = str(args)
        for pattern in mcp_config.policies.deny_patterns:
            if re.search(pattern, args_str, re.IGNORECASE):
                return (
                    f"Blocked by: deny_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Input matched a denied pattern."
                )
        
        return None
    
    def check_cli(self, cli_name: str, args: str) -> str | None:
        """Check if CLI command is allowed. Returns violation message or None."""
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return None
        
        policies = cli_config.policies
        
        # Check subcommands
        parts = args.split()
        if parts:
            subcommand = parts[0]
            
            if policies.allow_subcommands and subcommand not in policies.allow_subcommands:
                return (
                    f"Blocked by: allow_subcommands\n"
                    f"Subcommand '{subcommand}' is not in the allow list.\n"
                    f"Allowed: {', '.join(policies.allow_subcommands)}"
                )
            
            if policies.deny_subcommands and subcommand in policies.deny_subcommands:
                return (
                    f"Blocked by: deny_subcommands\n"
                    f"Subcommand '{subcommand}' is blocked."
                )
        
        # Check deny patterns
        for pattern in policies.deny_patterns:
            if re.search(pattern, args, re.IGNORECASE):
                return (
                    f"Blocked by: deny_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Command matched a denied pattern."
                )
        
        # Check require patterns
        for pattern in policies.require_patterns:
            if not re.search(pattern, args, re.IGNORECASE):
                return (
                    f"Blocked by: require_patterns\n"
                    f"Pattern: {pattern}\n"
                    f"Command must match this pattern."
                )
        
        # Check namespaces (for kubectl, etc.)
        if policies.allowed_namespaces or policies.denied_namespaces:
            ns_match = re.search(r"-n\s+(\S+)|--namespace[=\s]+(\S+)", args)
            if ns_match:
                namespace = ns_match.group(1) or ns_match.group(2)
                
                if policies.allowed_namespaces and namespace not in policies.allowed_namespaces:
                    return (
                        f"Blocked by: allowed_namespaces\n"
                        f"Namespace '{namespace}' is not allowed.\n"
                        f"Allowed: {', '.join(policies.allowed_namespaces)}"
                    )
                
                if policies.denied_namespaces and namespace in policies.denied_namespaces:
                    return (
                        f"Blocked by: denied_namespaces\n"
                        f"Namespace '{namespace}' is blocked."
                    )
        
        return None
    
    def check_interactive(self, cli_name: str, args: str) -> bool:
        """Check if command requires interactive confirmation."""
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return False
        
        for pattern in cli_config.policies.interactive_patterns:
            if re.search(pattern, args, re.IGNORECASE):
                return True
        
        return False
    
    def redact_output(self, cli_name: str, output: str) -> str:
        """Redact sensitive patterns from output."""
        cli_config = self.config.cli.get(cli_name)
        if not cli_config:
            return output
        
        for pattern in cli_config.policies.redact_patterns:
            output = re.sub(
                f"({pattern})\\s*[=:]?\\s*\\S+",
                r"\1=[REDACTED]",
                output,
                flags=re.IGNORECASE,
            )
        
        return output
```

### 11. Memory Store (`src/poni/memory/store.py`)

```python
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import tomlkit
import git

from poni.config.loader import get_poni_dir
from poni.config.models import MemoryConfig


@dataclass
class MemoryEntry:
    id: str
    content: str
    category: str
    added_by: str
    added_at: str
    context: str | None = None
    files: list[str] | None = None


class MemoryStore:
    def __init__(self, config):
        self.config = config.memory
        self.poni_dir = get_poni_dir()
        self.memory_dir = self.poni_dir / "memory"
    
    def list(self, category: str | None = None) -> list[MemoryEntry]:
        """List all memory entries, optionally filtered by category."""
        entries = []
        
        categories = [category] if category else self.config.categories
        
        for cat in categories:
            file_path = self.memory_dir / f"{cat}.toml"
            if not file_path.exists():
                continue
            
            with open(file_path) as f:
                data = tomlkit.load(f)
            
            for entry in data.get("entries", []):
                entries.append(MemoryEntry(
                    id=entry["id"],
                    content=entry["content"],
                    category=cat,
                    added_by=entry.get("added_by", "unknown"),
                    added_at=entry.get("added_at", "unknown"),
                    context=entry.get("context"),
                    files=entry.get("files"),
                ))
        
        return entries
    
    def add(
        self,
        content: str,
        category: str = "patterns",
        context: str | None = None,
        files: list[str] | None = None,
    ) -> MemoryEntry:
        """Add a new memory entry."""
        file_path = self.memory_dir / f"{category}.toml"
        
        # Load existing
        if file_path.exists():
            with open(file_path) as f:
                data = tomlkit.load(f)
        else:
            data = tomlkit.document()
            data["entries"] = tomlkit.aot()
        
        # Generate ID
        prefix = category[:3]
        existing_ids = [e["id"] for e in data.get("entries", [])]
        num = 1
        while f"{prefix}-{num:03d}" in existing_ids:
            num += 1
        entry_id = f"{prefix}-{num:03d}"
        
        # Get git user
        try:
            repo = git.Repo(search_parent_directories=True)
            added_by = repo.config_reader().get_value("user", "name")
        except Exception:
            added_by = "unknown"
        
        # Create entry
        entry = {
            "id": entry_id,
            "added_by": added_by,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
            "content": content,
        }
        if context:
            entry["context"] = context
        if files:
            entry["files"] = files
        
        # Add to file
        if "entries" not in data:
            data["entries"] = tomlkit.aot()
        data["entries"].append(entry)
        
        with open(file_path, "w") as f:
            tomlkit.dump(data, f)
        
        return MemoryEntry(
            id=entry_id,
            content=content,
            category=category,
            added_by=added_by,
            added_at=entry["added_at"],
            context=context,
            files=files,
        )
    
    def remove(self, entry_id: str) -> bool:
        """Remove a memory entry by ID."""
        for cat in self.config.categories:
            file_path = self.memory_dir / f"{cat}.toml"
            if not file_path.exists():
                continue
            
            with open(file_path) as f:
                data = tomlkit.load(f)
            
            entries = data.get("entries", [])
            for i, entry in enumerate(entries):
                if entry["id"] == entry_id:
                    del entries[i]
                    with open(file_path, "w") as f:
                        tomlkit.dump(data, f)
                    return True
        
        return False
    
    def search(self, query: str) -> list[MemoryEntry]:
        """Search memory entries by content."""
        query_lower = query.lower()
        results = []
        
        for entry in self.list():
            if query_lower in entry.content.lower():
                results.append(entry)
            elif entry.context and query_lower in entry.context.lower():
                results.append(entry)
        
        return results
    
    def get_relevant(self, files: list[str] | None = None) -> list[MemoryEntry]:
        """Get relevant memory entries for context injection."""
        if not self.config.enabled:
            return []
        
        if self.config.relevance == "all":
            entries = self.list()
        else:
            # TODO: Implement smart relevance matching based on files
            entries = self.list()
        
        return entries[: self.config.max_entries_in_context]
```

### 12. Memory Commands (`src/poni/cli/memory.py`)

```python
import typer
from rich.console import Console
from rich.table import Table

from poni.config.loader import load_config
from poni.memory.store import MemoryStore

app = typer.Typer(help="Manage shared team memory")
console = Console()


@app.command("list")
def list_memories(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List memory entries."""
    config = load_config()
    store = MemoryStore(config)
    entries = store.list(category)
    
    if not entries:
        console.print("No memory entries found.")
        return
    
    table = Table(title="Memory Entries")
    table.add_column("ID", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Content")
    table.add_column("Added By", style="dim")
    
    for entry in entries:
        content = entry.content[:60] + "..." if len(entry.content) > 60 else entry.content
        table.add_row(entry.id, entry.category, content, entry.added_by)
    
    console.print(table)


@app.command("add")
def add_memory(
    content: str = typer.Argument(..., help="Memory content"),
    category: str = typer.Option("patterns", "--category", "-c", help="Category"),
    files: str | None = typer.Option(None, "--files", "-f", help="File glob pattern"),
    context: str | None = typer.Option(None, "--context", help="Additional context"),
):
    """Add a memory entry."""
    config = load_config()
    store = MemoryStore(config)
    
    files_list = [files] if files else None
    entry = store.add(content, category, context, files_list)
    
    console.print(f"[green]✓[/green] Added memory {entry.id}: {content}")


@app.command("remove")
def remove_memory(
    entry_id: str = typer.Argument(..., help="Entry ID to remove"),
):
    """Remove a memory entry."""
    config = load_config()
    store = MemoryStore(config)
    
    if store.remove(entry_id):
        console.print(f"[green]✓[/green] Removed {entry_id}")
    else:
        console.print(f"[red]✗[/red] Entry {entry_id} not found")
        raise typer.Exit(1)


@app.command("search")
def search_memories(
    query: str = typer.Argument(..., help="Search query"),
):
    """Search memory entries."""
    config = load_config()
    store = MemoryStore(config)
    entries = store.search(query)
    
    if not entries:
        console.print("No matching entries found.")
        return
    
    for entry in entries:
        console.print(f"[cyan]{entry.id}[/cyan] [{entry.category}]")
        console.print(f"  {entry.content}")
        if entry.context:
            console.print(f"  [dim]{entry.context}[/dim]")
        console.print()
```

### 13. Enforcement (`src/poni/cli/enforce.py`)

```python
import subprocess
import typer
from rich.console import Console
from pathlib import Path
import git

from poni.config.loader import load_config

console = Console()


def enforce(
    hook: str | None = typer.Option(None, "--hook", help="Hook type: pre-commit, pre-push"),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues"),
    staged: bool = typer.Option(False, "--staged", help="Only check staged files"),
):
    """Run enforcement checks."""
    config = load_config()
    
    if not config.enforcement.enabled:
        return
    
    # Get files to check
    if staged or hook == "pre-commit":
        files = get_staged_files()
    else:
        files = None  # All files
    
    # Filter rules by trigger
    trigger = hook or "pre-commit"
    rules = [r for r in config.enforcement.rules if r.trigger == trigger and r.enabled]
    
    if not rules:
        return
    
    console.print(f"\n[bold]Poni enforcement checks:[/bold]\n")
    
    failed = []
    
    for rule in rules:
        result = run_rule(rule, files, config.poni.package_manager)
        
        if result.success:
            console.print(f"  [green]✓[/green] {rule.name}")
        else:
            console.print(f"  [red]✗[/red] {rule.name}")
            if result.output:
                for line in result.output.split("\n")[:10]:
                    console.print(f"    {line}")
            failed.append(rule)
    
    if failed:
        console.print(f"\n[red]Blocked. Fix {len(failed)} issue(s) above.[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[green]All checks passed.[/green]")


def get_staged_files() -> list[str]:
    """Get list of staged files."""
    try:
        repo = git.Repo(search_parent_directories=True)
        return [item.a_path for item in repo.index.diff("HEAD")]
    except Exception:
        return []


class RuleResult:
    def __init__(self, success: bool, output: str = ""):
        self.success = success
        self.output = output


def run_rule(rule, files: list[str] | None, package_manager: str | None) -> RuleResult:
    """Run a single enforcement rule."""
    if rule.command:
        # Command-based rule
        cmd = rule.command
        
        # Substitute package manager
        if package_manager:
            cmd = cmd.replace("npm ", f"{package_manager} ")
            cmd = cmd.replace("npx ", f"{package_manager} exec " if package_manager == "pnpm" else "npx ")
        
        # Substitute files
        if files and "${files}" in cmd:
            # Filter files by pattern
            import fnmatch
            patterns = rule.pattern if isinstance(rule.pattern, list) else [rule.pattern]
            matched = [f for f in files if any(fnmatch.fnmatch(f, p) for p in patterns)]
            
            if not matched:
                return RuleResult(True)
            
            cmd = cmd.replace("${files}", " ".join(matched))
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
            )
            return RuleResult(
                success=result.returncode == 0,
                output=result.stdout + result.stderr,
            )
        except Exception as e:
            return RuleResult(False, str(e))
    
    elif rule.check == "pattern-absent":
        # Check that pattern is absent from files
        import fnmatch
        import re
        
        patterns = rule.pattern if isinstance(rule.pattern, list) else [rule.pattern]
        target_files = files or list(Path.cwd().rglob("*"))
        
        violations = []
        for f in target_files:
            path = Path(f)
            if not path.is_file():
                continue
            if not any(fnmatch.fnmatch(str(path), p) for p in patterns):
                continue
            if any(fnmatch.fnmatch(str(path), e) for e in rule.exclude):
                continue
            
            try:
                content = path.read_text()
                if rule.deny_pattern and re.search(rule.deny_pattern, content):
                    violations.append(str(path))
            except Exception:
                pass
        
        if violations:
            msg = rule.message or f"Pattern '{rule.deny_pattern}' found in files"
            return RuleResult(False, f"{msg}\n" + "\n".join(violations[:5]))
        
        return RuleResult(True)
    
    elif rule.check == "test-coverage":
        # Check that test files exist for source files
        # TODO: Implement properly
        return RuleResult(True)
    
    elif rule.check == "branch-protection":
        # Check current branch against protected list
        try:
            repo = git.Repo(search_parent_directories=True)
            branch = repo.active_branch.name
            if branch in rule.protected:
                return RuleResult(
                    False,
                    rule.message or f"Cannot push to protected branch '{branch}'",
                )
        except Exception:
            pass
        return RuleResult(True)
    
    return RuleResult(True)
```

### 14. TypeScript Preset (`src/poni/presets/typescript.py`)

```python
def generate_config(detected) -> dict:
    """Generate TypeScript preset config."""
    pm = detected.package_manager or "npm"
    run = f"{pm} run" if pm != "npm" else "npm run"
    exec_cmd = f"{pm} exec" if pm == "pnpm" else "npx"
    
    config = {
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
    if "eslint" in detected.tools:
        rules.append({
            "name": "eslint",
            "trigger": "pre-commit",
            "command": f"{exec_cmd} eslint --fix ${{files}}",
            "pattern": "**/*.{ts,tsx,js,jsx}",
            "staged_only": True,
            "auto_stage": True,
        })
        hooks.append({
            "name": "post-write-eslint",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.{ts,tsx}",
            "commands": [f"{exec_cmd} eslint --fix ${{file}}"],
        })
    
    if "prettier" in detected.tools:
        rules.append({
            "name": "prettier",
            "trigger": "pre-commit",
            "command": f"{exec_cmd} prettier --write ${{files}}",
            "pattern": "**/*.{ts,tsx,js,jsx,json,md}",
            "staged_only": True,
            "auto_stage": True,
        })
    
    if "biome" in detected.tools:
        rules.append({
            "name": "biome",
            "trigger": "pre-commit",
            "command": f"{exec_cmd} biome check --apply ${{files}}",
            "pattern": "**/*.{ts,tsx,js,jsx,json}",
            "staged_only": True,
            "auto_stage": True,
        })
    
    # TypeScript check
    if "typescript" in detected.languages:
        rules.append({
            "name": "typecheck",
            "trigger": "pre-push",
            "command": f"{exec_cmd} tsc --noEmit",
        })
        hooks.append({
            "name": "post-write-typecheck",
            "trigger": "after_tool:filesystem.write_file",
            "pattern": "**/*.{ts,tsx}",
            "commands": [f"{exec_cmd} tsc --noEmit"],
            "block_until_pass": True,
            "message": "Fix type errors before continuing",
        })
    
    # Test runner
    if "vitest" in detected.tools:
        rules.append({
            "name": "test",
            "trigger": "pre-push",
            "command": f"{exec_cmd} vitest run",
        })
    elif "jest" in detected.tools:
        rules.append({
            "name": "test",
            "trigger": "pre-push",
            "command": f"{exec_cmd} jest",
        })
    
    # No console.log rule
    rules.append({
        "name": "no-console",
        "trigger": "pre-commit",
        "check": "pattern-absent",
        "pattern": "src/**/*.{ts,tsx}",
        "exclude": ["**/*.test.*", "**/*.spec.*"],
        "deny_pattern": r"console\.(log|debug|info)\(",
        "message": "Use logger instead of console methods",
    })
    
    # Verify before done hook
    hooks.append({
        "name": "verify-before-done",
        "trigger": "before_response",
        "commands": [f"{exec_cmd} tsc --noEmit"],
        "block_until_pass": True,
        "message": "All checks must pass before completing",
    })
    
    return config
```

---

## Testing

```bash
# Run tests
uv run pytest

# Run specific test
uv run pytest tests/test_policy.py -v

# Type check
uv run mypy src/poni

# Lint
uv run ruff check src/poni
uv run ruff format src/poni
```

---

## Build & Install

```bash
# Build
uv build

# Install locally for testing
uv pip install -e .

# Run
poni --help
poni init
poni serve
```

---

## Implementation Order

1. **Phase 1: Core**
   - [ ] Project structure and pyproject.toml
   - [ ] Config models (Pydantic)
   - [ ] Config loader with secret resolution
   - [ ] Basic CLI with Typer (init, validate)

2. **Phase 2: MCP Server**
   - [ ] FastMCP server setup
   - [ ] Policy engine
   - [ ] Built-in tools (memory_add, memory_search)
   - [ ] serve command

3. **Phase 3: Enforcement**
   - [ ] Git hook installation
   - [ ] Rule execution
   - [ ] enforce command

4. **Phase 4: Features**
   - [ ] Memory store (full CRUD)
   - [ ] CLI wrapping
   - [ ] Project detection
   - [ ] Presets (typescript, python)

5. **Phase 5: Lifecycle**
   - [ ] Lifecycle hooks
   - [ ] MCP proxy to child MCPs
   - [ ] Docs generation

---

## Notes for Implementation

1. **FastMCP**: Check latest docs at https://github.com/jlowin/fastmcp for current API
2. **Async**: Use async/await throughout for MCP server
3. **Error messages**: Make them actionable with examples
4. **Testing**: Write tests for policy engine first (most critical)
5. **Logging**: Use `rich` for CLI output, standard logging for MCP server
