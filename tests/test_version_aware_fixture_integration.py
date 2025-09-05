"""Integration tests for version-aware parser fixture in real test scenarios."""

import pytest
from pathlib import Path

from ynab_io.testing import budget_version


class TestVersionAwareFixtureIntegration:
    """Test version-aware fixture integration with real parser instances."""
    
    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")
    
    @budget_version(0)
    def test_base_version_has_correct_entity_counts(self, version_aware_parser):
        """Test that @budget_version(0) provides parser at base state."""
        parser = version_aware_parser
        
        # Should have base state counts (before any deltas applied)
        assert len(parser.accounts) == 3
        assert len(parser.payees) == 14  # Base state has more payees than final
        assert len(parser.transactions) == 17  # Base state has more transactions
        
        # Should have no deltas applied
        assert len(parser.applied_deltas) == 0
    
    @budget_version(67)
    def test_specific_version_has_expected_state(self, version_aware_parser):
        """Test that @budget_version(67) provides parser at version 67."""
        parser = version_aware_parser
        
        # Should have applied some but not all deltas
        assert len(parser.applied_deltas) > 0
        assert len(parser.applied_deltas) < 26  # Not all 26 deltas
        
        # All applied deltas should be up to version 67
        for applied_delta in parser.applied_deltas:
            end_version = parser._get_version_end_number(applied_delta)
            assert end_version <= 67
    
    @budget_version(141)  # Latest version
    def test_latest_version_has_all_deltas_applied(self, version_aware_parser):
        """Test that @budget_version(141) provides fully parsed state."""
        parser = version_aware_parser
        
        # Should have all 26 deltas applied
        assert len(parser.applied_deltas) == 26
        
        # Should have final state counts
        assert len(parser.accounts) == 3
        assert len(parser.payees) == 13
        assert len(parser.transactions) == 16
    
    def test_undecorated_test_gets_full_parser_state(self, version_aware_parser):
        """Test that tests without @budget_version get fully parsed state."""
        parser = version_aware_parser
        
        # Should have all deltas applied (same as latest version)
        assert len(parser.applied_deltas) == 26
        assert len(parser.accounts) == 3
        assert len(parser.payees) == 13
        assert len(parser.transactions) == 16
    
    @budget_version(87)
    def test_intermediate_version_has_partial_state(self, version_aware_parser):
        """Test that intermediate version has expected partial state."""
        parser = version_aware_parser
        
        # Should have applied deltas up to version 87
        applied_versions = [parser._get_version_end_number(delta) for delta in parser.applied_deltas]
        assert max(applied_versions) <= 87
        assert len(parser.applied_deltas) > 1  # More than just first delta
        assert len(parser.applied_deltas) < 26  # But not all deltas
        
        # Should have some entities
        assert len(parser.accounts) >= 3
        assert len(parser.payees) >= 10
        assert len(parser.transactions) >= 10


class TestVersionAwareFixtureRobustness:
    """Test robustness and error handling of version-aware fixture."""
    
    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")
    
    def test_fixture_handles_missing_version_gracefully(self, version_aware_parser):
        """Test that fixture works when test has no @budget_version annotation."""
        parser = version_aware_parser
        
        # Should still get a working parser (fully parsed)
        assert parser is not None
        assert len(parser.accounts) > 0
        assert len(parser.payees) > 0
        assert len(parser.transactions) > 0
    
    @budget_version(67)
    def test_fixture_restores_correctly_multiple_times(self, version_aware_parser):
        """Test that fixture provides consistent state across multiple uses."""
        parser1 = version_aware_parser
        initial_transaction_count = len(parser1.transactions)
        initial_delta_count = len(parser1.applied_deltas)
        
        # Parser state should be consistent
        assert len(parser1.applied_deltas) == initial_delta_count
        assert len(parser1.transactions) == initial_transaction_count
        
        # All applied deltas should be version 67 or earlier
        for delta in parser1.applied_deltas:
            assert parser1._get_version_end_number(delta) <= 67
    
    @budget_version(0)
    def test_base_version_fixture_is_idempotent(self, version_aware_parser):
        """Test that base version fixture consistently provides base state."""
        parser = version_aware_parser
        
        # Should always be base state
        assert len(parser.applied_deltas) == 0
        assert len(parser.accounts) == 3
        assert len(parser.payees) == 14
        assert len(parser.transactions) == 17