"""Tests for engine/token_accountant.py."""

from hexmind.engine.token_accountant import TokenAccountant
from hexmind.models.config import DiscussionConfig


class TestAvailableContext:
    def test_default_reserve(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        assert ta.available_context == 128000 - 2000

    def test_small_context(self):
        ta = TokenAccountant(context_limit=4000, config=DiscussionConfig())
        assert ta.available_context == 2000

    def test_tiny_context_clamped(self):
        ta = TokenAccountant(context_limit=1000, config=DiscussionConfig())
        assert ta.available_context == 0  # would be negative, clamped to 0


class TestCheckContextFit:
    def test_fits(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        result = ta.check_context_fit(system_tokens=500, user_tokens=1000)
        assert result.fits
        assert result.prompt_tokens == 1500
        assert result.headroom == ta.available_context - 1500
        assert not result.needs_compression

    def test_does_not_fit(self):
        ta = TokenAccountant(context_limit=4000, config=DiscussionConfig())
        result = ta.check_context_fit(system_tokens=1000, user_tokens=1500)
        # available = 2000, total = 2500
        assert not result.fits
        assert result.headroom < 0
        assert result.needs_compression


class TestNeedsCompression:
    def test_below_threshold(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        # available = 126000, threshold = 63000
        assert not ta.needs_compression(30000)

    def test_above_threshold(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        assert ta.needs_compression(70000)

    def test_exact_threshold(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        threshold = int(ta.available_context * 0.5)
        # At exactly the threshold → not triggered (need to exceed)
        assert not ta.needs_compression(threshold)
        assert ta.needs_compression(threshold + 1)


class TestEstimateRoundTokens:
    def test_single_persona(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        est = ta.estimate_round_tokens(1)
        assert est == 1600

    def test_five_personas(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        est = ta.estimate_round_tokens(5)
        assert est == 8000


class TestCompressionTarget:
    def test_target(self):
        ta = TokenAccountant(context_limit=128000, config=DiscussionConfig())
        target = ta.compression_target()
        assert target == ta.available_context // 3

    def test_target_minimum(self):
        ta = TokenAccountant(context_limit=2100, config=DiscussionConfig())
        # available = 100, target = 100//3 = 33, but min is 200
        assert ta.compression_target() == 200
