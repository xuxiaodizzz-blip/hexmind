"""Tests for the Knowledge Hub (Phase 4)."""

from __future__ import annotations

import asyncio
import json

import pytest

from hexmind.knowledge.base import (
    KnowledgeItem,
    KnowledgeSource,
    PlannedQuery,
    RateLimit,
    SourceFilters,
)
from hexmind.knowledge.citation import CitationManager
from hexmind.knowledge.hub import KnowledgeHub
from hexmind.knowledge.query_planner import KNOWLEDGE_HATS, QueryPlanner
from hexmind.models.hat import HatColor
from hexmind.models.persona import Persona


# ── Fixtures ───────────────────────────────────────────────


def _make_item(id: str, source: str = "test", title: str = "Paper", **kw) -> KnowledgeItem:
    return KnowledgeItem(id=id, source=source, title=title, **kw)


class FakeSource:
    """In-memory knowledge source for testing."""

    def __init__(
        self,
        source_id: str = "fake",
        items: list[KnowledgeItem] | None = None,
        rate_limit_val: RateLimit | None = None,
        delay: float = 0.0,
        fail: bool = False,
    ):
        self._source_id = source_id
        self._items = items or []
        self._rate_limit = rate_limit_val
        self._delay = delay
        self._fail = fail
        self.call_count = 0

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_name(self) -> str:
        return f"Fake ({self._source_id})"

    @property
    def rate_limit(self) -> RateLimit | None:
        return self._rate_limit

    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: SourceFilters | None = None,
    ) -> list[KnowledgeItem]:
        self.call_count += 1
        if self._fail:
            raise RuntimeError("Simulated failure")
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._items[:max_results]


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="test-eng",
        name="Test Engineer",
        domain="tech",
        description="A test persona",
    )


# ── CitationManager ───────────────────────────────────────


class TestCitationManager:
    def test_cite_assigns_sequential_numbers(self):
        cm = CitationManager()
        item1 = _make_item("a", title="Paper A")
        item2 = _make_item("b", title="Paper B")

        assert cm.cite(item1) == "[1]"
        assert cm.cite(item2) == "[2]"
        assert cm.count == 2

    def test_cite_deduplicates(self):
        cm = CitationManager()
        item = _make_item("a", title="Paper A")

        assert cm.cite(item) == "[1]"
        assert cm.cite(item) == "[1]"  # same item → same number
        assert cm.count == 1

    def test_render_bibliography(self):
        cm = CitationManager()
        cm.cite(_make_item("a", title="Paper A", authors=["Alice"], year=2024, url="https://example.com"))
        cm.cite(_make_item("b", title="Paper B", authors=["Bob", "Charlie"]))

        bib = cm.render_bibliography()
        assert "[1]" in bib
        assert "Paper A" in bib
        assert "Alice" in bib
        assert "(2024)" in bib
        assert "[2]" in bib
        assert "Paper B" in bib

    def test_render_bibliography_empty(self):
        cm = CitationManager()
        assert cm.render_bibliography() == ""

    def test_get_item(self):
        cm = CitationManager()
        item = _make_item("x", title="X")
        cm.cite(item)
        assert cm.get_item(1) is item
        assert cm.get_item(99) is None

    def test_all_items_ordered(self):
        cm = CitationManager()
        a = _make_item("a")
        b = _make_item("b")
        cm.cite(b)
        cm.cite(a)
        assert cm.all_items == [b, a]


# ── KnowledgeHub ──────────────────────────────────────────


class TestKnowledgeHub:
    @pytest.mark.asyncio
    async def test_search_single_source(self):
        hub = KnowledgeHub()
        items = [_make_item("1"), _make_item("2")]
        hub.register_source(FakeSource("s1", items=items))

        result = await hub.search("test query")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_multiple_sources(self):
        hub = KnowledgeHub()
        hub.register_source(FakeSource("s1", items=[_make_item("a", relevance_score=0.8)]))
        hub.register_source(FakeSource("s2", items=[_make_item("b", relevance_score=0.9)]))

        result = await hub.search("test")
        assert len(result) == 2
        # Sorted by relevance desc
        assert result[0].id == "b"
        assert result[1].id == "a"

    @pytest.mark.asyncio
    async def test_search_filters_by_source(self):
        hub = KnowledgeHub()
        s1 = FakeSource("s1", items=[_make_item("a")])
        s2 = FakeSource("s2", items=[_make_item("b")])
        hub.register_source(s1)
        hub.register_source(s2)

        result = await hub.search("test", sources=["s1"])
        assert len(result) == 1
        assert result[0].id == "a"
        assert s2.call_count == 0

    @pytest.mark.asyncio
    async def test_search_graceful_failure(self):
        """Failing source doesn't break the search."""
        hub = KnowledgeHub()
        hub.register_source(FakeSource("ok", items=[_make_item("x")]))
        hub.register_source(FakeSource("bad", fail=True))

        result = await hub.search("test")
        assert len(result) == 1
        assert result[0].id == "x"

    @pytest.mark.asyncio
    async def test_search_timeout(self):
        """Slow source times out gracefully."""
        hub = KnowledgeHub()
        hub.register_source(FakeSource("slow", items=[_make_item("x")], delay=20.0))
        hub.register_source(FakeSource("fast", items=[_make_item("y")]))

        result = await hub.search("test")
        # The slow source should timeout (15s), fast one returns
        assert any(i.id == "y" for i in result)

    @pytest.mark.asyncio
    async def test_search_multi_deduplicates(self):
        hub = KnowledgeHub()
        hub.register_source(FakeSource("s1", items=[_make_item("dup"), _make_item("unique1")]))

        queries = [
            PlannedQuery(query="q1", target_sources=["s1"]),
            PlannedQuery(query="q2", target_sources=["s1"]),
        ]
        result = await hub.search_multi(queries)
        # "dup" appears in both queries but should only appear once
        ids = [i.id for i in result]
        assert ids.count("dup") == 1

    def test_get_available_sources(self):
        hub = KnowledgeHub()
        hub.register_source(FakeSource("a"))
        hub.register_source(FakeSource("b"))
        assert sorted(hub.get_available_sources()) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_rate_limit_blocks(self):
        hub = KnowledgeHub()
        src = FakeSource(
            "limited",
            items=[_make_item("x")],
            rate_limit_val=RateLimit(max_per_window=1, window_seconds=60),
        )
        hub.register_source(src)

        r1 = await hub.search("q1")
        assert len(r1) == 1
        r2 = await hub.search("q2")
        assert len(r2) == 0  # rate limited


# ── QueryPlanner ──────────────────────────────────────────


class FakeLLM:
    """Minimal LLM stub for QueryPlanner tests."""

    def __init__(self, response_content: str = "[]"):
        self._content = response_content

    async def complete(self, system_prompt, user_prompt, **kwargs):
        from hexmind.models.llm import LLMResponse, TokenUsage

        return LLMResponse(
            content=self._content,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            model="test",
        )

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def count_messages_tokens(self, messages: list[dict[str, str]]) -> int:
        return sum(len(m.get("content", "")) for m in messages) // 4

    @property
    def context_limit(self) -> int:
        return 128000

    @property
    def model_name(self) -> str:
        return "test"

    @property
    def pricing(self):
        return None


class TestQueryPlanner:
    @pytest.mark.asyncio
    async def test_plan_queries_returns_list(self, sample_persona):
        planned = json.dumps([
            {"query": "PostgreSQL scalability", "target_sources": ["semantic_scholar"], "rationale": "test"}
        ])
        planner = QueryPlanner(FakeLLM(planned))

        result = await planner.plan_queries(
            question="Can PostgreSQL handle 1M concurrent?",
            hat=HatColor.WHITE,
            persona=sample_persona,
            context="",
            available_sources=["semantic_scholar"],
        )
        assert len(result) == 1
        assert result[0].query == "PostgreSQL scalability"

    @pytest.mark.asyncio
    async def test_red_hat_skips(self, sample_persona):
        planner = QueryPlanner(FakeLLM())

        result = await planner.plan_queries(
            question="test",
            hat=HatColor.RED,
            persona=sample_persona,
            context="",
            available_sources=["semantic_scholar"],
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self, sample_persona):
        """LLM failure triggers rule-based fallback."""
        planner = QueryPlanner(FakeLLM("not valid json!!!"))

        result = await planner.plan_queries(
            question="test question",
            hat=HatColor.WHITE,
            persona=sample_persona,
            context="",
            available_sources=["semantic_scholar", "arxiv"],
        )
        assert len(result) == 1
        assert result[0].query == "test question"

    def test_knowledge_hats_excludes_red(self):
        assert HatColor.RED not in KNOWLEDGE_HATS
        assert HatColor.WHITE in KNOWLEDGE_HATS
        assert HatColor.BLACK in KNOWLEDGE_HATS


# ── LocalFileSource ───────────────────────────────────────


class TestLocalFileSource:
    @pytest.mark.asyncio
    async def test_search_finds_matching_files(self, tmp_path):
        from hexmind.knowledge.sources.local_files import LocalFileSource

        (tmp_path / "readme.md").write_text("HexMind is great", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("Nothing here", encoding="utf-8")

        src = LocalFileSource(tmp_path)
        items = await src.search("HexMind")
        assert len(items) == 1
        assert "readme.md" in items[0].title

    @pytest.mark.asyncio
    async def test_search_empty_on_no_match(self, tmp_path):
        from hexmind.knowledge.sources.local_files import LocalFileSource

        (tmp_path / "file.md").write_text("nothing relevant", encoding="utf-8")
        src = LocalFileSource(tmp_path)
        items = await src.search("PostgreSQL")
        assert items == []


# ── ArchiveKnowledgeSource ────────────────────────────────


class TestArchiveKnowledgeSource:
    @pytest.mark.asyncio
    async def test_search_archive(self, tmp_path):
        from hexmind.knowledge.sources.archive_search import ArchiveKnowledgeSource

        # Create a fake archive entry
        entry_dir = tmp_path / "20260413-test"
        entry_dir.mkdir()
        (entry_dir / "meta.yaml").write_text(
            'question: "Should we use PostgreSQL?"\nstatus: converged\n',
            encoding="utf-8",
        )
        (entry_dir / "discussion.md").write_text("Discussion about PostgreSQL", encoding="utf-8")

        src = ArchiveKnowledgeSource(str(tmp_path))
        items = await src.search("PostgreSQL")
        assert len(items) >= 1
        assert "PostgreSQL" in items[0].title or "PostgreSQL" in items[0].snippet


# ── Persona knowledge_sources field ───────────────────────


class TestPersonaKnowledgeSources:
    def test_persona_with_knowledge_sources(self):
        p = Persona(
            id="test-doc",
            name="Doctor",
            domain="medical",
            description="A doctor",
            knowledge_sources=[
                {"source": "semantic_scholar", "auto_query": True, "max_results": 3},
            ],
        )
        assert len(p.knowledge_sources) == 1
        assert p.knowledge_sources[0].source == "semantic_scholar"
        assert p.knowledge_sources[0].auto_query is True

    def test_persona_without_knowledge_sources(self):
        p = Persona(
            id="test-eng",
            name="Engineer",
            domain="tech",
            description="An engineer",
        )
        assert p.knowledge_sources == []
