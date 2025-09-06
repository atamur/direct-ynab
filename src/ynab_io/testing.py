"""Testing utilities for YNAB parser, including version-aware test annotations.

This module provides:
- @budget_version decorator for specifying expected budget versions in tests
- version_aware_parser fixture for automatic parser restoration
- Validation utilities for budget version management

Example usage:
    @budget_version(67)
    def test_after_first_delta(version_aware_parser):
        parser = version_aware_parser
        assert len(parser.applied_deltas) == 1
"""

import functools
from pathlib import Path
from typing import Callable, Optional

import pytest

from .parser import YnabParser


def budget_version(version: int):
    """Decorator to specify which budget version a test expects.

    This decorator annotates test functions with version metadata that the
    version_aware_parser fixture uses to automatically restore the parser
    to the correct budget state.

    Args:
        version: The budget version number (0 = base state before any deltas,
                positive integers = state after specific deltas)

    Returns:
        Decorated test function with version metadata attached

    Raises:
        ValueError: If version is negative (invalid version number)

    Example:
        @budget_version(0)  # Test against base state
        def test_base_accounts(version_aware_parser):
            assert len(version_aware_parser.accounts) == 3

        @budget_version(67)  # Test against state after version 67 delta
        def test_after_first_delta(version_aware_parser):
            assert len(version_aware_parser.applied_deltas) == 1
    """
    _validate_version_number(version)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach version metadata to the wrapper function
        wrapper._budget_version = version
        return wrapper

    return decorator


def _validate_version_number(version: int) -> None:
    """Validate that version number is non-negative.

    Args:
        version: Version number to validate

    Raises:
        ValueError: If version is negative
    """
    if version < 0:
        raise ValueError("Budget version must be non-negative")


@pytest.fixture
def version_aware_parser(request):
    """Pytest fixture that provides a parser at the version specified by @budget_version.

    This fixture automatically detects if the test function has a @budget_version
    annotation and parses only up to that specific version, providing true version
    isolation. If no annotation is present, it provides the fully parsed state (latest version).

    Args:
        request: Pytest request object containing test context

    Returns:
        YnabParser: Parser instance parsed to the appropriate version

    Example:
        @budget_version(67)
        def test_specific_version(version_aware_parser):
            # Parser only parsed deltas up to version 67
            assert len(version_aware_parser.applied_deltas) == 1

        def test_latest_version(version_aware_parser):
            # Parser has all deltas applied (latest state)
            assert len(version_aware_parser.applied_deltas) == 26
    """
    test_budget_path = request.getfixturevalue("test_budget_path")

    # Create parser
    parser = YnabParser(test_budget_path)

    # Check for version annotation
    target_version = _get_test_version_annotation(request.node.function)
    if target_version is not None:
        # Use version-aware parsing - only parse up to target version
        parser.parse_up_to_version(target_version)
    else:
        # No version annotation - parse all deltas as before
        parser.parse()

    return parser


def _get_test_version_annotation(test_function: Callable) -> Optional[int]:
    """Extract version annotation from test function if present.

    Args:
        test_function: Test function to check for version annotation

    Returns:
        Version number if annotation present, None otherwise
    """
    return getattr(test_function, "_budget_version", None)


def validate_budget_version(version: int, budget_path: Path) -> bool:
    """Validate that a version number exists in the budget's delta sequence.

    Args:
        version: Version number to validate
        budget_path: Path to budget directory

    Returns:
        True if version exists, False otherwise
    """
    try:
        parser = YnabParser(budget_path)
        available_versions = parser.get_available_versions()
        return version in available_versions
    except Exception:
        return False
