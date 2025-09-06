"""Tests for the @budget_version annotation system."""

from pathlib import Path

import pytest

from ynab_io.testing import budget_version


class TestBudgetVersionDecorator:
    """Test cases for the @budget_version decorator functionality."""

    def test_budget_version_decorator_exists(self):
        """Test that budget_version decorator can be imported."""
        # This should pass after we implement the decorator
        assert callable(budget_version)

    def test_budget_version_decorator_stores_version_metadata(self):
        """Test that @budget_version decorator stores version metadata on test functions."""

        @budget_version(67)
        def dummy_test():
            pass

        # Should store version info as metadata on the function
        assert hasattr(dummy_test, "_budget_version")
        assert dummy_test._budget_version == 67

    def test_budget_version_decorator_with_invalid_version_raises_error(self):
        """Test that @budget_version raises error for invalid version numbers."""

        # Negative versions should raise error
        with pytest.raises(ValueError, match="Budget version must be non-negative"):

            @budget_version(-1)
            def dummy_test():
                pass

    def test_budget_version_decorator_preserves_function_metadata(self):
        """Test that @budget_version preserves original function metadata."""

        @budget_version(71)
        def test_with_docstring():
            """This is a test function."""
            pass

        # Should preserve function name and docstring
        assert test_with_docstring.__name__ == "test_with_docstring"
        assert test_with_docstring.__doc__ == """This is a test function."""
        assert test_with_docstring._budget_version == 71

    def test_budget_version_decorator_works_with_test_methods(self):
        """Test that @budget_version works on test methods within classes."""

        class DummyTestClass:
            @budget_version(84)
            def test_method(self):
                """A test method."""
                pass

        test_instance = DummyTestClass()
        # Should store version metadata on the method
        assert hasattr(test_instance.test_method, "_budget_version")
        assert test_instance.test_method._budget_version == 84


class TestBudgetVersionIntegration:
    """Test cases for integration with pytest and parser fixtures."""

    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

    def test_version_aware_parser_fixture_exists(self):
        """Test that version_aware_parser fixture can be imported and used."""
        from ynab_io.testing import version_aware_parser

        # Should be a callable fixture
        assert callable(version_aware_parser)

    def test_fixture_can_be_used_in_real_test(self):
        """Test that fixture can actually be used in a real test context."""
        # This is more of a documentation test showing how it should work
        from ynab_io.testing import budget_version

        @budget_version(67)
        def example_test(version_aware_parser):
            # This would work in a real test context
            assert hasattr(example_test, "_budget_version")
            assert example_test._budget_version == 67

        # Verify the annotation worked
        assert example_test._budget_version == 67


class TestVersionAnnotationUsageExamples:
    """Examples demonstrating how @budget_version should work in practice."""

    def test_example_test_at_base_version(self):
        """Example test that should run at base state (version 0)."""

        @budget_version(0)
        def test_base_state_has_correct_counts(version_aware_parser):
            parser = version_aware_parser
            # This test expects base state data
            assert len(parser.accounts) == 3
            assert len(parser.payees) == 14
            assert len(parser.transactions) == 17

        # Should have version metadata
        assert test_base_state_has_correct_counts._budget_version == 0

    def test_example_test_at_specific_delta_version(self):
        """Example test that should run at specific delta version."""

        @budget_version(87)
        def test_after_specific_changes(version_aware_parser):
            parser = version_aware_parser
            # This test expects state after version 87 deltas
            # (exact counts would depend on what changes happened)
            assert len(parser.accounts) >= 3
            assert len(parser.payees) >= 10

        # Should have version metadata
        assert test_after_specific_changes._budget_version == 87

    def test_decorator_validates_available_versions(self):
        """Test that decorator can validate version exists in fixture data."""
        from ynab_io.testing import validate_budget_version

        # Should validate against available versions
        test_budget_path = Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

        # Valid versions should pass
        assert validate_budget_version(0, test_budget_path) is True
        assert validate_budget_version(67, test_budget_path) is True
        assert validate_budget_version(141, test_budget_path) is True

        # Invalid version should fail
        assert validate_budget_version(999, test_budget_path) is False
