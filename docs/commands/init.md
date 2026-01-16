### `poni init`

Initializes Poni in the current repository with smart detection.

```bash
poni init                     # detect and generate config
poni init --preset typescript # use preset instead of detection
poni init --preset python
poni init --preset rust
poni init --preset go
poni init --preset monorepo
poni init --yes               # accept all defaults, no prompts
poni init --detect-only       # show what would be detected
```

**Behavior:**

1. Detect existing project setup:
   - `package.json` → eslint, prettier, biome, jest, vitest, typescript
   - `pyproject.toml` → ruff, black, mypy, pytest, flake8
   - `Cargo.toml` → rustfmt, clippy
   - `go.mod` → golangci-lint
   - `.husky/` → migrate existing hooks
   - `.pre-commit-config.yaml` → migrate existing hooks
   - Detect package manager (npm, pnpm, yarn, pip, cargo)

2. Generate `.poni/config.toml` based on detection

3. Create directory structure:
   ```
   .poni/
   ├── config.toml
   ├── prompts/
   ├── memory/
   │   ├── patterns.toml
   │   ├── decisions.toml
   │   ├── gotchas.toml
   │   └── glossary.toml
   └── docs/
       └── .lock.toml
   ```

4. Create/update `.mcp.json`:
   ```json
   {
     "mcpServers": {
       "poni": {
         "command": "poni",
         "args": ["serve"],
         "type": "stdio"
       }
     }
   }
   ```

5. Install git hooks (`.git/hooks/pre-commit`, `.git/hooks/pre-push`)

6. Update `.gitignore` with `.poni/.secrets.toml`

7. Print setup instructions

**Example Output:**

```
Detecting project setup...

Found:
  ✓ package.json (typescript, eslint, prettier, vitest)
  ✓ .eslintrc.js
  ✓ .prettierrc
  ✓ tsconfig.json
  ✓ .husky/ (existing hooks - will migrate)
  ✓ pnpm-lock.yaml (using pnpm)

Generated .poni/config.toml with:
  • ESLint + Prettier on commit
  • TypeScript type checking
  • Vitest for tests
  • Lifecycle hooks for agent enforcement

Migrated from .husky/:
  • pre-commit: eslint, prettier
  • pre-push: tsc, vitest

✓ Installed git hooks
✓ Created .poni/

Next steps:
  1. Review .poni/config.toml
  2. Remove .husky/ when ready (Poni handles hooks now)
  3. Commit .poni/ and .mcp.json to git

Configure Claude Code:
  Run 'claude config' and deny all tools except 'poni'
```
