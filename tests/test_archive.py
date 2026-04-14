"""Tests for archive/reader.py and archive/search.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hexmind.archive.reader import ArchiveEntry, ArchiveReader
from hexmind.archive.search import ArchiveSearch, SearchResult


# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture
def archive_dir(tmp_path: Path) -> Path:
    """Create a temporary archive with two entries."""
    # Entry 1
    entry1 = tmp_path / "2025-01-15_should-we-use-rust"
    entry1.mkdir()
    (entry1 / "meta.yaml").write_text(
        yaml.dump(
            {
                "question": "Should we use Rust?",
                "status": "completed",
                "confidence": "high",
                "verdict": "Yes, for performance-critical modules",
                "personas": ["backend-engineer", "tech-lead"],
                "created_at": "2025-01-15T10:00:00Z",
                "rounds": 3,
                "forks": 0,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (entry1 / "discussion.md").write_text(
        "# Discussion: Should we use Rust?\n\n## Round 1 - White Hat\nW1: Rust has zero-cost abstractions\n",
        encoding="utf-8",
    )
    (entry1 / "decision_summary.json").write_text(
        json.dumps(
            {
                "question": "Should we use Rust?",
                "options": ["Yes", "No"],
                "benefits": {"general": ["Performance"]},
                "costs": {"general": ["Learning curve"]},
                "risks": ["Team unfamiliarity"],
                "evidence": [],
                "decision": "Adopt Rust for backend services",
                "reasoning": "Performance gains outweigh learning cost",
                "dissents": [],
                "confidence": "high",
                "next_actions": ["Start POC"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Entry 2
    entry2 = tmp_path / "2025-01-10_database-migration"
    entry2.mkdir()
    (entry2 / "meta.yaml").write_text(
        yaml.dump(
            {
                "question": "Database migration strategy",
                "status": "partial",
                "confidence": "medium",
                "verdict": "Phased migration recommended",
                "personas": ["cfo", "backend-engineer"],
                "created_at": "2025-01-10T08:00:00Z",
                "rounds": 2,
                "forks": 1,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (entry2 / "discussion.md").write_text(
        "# Discussion: Database migration\n\nSome content about PostgreSQL\n",
        encoding="utf-8",
    )
    (entry2 / "decision_summary.json").write_text(
        json.dumps(
            {
                "question": "Database migration strategy",
                "options": ["Big bang", "Phased"],
                "benefits": {},
                "costs": {},
                "risks": ["Downtime risk"],
                "evidence": [],
                "decision": "Phased migration",
                "reasoning": "Lower risk",
                "dissents": [],
                "confidence": "medium",
                "next_actions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Non-archive directory (no meta.yaml)
    (tmp_path / "random-folder").mkdir()

    return tmp_path


# ── ArchiveEntry tests ─────────────────────────────────────


def test_entry_loads_meta(archive_dir: Path):
    entry = ArchiveEntry(archive_dir / "2025-01-15_should-we-use-rust")
    assert entry.question == "Should we use Rust?"
    assert entry.status == "completed"
    assert entry.confidence == "high"


def test_entry_loads_summary(archive_dir: Path):
    entry = ArchiveEntry(archive_dir / "2025-01-15_should-we-use-rust")
    summary = entry.summary
    assert summary is not None
    assert summary.decision == "Adopt Rust for backend services"
    assert summary.confidence == "high"


def test_entry_loads_discussion_md(archive_dir: Path):
    entry = ArchiveEntry(archive_dir / "2025-01-15_should-we-use-rust")
    md = entry.discussion_md
    assert "Round 1" in md
    assert "Rust" in md


def test_entry_dir_name(archive_dir: Path):
    entry = ArchiveEntry(archive_dir / "2025-01-15_should-we-use-rust")
    assert entry.dir_name == "2025-01-15_should-we-use-rust"


def test_entry_personas(archive_dir: Path):
    entry = ArchiveEntry(archive_dir / "2025-01-15_should-we-use-rust")
    assert "backend-engineer" in entry.personas


def test_entry_missing_meta_returns_defaults(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    entry = ArchiveEntry(empty_dir)
    assert entry.question == ""
    assert entry.status == "unknown"
    assert entry.summary is None
    assert entry.discussion_md == ""


# ── ArchiveReader tests ────────────────────────────────────


def test_reader_list_entries(archive_dir: Path):
    reader = ArchiveReader(str(archive_dir))
    entries = reader.list_entries()
    assert len(entries) == 2
    # Sorted newest first
    assert entries[0].dir_name == "2025-01-15_should-we-use-rust"
    assert entries[1].dir_name == "2025-01-10_database-migration"


def test_reader_get_entry(archive_dir: Path):
    reader = ArchiveReader(str(archive_dir))
    entry = reader.get_entry("2025-01-10_database-migration")
    assert entry is not None
    assert entry.question == "Database migration strategy"


def test_reader_get_entry_missing(archive_dir: Path):
    reader = ArchiveReader(str(archive_dir))
    assert reader.get_entry("nonexistent") is None


def test_reader_latest(archive_dir: Path):
    reader = ArchiveReader(str(archive_dir))
    latest = reader.latest()
    assert latest is not None
    assert "Rust" in latest.question


def test_reader_empty_dir(tmp_path: Path):
    reader = ArchiveReader(str(tmp_path / "empty"))
    assert reader.list_entries() == []
    assert reader.latest() is None


# ── ArchiveSearch tests ────────────────────────────────────


def test_search_by_question(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("Rust")
    assert result.count > 0
    fields = {h.field for h in result.hits}
    assert "question" in fields


def test_search_by_verdict(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("performance-critical")
    assert result.count > 0
    assert any(h.field == "verdict" for h in result.hits)


def test_search_by_discussion_content(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("PostgreSQL")
    assert result.count > 0
    assert any(h.field == "discussion" for h in result.hits)


def test_search_by_summary(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("Adopt Rust")
    assert result.count > 0
    assert any(h.field == "summary" for h in result.hits)


def test_search_no_results(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("blockchain")
    assert result.count == 0


def test_search_max_results(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("migration", max_results=1)
    assert result.count <= 1


def test_search_case_insensitive(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("rust")
    assert result.count > 0


def test_snippet_contains_match(archive_dir: Path):
    search = ArchiveSearch(str(archive_dir))
    result = search.search("zero-cost")
    assert result.count > 0
    assert "zero-cost" in result.hits[0].snippet.lower()
