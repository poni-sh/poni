### `poni serve`

Runs Poni as an MCP server. Called by Claude Code via `.mcp.json`.

**Behavior:**

1. Load and parse `.poni/config.toml`
2. Resolve secrets from configured source
3. Load memory entries from `.poni/memory/`
4. Start child MCP processes
5. Expose aggregated tools:
   - Tools from child MCPs (filtered by allow/deny)
   - Custom team tools
   - CLI wrappers (aws, psql, kubectl, etc.)
   - Built-in poni tools
6. Expose prompts from `.poni/prompts/`
7. Inject relevant memory into context
8. Handle tool calls with policy enforcement
9. Execute lifecycle hooks on file changes
10. Log all activity
