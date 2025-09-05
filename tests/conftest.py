"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path

# Import fixtures from testing module to make them available globally
from ynab_io.testing import version_aware_parser


@pytest.fixture
def test_budget_path():
    """Path to the test budget fixture."""
    return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")