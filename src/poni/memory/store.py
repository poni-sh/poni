"""Memory storage for Poni."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import tomlkit

from poni.config.loader import get_poni_dir
from poni.config.models import Config


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    content: str
    category: str
    added_by: str
    added_at: str
    context: str | None = None
    files: list[str] | None = None


class MemoryStore:
    """Store for shared team memory."""

    def __init__(self, config: Config):
        """Initialize the memory store.

        Args:
            config: The Poni configuration.
        """
        self.config = config.memory
        self.poni_dir = get_poni_dir()
        self.memory_dir = self.poni_dir / "memory"

    def list_entries(self, category: str | None = None) -> list[MemoryEntry]:
        """List all memory entries, optionally filtered by category.

        Args:
            category: Optional category to filter by.

        Returns:
            List of memory entries.
        """
        entries: list[MemoryEntry] = []

        categories = [category] if category else self.config.categories

        for cat in categories:
            file_path = self.memory_dir / f"{cat}.toml"
            if not file_path.exists():
                continue

            try:
                with open(file_path) as f:
                    data = tomlkit.load(f)

                for entry in data.get("entries", []):
                    entries.append(
                        MemoryEntry(
                            id=entry["id"],
                            content=entry["content"],
                            category=cat,
                            added_by=entry.get("added_by", "unknown"),
                            added_at=entry.get("added_at", "unknown"),
                            context=entry.get("context"),
                            files=entry.get("files"),
                        )
                    )
            except (OSError, tomlkit.exceptions.TOMLKitError):
                continue

        return entries

    def add(
        self,
        content: str,
        category: str = "patterns",
        context: str | None = None,
        files: list[str] | None = None,
    ) -> MemoryEntry:
        """Add a new memory entry.

        Args:
            content: The memory content.
            category: The category (patterns, decisions, gotchas, glossary).
            context: Optional additional context.
            files: Optional file patterns this relates to.

        Returns:
            The created memory entry.
        """
        # Ensure memory directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)

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
        added_by = self._get_git_user()

        # Create entry
        entry = tomlkit.table()
        entry["id"] = entry_id
        entry["added_by"] = added_by
        entry["added_at"] = datetime.now().strftime("%Y-%m-%d")
        entry["content"] = content
        if context:
            entry["context"] = context
        if files:
            entry["files"] = files

        # Add to file
        if "entries" not in data:
            data["entries"] = tomlkit.aot()
        data["entries"].append(entry)  # type: ignore[union-attr, call-arg, arg-type]

        with open(file_path, "w") as f:
            tomlkit.dump(data, f)

        return MemoryEntry(
            id=entry_id,
            content=content,
            category=category,
            added_by=added_by,
            added_at=str(entry["added_at"]),
            context=context,
            files=files,
        )

    def remove(self, entry_id: str) -> bool:
        """Remove a memory entry by ID.

        Args:
            entry_id: The ID of the entry to remove.

        Returns:
            True if removed, False if not found.
        """
        for cat in self.config.categories:
            file_path = self.memory_dir / f"{cat}.toml"
            if not file_path.exists():
                continue

            try:
                with open(file_path) as f:
                    data = tomlkit.load(f)

                entries = data.get("entries", [])
                for i, entry in enumerate(entries):
                    if entry["id"] == entry_id:
                        del entries[i]
                        with open(file_path, "w") as f:
                            tomlkit.dump(data, f)
                        return True
            except (OSError, tomlkit.exceptions.TOMLKitError):
                continue

        return False

    def search(self, query: str) -> list[MemoryEntry]:
        """Search memory entries by content.

        Args:
            query: The search query.

        Returns:
            List of matching entries.
        """
        query_lower = query.lower()
        results: list[MemoryEntry] = []

        for entry in self.list_entries():
            if query_lower in entry.content.lower():
                results.append(entry)
            elif entry.context and query_lower in entry.context.lower():
                results.append(entry)

        return results

    def get_relevant(self, files: list[str] | None = None) -> list[MemoryEntry]:
        """Get relevant memory entries for context injection.

        Args:
            files: Optional list of files to match against.

        Returns:
            Relevant memory entries.
        """
        if not self.config.enabled:
            return []

        if self.config.relevance == "all":
            entries = self.list_entries()
        else:
            # TODO: Implement smart relevance matching based on files
            entries = self.list_entries()

        return entries[: self.config.max_entries_in_context]

    def _get_git_user(self) -> str:
        """Get the current git user name.

        Returns:
            Git user name or 'unknown'.
        """
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            name = repo.config_reader().get_value("user", "name")
            return str(name)
        except Exception:
            return "unknown"
