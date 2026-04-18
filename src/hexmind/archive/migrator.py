"""Migrator: import JSON file archives into the database."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hexmind.archive.db_models import (
    DiscussionDB,
    DiscussionTagDB,
    PanelistOutputDB,
    RoundDB,
    TreeNodeDB,
)
from hexmind.archive.reader import ArchiveEntry, ArchiveReader

logger = logging.getLogger(__name__)


class ArchiveMigrator:
    """Migrate local JSON/YAML archive directories into the database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def migrate_all(self, archive_dir: str = "discussion_archive") -> int:
        """Migrate all entries from archive_dir. Returns count of migrated discussions."""
        reader = ArchiveReader(archive_dir)
        entries = reader.list_entries()
        migrated = 0
        for entry in entries:
            try:
                result = await self._migrate_entry(entry)
                if result:  # empty string means skipped (already migrated)
                    migrated += 1
                    logger.info("Migrated: %s", entry.dir_name)
            except Exception:
                logger.exception("Failed to migrate: %s", entry.dir_name)
        return migrated

    async def _migrate_entry(self, entry: ArchiveEntry) -> str:
        async with self._session_factory() as session:
            source_tag = self._archive_source_tag(entry.dir_name)
            # Idempotency should be based on archive source identity, not content similarity.
            existing = await session.execute(
                select(DiscussionTagDB.discussion_id)
                .where(DiscussionTagDB.tag == source_tag)
                .limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("Already migrated, skipping: %s", entry.dir_name)
                return ""

            # 1. Create discussion
            meta = entry.meta
            disc = DiscussionDB(
                question=entry.question,
                status=entry.status,
                config={
                    "request_config_snapshot": entry.meta.get("request_config_snapshot", {}),
                    "runtime_config_snapshot": entry.meta.get("runtime_config_snapshot", {}),
                    "migration_metadata": {
                        "archive_source_dir": entry.dir_name,
                    },
                },
                confidence=entry.confidence or None,
                discussion_locale="zh",
                model_used=meta.get("model_used"),
            )
            if entry.verdict:
                disc.verdict = {"summary": entry.verdict}
            session.add(disc)
            await session.flush()

            # 2. Create root tree node
            root = TreeNodeDB(
                discussion_id=disc.id,
                question=entry.question,
                depth=0,
                status=entry.status,
            )
            if entry.verdict:
                root.verdict = {"summary": entry.verdict}
            session.add(root)
            await session.flush()

            # 3. Parse decision_summary.json for structured data
            summary = entry.summary
            if summary:
                summary_data = summary.model_dump()
                # Merge with existing verdict — don't overwrite basic fields
                if disc.verdict:
                    merged = {**disc.verdict, **summary_data}
                else:
                    merged = summary_data
                disc.verdict = merged

            # 4. Parse events from discussion.md to reconstruct rounds
            await self._reconstruct_rounds(session, entry, root.id)

            # 5. Add persona tags
            session.add(DiscussionTagDB(discussion_id=disc.id, tag=source_tag))
            for persona_id in entry.personas:
                session.add(
                    DiscussionTagDB(discussion_id=disc.id, tag=f"persona:{persona_id}")
                )

            await session.commit()
            return disc.id

    def _archive_source_tag(self, dir_name: str) -> str:
        digest = hashlib.sha1(dir_name.encode("utf-8")).hexdigest()[:16]
        return f"archive-src:{digest}"

    async def _reconstruct_rounds(
        self, session: AsyncSession, entry: ArchiveEntry, tree_node_id: str
    ) -> None:
        """Best-effort round reconstruction from the discussion markdown."""
        md = entry.discussion_md
        if not md:
            return

        round_num = 0
        current_hat = "white"
        current_reasoning = ""

        for line in md.split("\n"):
            stripped = line.strip()
            if stripped.startswith("## Round "):
                round_num += 1
                # Parse hat from "## Round N — Color Hat"
                parts = stripped.split("—")
                if len(parts) > 1:
                    hat_part = parts[1].strip().lower().replace(" hat", "")
                    if hat_part in ("white", "red", "black", "yellow", "green"):
                        current_hat = hat_part
            elif stripped.startswith("*Blue Hat:") and stripped.endswith("*"):
                current_reasoning = stripped[10:-1].strip()
                rnd = RoundDB(
                    tree_node_id=tree_node_id,
                    round_number=round_num,
                    hat=current_hat,
                    blue_hat_reasoning=current_reasoning,
                )
                session.add(rnd)
                await session.flush()
