# Poni - Feature Overview

## CLI Commands

| Command | Description |
|---------|-------------|
| `poni init` | Initialize Poni, detect project setup, generate config |
| `poni init --preset <lang>` | Use preset (typescript, python, rust, go) |
| `poni serve` | Run as MCP server (called by Claude Code) |
| `poni validate` | Validate configuration |
| `poni enforce` | Run enforcement checks manually |
| `poni memory list` | List shared team memory |
| `poni memory add` | Add memory entry |
| `poni memory search` | Search memory entries |
| `poni docs generate` | Generate/update documentation |
| `poni docs generate --changed` | Regenerate only changed docs |
| `poni tools list` | List available custom tools |
| `poni run <tool>` | Run a custom tool |
| `poni migrate husky` | Migrate from husky hooks |
| `poni migrate pre-commit` | Migrate from pre-commit (Python) |

---

## Free Features

### MCP Proxy & Governance
- Proxy all MCP servers through single endpoint
- Tool allow/deny lists per MCP
- Regex pattern policies (block DROP TABLE, etc.)
- Protected file paths
- Secret resolution from `.env` files

### CLI Tool Wrapping
- Wrap any CLI (aws, psql, kubectl, docker, gh, terraform)
- Subcommand allow/deny lists
- Pattern-based input policies
- Output redaction (hide passwords, keys)
- Interactive confirmation for dangerous commands
- Namespace/context restrictions

### Enforcement (replaces husky, lint-staged, pre-commit)
- Pre-commit hooks (lint, format, type check)
- Pre-push hooks (tests, build)
- Auto-fix and auto-stage
- Pattern checks (no console.log, no TODO without ticket)
- Test file requirement checks
- Branch protection

### Lifecycle Hooks (agent enforcement)
- Post-file-write checks (lint after every save)
- Block agent until checks pass
- Pre-response verification (tests must pass before "done")
- Configurable retries

### Shared Memory
- Team knowledge stored in git
- Categories: patterns, decisions, gotchas, glossary
- File-based relevance matching
- Auto-injection into agent context
- Agents can add memories

### Auto Documentation
- Generate docs from code
- Incremental regeneration (only changed files)
- Custom prompts per doc target
- Per-package README generation (monorepo)

### Custom Tools
- Expose team scripts as agent tools
- Argument substitution
- Confirmation prompts
- Branch restrictions
- Timeout configuration

### Project Detection
- Auto-detect eslint, prettier, biome, ruff, mypy, jest, vitest, pytest, cargo
- Detect package manager (npm, pnpm, yarn)
- Migrate existing husky/.pre-commit hooks
- Language presets (typescript, python, rust, go)

---

## Paid Features

### Enterprise Secret Management
- AWS Secrets Manager
- HashiCorp Vault
- GCP Secret Manager
- Azure Key Vault
- 1Password
- Doppler

### Dashboard
- Web UI for policy management
- Edit config without git commits
- Visual rule builder

### Audit Logs
- Full history of agent actions
- What tool, what input, who, when
- Compliance reporting
- Export for SIEM integration

### Team Management
- Role-based access control
- Per-user tool permissions
- Team-wide policy inheritance

### Workflow Integration
- Linear integration
- Jira integration
- GitHub Issues integration
- Auto-create branches from tickets
- Auto-link PRs to tickets

### Enterprise
- SSO (SAML, OIDC)
- Custom policy templates
- Priority support

---

## Pricing (Proposed)

| Tier | Price | For |
|------|-------|-----|
| Free | $0 | Individual devs, small teams |
| Team | $20/seat/month | Teams needing secrets + audit |
| Enterprise | Custom | SSO, compliance, support |

---

## Config At a Glance

```toml
# .poni/config.toml

[secrets]
source = "env"                    # Free: .env files
# source = "aws-secrets-manager"  # Paid: cloud secrets

[mcps.postgres]                   # MCP proxy
tools.allow = ["query", "list_tables"]
policies.deny_patterns = ["DROP", "TRUNCATE"]

[cli.aws]                         # CLI wrapper
policies.deny_subcommands = ["iam", "ec2"]
policies.deny_patterns = ["--recursive"]

[tools.db-reset]                  # Custom tool
command = "make db-reset"
confirm = true

[enforcement]                     # Git hooks
[[enforcement.rules]]
name = "lint"
trigger = "pre-commit"
command = "pnpm eslint --fix ${files}"

[lifecycle]                       # Agent enforcement
[[lifecycle.hooks]]
trigger = "after_tool:filesystem.write_file"
commands = ["pnpm tsc --noEmit"]
block_until_pass = true

[memory]                          # Shared knowledge
enabled = true

[docs]                            # Auto documentation
[[docs.targets]]
paths = ["src/**/*.ts"]
output = "docs/api.md"
```
