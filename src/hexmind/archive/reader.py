"""ArchiveReader: load structured archive data from disk."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from hexmind.models.tree import DecisionSummary


class ArchiveEntry:
    """Single archive entry loaded from disk."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._meta: dict | None = None
        self._summary: DecisionSummary | None = None

    @property
    def meta(self) -> dict:
        if self._meta is None:
            meta_path = self.path / "meta.yaml"
            if meta_path.exists():
                self._meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            else:
                self._meta = {}
        return self._meta

    @property
    def question(self) -> str:
        return self.meta.get("question", "")

    @property
    def status(self) -> str:
        return self.meta.get("status", "unknown")

    @property
    def confidence(self) -> str:
        return self.meta.get("confidence", "")

    @property
    def created_at(self) -> str:
        return self.meta.get("created_at", "")

    @property
    def personas(self) -> list[str]:
        return self.meta.get("personas", [])

    @property
    def verdict(self) -> str:
        return self.meta.get("verdict", "")

    @property
    def summary(self) -> DecisionSummary | None:
        if self._summary is None:
            summary_path = self.path / "decision_summary.json"
            if summary_path.exists():
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                self._summary = DecisionSummary.model_validate(data)
        return self._summary

    @property
    def discussion_md(self) -> str:
        md_path = self.path / "discussion.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")
        return ""

    @property
    def dir_name(self) -> str:
        return self.path.name


class ArchiveReader:
    """Load and enumerate discussion archives from a directory."""

    def __init__(self, archive_dir: str = "discussion_archive") -> None:
        self.archive_dir = Path(archive_dir)

    def list_entries(self) -> list[ArchiveEntry]:
        """List all archive entries, sorted by directory name (newest first)."""
        if not self.archive_dir.exists():
            return []
        entries = []
        for child in sorted(self.archive_dir.iterdir(), reverse=True):
            if child.is_dir() and (child / "meta.yaml").exists():
                entries.append(ArchiveEntry(child))
        return entries

    def get_entry(self, dir_name: str) -> ArchiveEntry | None:
        """Get a specific archive entry by directory name."""
        path = (self.archive_dir / dir_name).resolve()
        if not path.is_relative_to(self.archive_dir.resolve()):
            return None
        if path.is_dir() and (path / "meta.yaml").exists():
            return ArchiveEntry(path)
        return None

    def latest(self) -> ArchiveEntry | None:
        """Get the most recent archive entry."""
        entries = self.list_entries()
        return entries[0] if entries else None
