"""Lock file management for incremental doc generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import tomlkit

from poni.config.loader import get_poni_dir
from poni.config.models import DocsTarget


@dataclass
class DocLockEntry:
    """Entry in the docs lock file."""

    target: str
    source_hash: str
    generated_at: str
    output_path: str


class DocsLock:
    """Manager for the docs lock file."""

    def __init__(self) -> None:
        """Initialize the docs lock manager."""
        self.poni_dir = get_poni_dir()
        self.lock_path = self.poni_dir / "docs" / ".lock.toml"

    def load(self) -> dict[str, DocLockEntry]:
        """Load the lock file.

        Returns:
            Dict mapping target names to lock entries.
        """
        if not self.lock_path.exists():
            return {}

        try:
            with open(self.lock_path) as f:
                data = tomlkit.load(f)

            entries = {}
            for target, entry in data.get("targets", {}).items():
                entries[target] = DocLockEntry(
                    target=target,
                    source_hash=entry.get("source_hash", ""),
                    generated_at=entry.get("generated_at", ""),
                    output_path=entry.get("output_path", ""),
                )
            return entries
        except Exception:
            return {}

    def save(self, entries: dict[str, DocLockEntry]) -> None:
        """Save the lock file.

        Args:
            entries: Dict mapping target names to lock entries.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        data = tomlkit.document()
        targets = tomlkit.table()

        for name, entry in entries.items():
            targets[name] = {
                "source_hash": entry.source_hash,
                "generated_at": entry.generated_at,
                "output_path": entry.output_path,
            }

        data["targets"] = targets

        with open(self.lock_path, "w") as f:
            tomlkit.dump(data, f)

    def compute_hash(self, paths: list[str], base_dir: Path | None = None) -> str:
        """Compute hash of source files.

        Args:
            paths: Glob patterns for source files.
            base_dir: Base directory for relative paths.

        Returns:
            Hash string of all source content.
        """
        if base_dir is None:
            base_dir = Path.cwd()

        hasher = hashlib.sha256()

        # Collect all matching files
        files: list[Path] = []
        for pattern in paths:
            files.extend(base_dir.glob(pattern))

        # Sort for deterministic hashing
        files.sort()

        for file_path in files:
            if file_path.is_file():
                try:
                    content = file_path.read_bytes()
                    hasher.update(content)
                except OSError:
                    pass

        return hasher.hexdigest()[:16]

    def needs_regeneration(
        self,
        target: DocsTarget,
        base_dir: Path | None = None,
    ) -> bool:
        """Check if a target needs regeneration.

        Args:
            target: The docs target configuration.
            base_dir: Base directory for source files.

        Returns:
            True if regeneration is needed.
        """
        entries = self.load()
        entry = entries.get(target.name)

        if not entry:
            return True

        current_hash = self.compute_hash(target.paths, base_dir)
        return current_hash != entry.source_hash

    def update(
        self,
        target: DocsTarget,
        output_path: str,
        base_dir: Path | None = None,
    ) -> None:
        """Update lock file after generation.

        Args:
            target: The docs target configuration.
            output_path: Path to the generated output.
            base_dir: Base directory for source files.
        """
        entries = self.load()

        source_hash = self.compute_hash(target.paths, base_dir)

        entries[target.name] = DocLockEntry(
            target=target.name,
            source_hash=source_hash,
            generated_at=datetime.now().isoformat(),
            output_path=output_path,
        )

        self.save(entries)
