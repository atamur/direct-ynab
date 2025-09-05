"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from assertpy import assert_that

# Import fixtures from testing module to make them available globally
from ynab_io.testing import version_aware_parser


@pytest.fixture
def test_budget_path():
    """Path to the test budget fixture."""
    return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")


def assert_parser_collections_populated(parser):
    """Shared helper to verify parser has populated collections.
    
    Replaces repetitive is_not_empty() assertions across test files.
    """
    assert_that(parser.accounts).is_not_empty()
    assert_that(parser.payees).is_not_empty()
    assert_that(parser.transactions).is_not_empty()


def assert_parser_collections_exist(parser):
    """Shared helper to verify parser has core collection attributes.
    
    Used for testing parser state without requiring populated data.
    """
    assert_that(parser.accounts).is_not_none()
    assert_that(parser.payees).is_not_none()
    assert_that(parser.transactions).is_not_none()
    assert_that(parser.master_categories).is_not_none()
    assert_that(parser.categories).is_not_none()
    assert_that(parser.monthly_budgets).is_not_none()