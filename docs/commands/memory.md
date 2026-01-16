### `poni memory`

Manage shared team memory.

```bash
poni memory list                     # list all entries
poni memory list --category gotchas  # filter by category
poni memory add "content"            # add to patterns (default)
poni memory add -c gotchas "content" # add to specific category
poni memory add -c patterns -f "src/api/**" "Use ResponseWrapper<T>"
poni memory remove <id>              # remove entry
poni memory search "query"           # search entries
```

**Categories:** `patterns`, `decisions`, `gotchas`, `glossary`
