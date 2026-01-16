"""Tests for memory store."""

from pathlib import Path

import pytest

from poni.config.models import Config, MemoryConfig
from poni.memory.store import MemoryStore


@pytest.fixture
def memory_config(tmp_path: Path, monkeypatch) -> Config:
    """Create a config for memory testing."""
    # Create .poni/memory directory
    poni_dir = tmp_path / ".poni"
    poni_dir.mkdir()
    memory_dir = poni_dir / "memory"
    memory_dir.mkdir()

    # Create config.toml so get_poni_dir works
    config_path = poni_dir / "config.toml"
    config_path.write_text('[poni]\nversion = "0.1.0"\n')

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    return Config(
        memory=MemoryConfig(
            enabled=True,
            max_entries_in_context=10,
            categories=["patterns", "decisions", "gotchas"],
        )
    )


@pytest.fixture
def store(memory_config: Config) -> MemoryStore:
    """Create a memory store instance."""
    return MemoryStore(memory_config)


class TestMemoryStore:
    """Tests for MemoryStore class."""

    def test_list_empty(self, store: MemoryStore):
        """Test listing when no entries exist."""
        entries = store.list_entries()
        assert entries == []

    def test_add_entry(self, store: MemoryStore):
        """Test adding a memory entry."""
        entry = store.add("Test pattern", category="patterns")
        assert entry.id == "pat-001"
        assert entry.content == "Test pattern"
        assert entry.category == "patterns"

    def test_add_multiple_entries(self, store: MemoryStore):
        """Test adding multiple entries generates unique IDs."""
        entry1 = store.add("Pattern 1", category="patterns")
        entry2 = store.add("Pattern 2", category="patterns")
        entry3 = store.add("Decision 1", category="decisions")

        assert entry1.id == "pat-001"
        assert entry2.id == "pat-002"
        assert entry3.id == "dec-001"

    def test_list_entries(self, store: MemoryStore):
        """Test listing all entries."""
        store.add("Pattern 1", category="patterns")
        store.add("Decision 1", category="decisions")

        entries = store.list_entries()
        assert len(entries) == 2

    def test_list_by_category(self, store: MemoryStore):
        """Test filtering by category."""
        store.add("Pattern 1", category="patterns")
        store.add("Pattern 2", category="patterns")
        store.add("Decision 1", category="decisions")

        patterns = store.list_entries(category="patterns")
        assert len(patterns) == 2
        assert all(e.category == "patterns" for e in patterns)

    def test_remove_entry(self, store: MemoryStore):
        """Test removing an entry."""
        entry = store.add("To be removed", category="patterns")
        assert store.remove(entry.id) is True

        entries = store.list_entries()
        assert len(entries) == 0

    def test_remove_nonexistent(self, store: MemoryStore):
        """Test removing a nonexistent entry."""
        assert store.remove("pat-999") is False

    def test_search_by_content(self, store: MemoryStore):
        """Test searching entries by content."""
        store.add("Use async/await for IO", category="patterns")
        store.add("Prefer composition over inheritance", category="patterns")
        store.add("Database uses async", category="decisions")

        results = store.search("async")
        assert len(results) == 2
        assert all("async" in e.content.lower() for e in results)

    def test_search_by_context(self, store: MemoryStore):
        """Test searching entries by context."""
        store.add("Pattern 1", category="patterns", context="Python specific")
        store.add("Pattern 2", category="patterns", context="JavaScript only")

        results = store.search("Python")
        assert len(results) == 1
        assert results[0].context == "Python specific"

    def test_search_case_insensitive(self, store: MemoryStore):
        """Test that search is case insensitive."""
        store.add("Use UPPERCASE names", category="patterns")

        results = store.search("uppercase")
        assert len(results) == 1

    def test_add_with_context(self, store: MemoryStore):
        """Test adding entry with context."""
        entry = store.add(
            "Use dependency injection",
            category="patterns",
            context="For testability",
        )
        assert entry.context == "For testability"

    def test_add_with_files(self, store: MemoryStore):
        """Test adding entry with file patterns."""
        entry = store.add(
            "Error handling pattern",
            category="patterns",
            files=["src/**/*.py"],
        )
        assert entry.files == ["src/**/*.py"]

    def test_get_relevant_respects_max(self, store: MemoryStore):
        """Test that get_relevant respects max_entries_in_context."""
        for i in range(20):
            store.add(f"Pattern {i}", category="patterns")

        relevant = store.get_relevant()
        assert len(relevant) == 10  # max_entries_in_context

    def test_get_relevant_when_disabled(self, store: MemoryStore):
        """Test get_relevant when memory is disabled."""
        store.add("Pattern 1", category="patterns")
        store.config.enabled = False

        relevant = store.get_relevant()
        assert relevant == []
