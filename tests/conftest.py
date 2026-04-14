"""Shared test fixtures."""

import pytest

from hexmind.models.config import DiscussionConfig


@pytest.fixture
def default_config() -> DiscussionConfig:
    return DiscussionConfig()
