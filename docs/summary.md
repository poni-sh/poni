# Poni - Agentic Development Control Plane

## Overview

Poni is a CLI tool and MCP server that provides governance, shared knowledge, and team tooling for agentic development. It acts as the complete control plane for AI agents in development workflows.

## Core Features

| Feature | Purpose |
|---------|---------|
| **MCP Proxy** | Governance layer for MCP servers with policy enforcement |
| **Tools** | Team scripts exposed as agent capabilities |
| **CLI Wrapping** | Arbitrary CLI tools (aws, psql, kubectl) with policies |
| **Enforcement** | Pre-commit/pre-push checks, replaces husky/lint-staged |
| **Lifecycle Hooks** | Force agents to run checks after writing code |
| **Workflow** | Ticket/PR integration (Linear, Jira, GitHub) |

## Core Concept

Poni runs as the single approved MCP in Claude Code (or other MCP clients). All other MCPs, CLI tools, and scripts are defined in Poni's config and proxied through it. This allows Poni to:

- Enforce tool allow/deny lists
- Apply regex-based policies on tool inputs
- Wrap arbitrary CLI tools with guardrails
- Provide shared prompts with scoped permissions
- Manage secrets from .env files
- Share team memory/knowledge with all agents
- Auto-generate and maintain documentation
- Expose team scripts as agent tools
- Enforce code quality via lifecycle hooks
- Replace pre-commit hooks with unified config
- Integrate with ticket/PR workflows


---

### `poni tools`

Manage and run custom tools.

```bash
poni tools list                 # list available tools
poni run <tool> [args...]       # run a tool
poni run db-reset
poni run test-package api --watch
```

---

### `poni enforce`

Run enforcement checks manually.

```bash
poni enforce                    # run all pre-commit checks
poni enforce --hook pre-commit  # run specific hook (git calls this)
poni enforce --hook pre-push
poni enforce --fix              # auto-fix what's possible
poni enforce --staged           # only staged files
```

---

### `poni migrate`

Migrate from existing tools.

```bash
poni migrate husky              # migrate from husky
poni migrate pre-commit         # migrate from pre-commit (python)
poni migrate lint-staged        # migrate lint-staged config
```

---

### `poni workflow` (future)

Ticket and PR management.

```bash
poni ticket show                # show current ticket (from branch)
poni ticket list                # list assigned tickets
poni ticket start ENG-123       # create branch, update status
poni ticket update              # sync progress

poni pr create                  # create PR linked to ticket
poni pr status                  # show checks, reviews
```

---

## Configuration Format

### Complete Config Example

```toml
# .poni/config.toml

[poni]
version = "0.1.0"
detected = ["typescript", "eslint", "prettier", "vitest"]  # from init
package_manager = "pnpm"

# =============================================================================
# SECRETS
# =============================================================================

[secrets]
source = "env"  # reads from .env and environment variables

# Future paid tier:
# source = "aws-secrets-manager"
# region = "us-east-1"
# prefix = "myapp/dev/"

# =============================================================================
# MCP SERVERS
# =============================================================================

[mcps.postgres]
command = "mcp-server-postgres"
args = ["--connection-string", "${DATABASE_URL}"]

[mcps.postgres.tools]
allow = ["query", "list_tables", "describe_table"]

[mcps.postgres.policies]
deny_patterns = [
  "DROP\\s+TABLE",
  "TRUNCATE",
  "DELETE\\s+FROM\\s+\\w+\\s*;$",
]

[mcps.github]
command = "mcp-server-github"
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }

[mcps.github.tools]
deny = ["delete_repository", "delete_branch"]

[mcps.filesystem]
command = "mcp-server-filesystem"
args = ["--root", "./"]

[mcps.filesystem.tools]
allow = ["read_file", "list_directory", "write_file"]

[mcps.filesystem.policies]
protected_paths = [".poni/**", ".mcp.json", ".env", ".git/**"]

# =============================================================================
# CLI TOOL WRAPPERS
# =============================================================================

[cli.aws]
description = "AWS CLI with guardrails"
command = "aws"
env = { AWS_PROFILE = "${AWS_PROFILE}" }

[cli.aws.policies]
allow_subcommands = ["s3", "dynamodb", "logs", "sts"]
deny_subcommands = ["iam", "ec2", "rds", "lambda"]
deny_patterns = [
  "s3 rm.*--recursive",
  "s3 rb",
  "dynamodb delete-table",
]

[cli.psql]
description = "PostgreSQL CLI with query restrictions"
command = "psql"
args = ["${DATABASE_URL}"]

[cli.psql.policies]
allow_patterns = [
  "^SELECT",
  "^\\\\d",
  "^\\\\dt",
  "^EXPLAIN",
]
deny_patterns = [
  "DROP",
  "TRUNCATE",
  "DELETE\\s+FROM\\s+\\w+\\s*;$",
  "ALTER",
  "CREATE",
]
interactive_patterns = ["^UPDATE", "^INSERT"]  # require confirmation
redact_patterns = ["password", "api_key", "secret"]
max_output_lines = 1000

[cli.kubectl]
description = "Kubernetes CLI - read only"
command = "kubectl"

[cli.kubectl.policies]
allow_subcommands = ["get", "describe", "logs", "top"]
deny_subcommands = ["delete", "apply", "edit", "patch", "exec"]
allowed_namespaces = ["development", "staging"]
denied_namespaces = ["production", "kube-system"]

[cli.docker]
description = "Docker CLI with restrictions"
command = "docker"

[cli.docker.policies]
allow_subcommands = ["ps", "logs", "images", "inspect", "build"]
deny_subcommands = ["rm", "rmi", "system prune", "volume rm"]
deny_patterns = ["--privileged", "-v /:/", "-v /etc:/"]

[cli.gh]
description = "GitHub CLI"
command = "gh"

[cli.gh.policies]
allow_subcommands = ["pr", "issue", "repo view", "api"]
deny_subcommands = ["repo delete", "api -X DELETE"]

[cli.terraform]
description = "Terraform - plan only"
command = "terraform"

[cli.terraform.policies]
allow_subcommands = ["plan", "show", "state list", "output", "validate"]
deny_subcommands = ["apply", "destroy", "import"]

# =============================================================================
# CUSTOM TEAM TOOLS
# =============================================================================

[tools.db-reset]
description = "Reset local database to clean state"
command = "make db-reset"
confirm = true

[tools.db-seed]
description = "Seed database with test data"
command = "make db-seed"

[tools.gen-types]
description = "Generate TypeScript types from OpenAPI"
command = "pnpm generate:types"
working_dir = "packages/api"

[tools.test-package]
description = "Run tests for a specific package"
command = "pnpm test --filter ${package} ${flags}"
args = ["package"]
optional_args = ["flags"]

[tools.deploy-staging]
description = "Deploy to staging"
command = "./scripts/deploy.sh staging"
confirm = true
confirm_message = "Deploy to staging?"
allowed_branches = ["main", "develop", "staging/*"]
timeout = 300

# =============================================================================
# ENFORCEMENT (replaces husky, lint-staged, pre-commit)
# =============================================================================

[enforcement]
enabled = true
parallel = true

# --- Pre-commit checks ---

[[enforcement.rules]]
name = "eslint"
trigger = "pre-commit"
command = "pnpm eslint --fix ${files}"
pattern = "**/*.{ts,tsx,js,jsx}"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "prettier"
trigger = "pre-commit"
command = "pnpm prettier --write ${files}"
pattern = "**/*.{ts,tsx,js,jsx,json,md}"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "no-console"
trigger = "pre-commit"
check = "pattern-absent"
pattern = "src/**/*.{ts,tsx}"
exclude = ["**/*.test.*", "**/*.spec.*"]
deny_pattern = "console\\.(log|debug|info)\\("
message = "Use logger instead of console methods"

[[enforcement.rules]]
name = "tests-required"
trigger = "pre-commit"
check = "test-coverage"
pattern = "src/**/*.ts"
test_pattern = "{src,tests}/**/*.{test,spec}.ts"

[[enforcement.rules]]
name = "no-todo-without-ticket"
trigger = "pre-commit"
check = "pattern-absent"
pattern = "src/**/*.{ts,py,rs}"
deny_pattern = "TODO(?!\\s*\\([A-Z]+-\\d+\\))"
message = "TODOs must reference a ticket: TODO(ENG-123)"

# --- Pre-push checks ---

[[enforcement.rules]]
name = "typecheck"
trigger = "pre-push"
command = "pnpm tsc --noEmit"

[[enforcement.rules]]
name = "tests-pass"
trigger = "pre-push"
command = "pnpm vitest run"

[[enforcement.rules]]
name = "no-wip-commits"
trigger = "pre-push"
check = "pattern-absent"
target = "commit-messages"
deny_pattern = "^(WIP|wip|fixup!)"
message = "Clean up WIP commits before pushing"

[[enforcement.rules]]
name = "no-main-push"
trigger = "pre-push"
check = "branch-protection"
protected = ["main", "production"]
message = "Create a PR instead of pushing directly"

# =============================================================================
# LIFECYCLE HOOKS (agent enforcement)
# =============================================================================

[lifecycle]
enabled = true

[[lifecycle.hooks]]
name = "post-write-lint"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.{ts,tsx}"
commands = ["pnpm eslint --fix ${file}", "pnpm prettier --write ${file}"]

[[lifecycle.hooks]]
name = "post-write-typecheck"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.{ts,tsx}"
commands = ["pnpm tsc --noEmit"]
block_until_pass = true
max_retries = 3
message = "Fix type errors before continuing"

[[lifecycle.hooks]]
name = "verify-before-done"
trigger = "before_response"
commands = ["pnpm vitest run", "pnpm tsc --noEmit"]
block_until_pass = true
message = "All tests must pass before completing"

# =============================================================================
# MEMORY
# =============================================================================

[memory]
enabled = true
max_entries_in_context = 20
relevance = "auto"  # "auto" = smart matching, "all" = include everything
categories = ["patterns", "decisions", "gotchas", "glossary"]

# =============================================================================
# DOCS
# =============================================================================

[docs]
enabled = true
output_dir = "docs/"

[[docs.targets]]
name = "api"
description = "API endpoint documentation"
paths = ["packages/api/src/**/*.ts"]
output = "docs/api.md"
prompt = """
Document all API endpoints including:
- HTTP method and path
- Request/response types
- Authentication requirements
- Example curl commands
"""

[[docs.targets]]
name = "database"
description = "Database schema documentation"
paths = ["prisma/schema.prisma"]
output = "docs/database.md"
prompt = "Document all tables, columns, relationships, and constraints"

[[docs.targets]]
name = "package-readmes"
description = "Individual package READMEs"
paths = ["packages/*/src/**"]
output = "packages/*/README.md"
per_directory = true
prompt_file = ".poni/prompts/package-readme.md"

# =============================================================================
# WORKFLOW (future)
# =============================================================================

# [workflow]
# ticket_system = "linear"
# pr_system = "github"
#
# [workflow.linear]
# api_key = "${LINEAR_API_KEY}"
# team_id = "ENG"
#
# [workflow.github]
# token = "${GITHUB_TOKEN}"
# repo = "org/repo"
#
# [workflow.conventions]
# branch_format = "{{ticket_id}}-{{slug}}"
# commit_format = "[{{ticket_id}}] {{message}}"
# pr_title_format = "[{{ticket_id}}] {{ticket_title}}"
```

---

## Presets

### TypeScript Preset

Applied with `poni init --preset typescript` or auto-detected.

```toml
[poni]
version = "0.1.0"
preset = "typescript"

[secrets]
source = "env"

[enforcement]
enabled = true

[[enforcement.rules]]
name = "eslint"
trigger = "pre-commit"
command = "npx eslint --fix ${files}"
pattern = "**/*.{ts,tsx,js,jsx}"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "prettier"
trigger = "pre-commit"
command = "npx prettier --write ${files}"
pattern = "**/*.{ts,tsx,js,jsx,json,md}"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "no-console"
trigger = "pre-commit"
check = "pattern-absent"
pattern = "src/**/*.{ts,tsx}"
exclude = ["**/*.test.*"]
deny_pattern = "console\\.(log|debug|info)\\("

[[enforcement.rules]]
name = "tests-required"
trigger = "pre-commit"
check = "test-coverage"
pattern = "src/**/*.ts"
test_pattern = "{src,tests}/**/*.{test,spec}.ts"

[[enforcement.rules]]
name = "typecheck"
trigger = "pre-push"
command = "npx tsc --noEmit"

[[enforcement.rules]]
name = "tests-pass"
trigger = "pre-push"
command = "npm test"

[lifecycle]
enabled = true

[[lifecycle.hooks]]
name = "post-write-lint"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.{ts,tsx}"
commands = ["npx eslint --fix ${file}", "npx prettier --write ${file}"]

[[lifecycle.hooks]]
name = "post-write-typecheck"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.{ts,tsx}"
commands = ["npx tsc --noEmit"]
block_until_pass = true

[[lifecycle.hooks]]
name = "verify-before-done"
trigger = "before_response"
commands = ["npm test", "npx tsc --noEmit"]
block_until_pass = true

[memory]
enabled = true
max_entries_in_context = 20
```

### Python Preset

Applied with `poni init --preset python` or auto-detected.

```toml
[poni]
version = "0.1.0"
preset = "python"

[secrets]
source = "env"

[enforcement]
enabled = true

[[enforcement.rules]]
name = "ruff"
trigger = "pre-commit"
command = "ruff check --fix ${files}"
pattern = "**/*.py"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "ruff-format"
trigger = "pre-commit"
command = "ruff format ${files}"
pattern = "**/*.py"
staged_only = true
auto_stage = true

[[enforcement.rules]]
name = "mypy"
trigger = "pre-commit"
command = "mypy ${files}"
pattern = "**/*.py"
staged_only = true

[[enforcement.rules]]
name = "tests-required"
trigger = "pre-commit"
check = "test-coverage"
pattern = "src/**/*.py"
test_pattern = "tests/**/test_*.py"

[[enforcement.rules]]
name = "tests-pass"
trigger = "pre-push"
command = "pytest"

[lifecycle]
enabled = true

[[lifecycle.hooks]]
name = "post-write-lint"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.py"
commands = ["ruff check --fix ${file}", "ruff format ${file}"]

[[lifecycle.hooks]]
name = "post-write-typecheck"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.py"
commands = ["mypy ${file}"]
block_until_pass = true

[[lifecycle.hooks]]
name = "verify-before-done"
trigger = "before_response"
commands = ["pytest", "mypy ."]
block_until_pass = true

[memory]
enabled = true
max_entries_in_context = 20
```

### Rust Preset

```toml
[poni]
version = "0.1.0"
preset = "rust"

[enforcement]
enabled = true

[[enforcement.rules]]
name = "rustfmt"
trigger = "pre-commit"
command = "cargo fmt -- --check"
pattern = "**/*.rs"

[[enforcement.rules]]
name = "clippy"
trigger = "pre-commit"
command = "cargo clippy -- -D warnings"
pattern = "**/*.rs"

[[enforcement.rules]]
name = "tests-pass"
trigger = "pre-push"
command = "cargo test"

[lifecycle]
enabled = true

[[lifecycle.hooks]]
name = "post-write-check"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.rs"
commands = ["cargo fmt", "cargo clippy -- -D warnings"]
block_until_pass = true

[[lifecycle.hooks]]
name = "verify-before-done"
trigger = "before_response"
commands = ["cargo test", "cargo clippy -- -D warnings"]
block_until_pass = true
```

---

## Memory Format

### `.poni/memory/patterns.toml`

```toml
[[entries]]
id = "pat-001"
added_by = "oleks"
added_at = "2025-01-13"
content = "Use factoryCreate() not new Constructor() for all models"
context = "Ensures proper DI injection and testability"
files = ["src/models/**"]

[[entries]]
id = "pat-002"
added_by = "sarah"
added_at = "2025-01-10"
content = "All API responses must use ResponseWrapper<T>"
context = "Standardizes error handling and pagination"
files = ["src/api/**", "src/controllers/**"]
```

### `.poni/memory/gotchas.toml`

```toml
[[entries]]
id = "got-001"
added_by = "mike"
added_at = "2025-01-08"
content = "Redis connection must be closed manually in tests"
context = "Jest doesn't clean up connections, causes hanging tests"
files = ["**/*.test.ts"]
```

### `.poni/memory/decisions.toml`

```toml
[[entries]]
id = "dec-001"
added_by = "oleks"
added_at = "2025-01-05"
content = "We use event sourcing for audit logs"
context = "See ADR-012 for full rationale"
```

### `.poni/memory/glossary.toml`

```toml
[[entries]]
id = "glo-001"
added_by = "oleks"
added_at = "2025-01-13"
content = "SKU = internal product identifier, not customer-facing"
```

---

## Prompt Format

### `.poni/prompts/code-review.toml`

```toml
[prompt]
name = "code-review"
description = "Review code for quality and security issues"

[prompt.content]
text = """
Review this code for:
- Security vulnerabilities
- Performance issues
- Code style violations

Provide specific line references and suggested fixes.
"""

[prompt.tools]
allow = ["read_file", "list_directory"]

[prompt.files]
include = ["src/**/*.ts", "src/**/*.tsx"]
exclude = ["**/*.test.ts", "node_modules/**"]
```

---

## Project Detection

### Detection Sources

| File | Detects |
|------|---------|
| `package.json` | typescript, eslint, prettier, biome, jest, vitest, mocha |
| `.eslintrc*` | eslint config |
| `.prettierrc*` | prettier config |
| `biome.json` | biome (replaces eslint+prettier) |
| `tsconfig.json` | typescript |
| `.husky/` | existing hooks to migrate |
| `lint-staged.config*` | staged file config |
| `pyproject.toml` | ruff, black, mypy, pytest, flake8, isort |
| `.pre-commit-config.yaml` | existing python hooks |
| `Cargo.toml` | rust project |
| `rustfmt.toml` | rust format config |
| `go.mod` | go project |
| `.golangci.yml` | golangci-lint |
| `pnpm-lock.yaml` | pnpm package manager |
| `yarn.lock` | yarn package manager |
| `package-lock.json` | npm package manager |

### Detection Flow

```rust
// Pseudocode
fn detect_project() -> ProjectConfig {
    let mut config = ProjectConfig::default();
    
    // Detect package manager
    if exists("pnpm-lock.yaml") { config.pkg_manager = "pnpm"; }
    else if exists("yarn.lock") { config.pkg_manager = "yarn"; }
    else if exists("package-lock.json") { config.pkg_manager = "npm"; }
    
    // JavaScript/TypeScript
    if let Some(pkg) = read_package_json() {
        if pkg.has_dep("typescript") { config.add("typescript"); }
        if pkg.has_dep("eslint") { config.add_tool("eslint"); }
        if pkg.has_dep("prettier") { config.add_tool("prettier"); }
        if pkg.has_dep("biome") { config.add_tool("biome"); }
        if pkg.has_dep("jest") { config.add_tool("jest"); }
        if pkg.has_dep("vitest") { config.add_tool("vitest"); }
    }
    
    // Python
    if let Some(pyproject) = read_pyproject_toml() {
        config.add("python");
        if pyproject.has_tool("ruff") { config.add_tool("ruff"); }
        if pyproject.has_tool("black") { config.add_tool("black"); }
        if pyproject.has_tool("mypy") { config.add_tool("mypy"); }
        if pyproject.has_tool("pytest") { config.add_tool("pytest"); }
    }
    
    // Rust
    if exists("Cargo.toml") {
        config.add("rust");
        config.add_tool("rustfmt");
        config.add_tool("clippy");
    }
    
    // Migrate existing hooks
    if exists(".husky/") { config.migrate_husky(); }
    if exists(".pre-commit-config.yaml") { config.migrate_precommit(); }
    
    config
}
```

---

## Lifecycle Hook Triggers

| Trigger | When |
|---------|------|
| `after_tool:<name>` | After specific MCP tool call |
| `after_tool:*` | After any tool call |
| `before_response` | Before agent responds to user |
| `after_prompt:<name>` | After specific poni prompt |
| `on_file_change` | When matched files change |

### Blocking Behavior

```toml
[[lifecycle.hooks]]
name = "post-write-typecheck"
trigger = "after_tool:filesystem.write_file"
pattern = "**/*.ts"
commands = ["pnpm tsc --noEmit"]
block_until_pass = true   # agent cannot continue until fixed
max_retries = 3           # give up after 3 attempts
message = "Fix type errors before continuing"
```

**Agent experience:**

```
Agent: [writes src/api/users.ts]

Poni: ⚠️ Post-write checks failed:

  ✗ pnpm tsc --noEmit
    src/api/users.ts:15:3 - error TS2345: Argument of type 'string' 
    is not assignable to parameter of type 'number'

Fix these errors before continuing. (Attempt 1/3)

Agent: [fixes the error]

Poni: ✓ All checks passed. Continuing.
```

---

## Enforcement Check Types

| Check | Description |
|-------|-------------|
| `command` | Run shell command, non-zero = fail |
| `pattern-absent` | Deny pattern must not exist in files |
| `pattern-present` | Require pattern must exist in files |
| `test-coverage` | New code must have corresponding test file |
| `file-pair` | Related file must exist (e.g., migration + rollback) |
| `branch-protection` | Block push to protected branches |

---

## CLI Wrapper Policy Options

```toml
[cli.example]
command = "example-cli"
description = "Example CLI tool"

[cli.example.policies]
# Subcommand filtering
allow_subcommands = ["read", "list", "get"]
deny_subcommands = ["delete", "drop", "rm"]

# Pattern matching on full command
allow_patterns = ["^SELECT", "^GET"]
deny_patterns = ["DROP.*TABLE", "--force"]

# Require certain patterns/flags
require_patterns = ["LIMIT \\d+"]
require_flags = ["--profile", "--region"]

# Namespace/context restrictions (for kubectl, etc.)
allowed_namespaces = ["dev", "staging"]
denied_namespaces = ["production", "kube-system"]

# Interactive confirmation
interactive_patterns = ["^UPDATE", "^INSERT"]

# Output handling
redact_patterns = ["password", "secret", "api_key"]
max_output_lines = 1000
```

---

## Dependencies

```toml
[package]
name = "poni"
version = "0.1.0"
edition = "2021"

[dependencies]
# CLI
clap = { version = "4", features = ["derive"] }

# Async runtime
tokio = { version = "1", features = ["full", "process"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"

# Environment/secrets
dotenvy = "0.15"

# Patterns and paths
regex = "1"
glob = "0.3"

# Hashing
sha2 = "0.10"
hex = "0.4"

# Time
chrono = { version = "0.4", features = ["serde"] }

# Logging
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

# MCP SDK (verify current crate name on crates.io)
rmcp = { version = "0.1", features = ["server", "client", "transport-stdio"] }

# Git
git2 = "0.18"

# Process management
which = "6"  # find executables
```

---

## Error Messages

All errors should be actionable:

```
Error: Secret 'DATABASE_URL' not found

Add it to your .env file:
  DATABASE_URL=postgres://user:pass@localhost/db

Or set as environment variable:
  export DATABASE_URL=postgres://user:pass@localhost/db
```

```
Error: Policy violation in tool 'poni.cli.aws'

Blocked by: deny_patterns
Pattern: "s3 rm.*--recursive"
Command: aws s3 rm s3://bucket/ --recursive

Recursive S3 deletion is not allowed by team policy.
```

```
Error: Enforcement check failed: tests-required

You modified src/api/users.ts but no test file exists.
Expected: src/api/users.test.ts or tests/api/users.test.ts

Write tests before committing.
```

```
Error: Lifecycle hook blocked: post-write-typecheck

  ✗ pnpm tsc --noEmit
    src/api/users.ts:15:3 - error TS2345

Fix type errors before continuing. (Attempt 2/3)
```

---

## MCP Tools Exposed

When running, Poni exposes these tools to agents:

**From child MCPs (prefixed):**
```
postgres.query
postgres.list_tables
github.create_issue
github.list_prs
filesystem.read_file
filesystem.write_file
```

**From CLI wrappers:**
```
poni.cli.aws
poni.cli.psql
poni.cli.kubectl
poni.cli.docker
poni.cli.gh
poni.cli.terraform
```

**From custom tools:**
```
poni.db-reset
poni.db-seed
poni.test-package
poni.deploy-staging
```

**Built-in:**
```
poni.memory_add
poni.memory_search
poni.docs_generate
poni.enforce
```

---

## Git Hooks

Poni installs these hooks in `.git/hooks/`:

**pre-commit:**
```bash
#!/bin/sh
exec poni enforce --hook pre-commit
```

**pre-push:**
```bash
#!/bin/sh
exec poni enforce --hook pre-push
```

---

## Out of Scope for v0.1.0

- Container runtime integration (container-use)
- AWS Secrets Manager / Vault / other secret backends
- Dashboard / team management UI
- Audit log persistence
- Prompt chaining / composition
- Cost tracking
- Workflow integration (Linear, Jira)
- AST-based policies (tree-sitter, ast-grep)

---

## Success Criteria

### Core
- [ ] `poni init` detects project setup and generates config
- [ ] `poni init --preset <x>` applies preset config
- [ ] `poni validate` catches config errors
- [ ] `poni serve` runs as MCP server
- [ ] Git hooks installed and working

### MCP Proxy
- [ ] Tool calls proxied to child MCPs
- [ ] Tool allow/deny lists enforced
- [ ] Regex deny_patterns block matching inputs
- [ ] Secrets resolved from .env

### CLI Wrappers
- [ ] CLI tools exposed as MCP tools
- [ ] Subcommand allow/deny enforced
- [ ] Pattern policies enforced
- [ ] Output redaction working
- [ ] Interactive confirmation working

### Enforcement
- [ ] Pre-commit rules run on commit
- [ ] Pre-push rules run on push
- [ ] Auto-fix and auto-stage working
- [ ] Pattern checks working
- [ ] Test coverage check working

### Lifecycle Hooks
- [ ] Hooks trigger after file writes
- [ ] Hooks trigger before response
- [ ] Block until pass working
- [ ] Max retries working

### Memory
- [ ] `poni memory add` creates entries
- [ ] `poni memory list` shows entries
- [ ] `poni memory search` finds entries
- [ ] Memory injected into agent context
- [ ] Relevance matching working

### Docs
- [ ] `poni docs generate` creates docs
- [ ] `poni docs generate --changed` incremental
- [ ] Lock file tracks state
- [ ] Generated files have header

### Tools
- [ ] `poni tools list` shows tools
- [ ] `poni run <tool>` executes
- [ ] Argument substitution working
- [ ] Confirm flag working
- [ ] Branch restrictions working

---

## Future Paid Features

| Feature | Free | Paid |
|---------|------|------|
| MCP proxy | ✓ | ✓ |
| Memory | ✓ | ✓ |
| Docs | ✓ | ✓ |
| Tools | ✓ | ✓ |
| CLI wrappers | ✓ | ✓ |
| Enforcement | ✓ | ✓ |
| Lifecycle hooks | ✓ | ✓ |
| .env secrets | ✓ | ✓ |
| AWS Secrets Manager | - | ✓ |
| Vault / GCP / Azure | - | ✓ |
| 1Password / Doppler | - | ✓ |
| Dashboard | - | ✓ |
| Audit logs | - | ✓ |
| Team management | - | ✓ |
| SSO | - | ✓ |

---

## References

- MCP Specification: https://modelcontextprotocol.io/
- Rust MCP SDK: Check crates.io for latest
- TOML format: https://toml.io/
- Container Use: https://github.com/dagger/container-use
