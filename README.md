# Poni

**The control plane for agentic development.**

Poni is a CLI tool and MCP server that gives teams governance, guardrails, and shared context for AI-assisted development. It acts as a policy layer between AI agents and your codebase.

## Features

- **Policy Enforcement** - Define allow/deny rules for CLI commands and MCP tools
- **Git Hooks** - Pre-commit and pre-push enforcement that replaces husky/pre-commit
- **Shared Memory** - Team-wide context that persists across sessions and developers
- **CLI Wrapping** - Govern access to tools like `aws`, `kubectl`, `psql` with policies
- **Project Detection** - Auto-detects your stack and generates sensible defaults
- **MCP Server** - Exposes tools to Claude Code and other MCP clients

## Installation

```bash
# Using uv (recommended)
uv tool install poni

# Using pip
pip install poni
```

## Quick Start

```bash
# Initialize in your project
poni init

# This creates:
# - .poni/config.toml     (configuration)
# - .poni/memory/         (shared team memory)
# - .mcp.json             (MCP server config)
# - Git hooks             (pre-commit, pre-push)
```

Add Poni to your Claude Code MCP servers, then deny all other tools except `poni`.

## CLI Commands

```
poni init              Initialize Poni in current repository
poni validate          Validate configuration
poni serve             Run as MCP server (stdio or SSE)
poni enforce           Run enforcement checks manually
poni run <tool>        Run a custom team tool

poni memory list       List memory entries
poni memory add        Add a memory entry
poni memory search     Search memory entries
poni memory remove     Remove a memory entry

poni tools list        List configured tools
poni tools show        Show tool details

poni docs generate     Generate documentation
poni docs status       Show documentation status
```

## Configuration

Poni is configured via `.poni/config.toml`:

```toml
[poni]
version = "0.1.0"
package_manager = "pnpm"

[secrets]
source = "env"  # Resolve ${VAR} from environment

# CLI Wrappers with policies
[cli.aws]
command = "aws"
description = "AWS CLI"

[cli.aws.policies]
allow_subcommands = ["s3", "ec2", "lambda"]
deny_subcommands = ["iam", "organizations"]
deny_patterns = ["--recursive.*delete"]
interactive_patterns = ["delete", "remove"]
redact_patterns = ["AccessKeyId", "SecretAccessKey"]

[cli.kubectl]
command = "kubectl"

[cli.kubectl.policies]
allowed_namespaces = ["staging", "dev"]
denied_namespaces = ["production", "kube-system"]

# Custom team tools
[tools.deploy]
description = "Deploy to staging"
command = "deploy.sh"
args = ["--env", "staging"]
confirm = true
allowed_branches = ["main", "release/*"]
timeout = 300

# Enforcement rules
[[enforcement.rules]]
name = "eslint"
trigger = "pre-commit"
command = "npx eslint --fix ${files}"
pattern = "**/*.{ts,tsx}"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "no-console"
trigger = "pre-commit"
check = "pattern-absent"
pattern = "src/**/*.ts"
deny_pattern = "console\\.(log|debug)\\("
message = "Use logger instead of console"

[[enforcement.rules]]
name = "branch-protection"
trigger = "pre-push"
check = "branch-protection"
protected = ["main", "production"]

# Shared memory
[memory]
enabled = true
max_entries_in_context = 20
categories = ["patterns", "decisions", "gotchas", "glossary"]
```

## Shared Memory

Memory entries are stored in `.poni/memory/` and shared via git:

```bash
# Add a pattern
poni memory add "Use async/await for all IO operations" -c patterns

# Add a decision
poni memory add "Chose PostgreSQL over MySQL for JSON support" -c decisions

# Add a gotcha
poni memory add "The /api/v2 endpoint requires auth header" -c gotchas
```

Memory is automatically injected into MCP context for AI agents.

## Presets

Poni auto-detects your project and applies sensible defaults:

- **TypeScript** - ESLint, Prettier, Biome, TypeScript checks
- **Python** - Ruff, Black, mypy, pytest
- **Rust** - rustfmt, clippy, cargo test
- **Go** - gofmt, go vet, golangci-lint

```bash
# Use a specific preset
poni init --preset typescript

# Just see what would be detected
poni init --detect-only
```

## MCP Server

Poni runs as an MCP server, exposing tools to AI agents:

```bash
# Run on stdio (default, for Claude Code)
poni serve

# Run on SSE (for web clients)
poni serve --transport sse --port 8000
```

### Built-in MCP Tools

- `poni.memory.add` - Add memory entries
- `poni.memory.list` - List memory entries
- `poni.memory.search` - Search memory
- `poni.cli.<name>` - Wrapped CLI commands with policies
- `poni.<tool>` - Custom team tools

## Policy Examples

### Prevent dangerous operations

```toml
[cli.aws.policies]
deny_patterns = [
    "--recursive.*delete",
    "s3 rm",
    "ec2 terminate",
]
```

### Require dry-run for destructive commands

```toml
[cli.terraform.policies]
require_patterns = ["--dry-run"]
interactive_patterns = ["apply", "destroy"]
```

### Restrict to specific namespaces

```toml
[cli.kubectl.policies]
allowed_namespaces = ["staging", "dev"]
denied_namespaces = ["production", "kube-system"]
```

### Redact sensitive output

```toml
[cli.aws.policies]
redact_patterns = ["AccessKeyId", "SecretAccessKey", "SessionToken"]
```

## Development

```bash
# Clone the repo
git clone https://github.com/your-org/poni
cd poni

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check src/poni

# Run type checker
uv run mypy src/poni
```
