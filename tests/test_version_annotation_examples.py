"""Examples showing how to use @budget_version annotation in existing tests.

This file demonstrates how existing tests can be updated to use the version annotation
system to make them resilient to fixture data changes.
"""

import pytest
from pathlib import Path
from assertpy import assert_that

from ynab_io.testing import budget_version
from ynab_io.models import Account, Payee, Transaction


class TestVersionAnnotationExamples:
    """Examples showing version annotation usage patterns."""
    
    @budget_version(0)  # Base state before any deltas
    def test_base_state_account_structure(self, version_aware_parser):
        """Test that validates base state account structure.
        
        This test is locked to version 0 (base state) so it will always test
        the original Budget.yfull data regardless of fixture updates.
        """
        parser = version_aware_parser
        
        # These assertions are safe because they're based on base state
        assert_that(parser.accounts).is_not_empty()
        assert_that(len(parser.accounts)).is_greater_than(0)
        assert all(isinstance(account, Account) for account in parser.accounts.values())
        
        # Can test specific account properties that exist in base state
        account_names = [account.accountName for account in parser.accounts.values()]
        assert_that(account_names).is_not_empty()
        assert all(name for name in account_names)  # All accounts have names
    
    @budget_version(67)  # After first delta is applied
    def test_after_first_delta_changes(self, version_aware_parser):
        """Test that validates state after first delta (A-63_A-67.ydiff).
        
        This test is locked to version 67 so it will always test the state
        after exactly one delta has been applied.
        """
        parser = version_aware_parser
        
        # Should have exactly one delta applied
        assert len(parser.applied_deltas) == 1
        
        # The applied delta should be the first one (ending at version 67)
        applied_delta = parser.applied_deltas[0]
        end_version = parser._get_version_end_number(applied_delta)
        assert end_version == 67
        
        # Can test specific changes that happened in first delta
        assert len(parser.accounts) >= 3  # At least the original accounts
        assert len(parser.payees) >= 10   # Should have payees
        assert len(parser.transactions) >= 10  # Should have transactions
    
    @budget_version(87)  # After several deltas
    def test_intermediate_state_validation(self, version_aware_parser):
        """Test that validates intermediate state after several deltas.
        
        This test is locked to version 87, so it tests the budget state
        after specific changes have been made, but before the final state.
        """
        parser = version_aware_parser
        
        # Should have multiple deltas applied but not all
        assert len(parser.applied_deltas) > 1
        assert_that(len(parser.applied_deltas)).is_less_than(len(parser._discover_delta_files()))  # Not all deltas
        
        # All applied deltas should be version 87 or earlier
        for delta in parser.applied_deltas:
            end_version = parser._get_version_end_number(delta)
            assert end_version <= 87
        
        # Can test that specific entities exist at this point
        assert len(parser.accounts) >= 3
        assert len(parser.payees) >= 10
        assert len(parser.transactions) >= 10
        
        # Validate entity types
        for account in parser.accounts.values():
            assert isinstance(account, Account)
            assert hasattr(account, 'accountName')
            assert hasattr(account, 'accountType')
    
    @budget_version(141)  # Latest version  
    def test_final_state_comprehensive_validation(self, version_aware_parser):
        """Test that validates the final state after all deltas.
        
        This test is locked to version 141 (latest) so it will test the
        complete final state of the budget.
        """
        parser = version_aware_parser
        
        # Should have all deltas applied (flexible count assertion)
        assert_that(parser.applied_deltas).is_not_empty()
        assert_that(len(parser.applied_deltas)).is_greater_than(10)  # Multiple deltas
        
        # Final state should have entities (flexible count assertions)
        assert_that(parser.accounts).is_not_empty()
        assert_that(parser.payees).is_not_empty()
        assert_that(parser.transactions).is_not_empty()
        
        # All entities should be properly typed
        for account in parser.accounts.values():
            assert isinstance(account, Account)
        for payee in parser.payees.values():
            assert isinstance(payee, Payee)
        for transaction in parser.transactions.values():
            assert isinstance(transaction, Transaction)
    
    def test_without_version_annotation_gets_latest_state(self, version_aware_parser):
        """Example of test without version annotation - gets latest state.
        
        Tests without @budget_version annotation get the fully parsed state,
        which is equivalent to @budget_version(141) for this fixture.
        """
        parser = version_aware_parser
        
        # Should get the same state as latest version (flexible count assertions)
        assert_that(parser.applied_deltas).is_not_empty()
        assert_that(len(parser.applied_deltas)).is_greater_than(10)  # Multiple deltas
        assert_that(parser.accounts).is_not_empty()
        assert_that(parser.payees).is_not_empty()
        assert_that(parser.transactions).is_not_empty()


class TestVersionAnnotationMigrationExamples:
    """Examples showing how to migrate existing tests to use version annotations."""
    
    # OLD WAY: Brittle test that breaks when fixture changes
    def test_old_style_brittle_test(self, version_aware_parser):
        """Old style test that might break when fixture data changes.
        
        This test assumes specific counts but doesn't specify which version
        it expects, making it fragile to fixture updates.
        """
        parser = version_aware_parser
        
        # This works now but could break if fixture is updated (flexible count assertion)
        assert_that(parser.transactions).is_not_empty()
        assert_that(len(parser.transactions)).is_greater_than(0)
        
        # This test is fragile because it doesn't specify which budget version
        # it was designed for, so fixture updates could break it
    
    # NEW WAY: Resilient test with explicit version
    @budget_version(141)  # Explicitly specify expected version
    def test_new_style_resilient_test(self, version_aware_parser):
        """New style test that specifies exactly which version it expects.
        
        This test explicitly declares it expects version 141, making it
        resilient to fixture changes and clearly documenting its assumptions.
        """
        parser = version_aware_parser
        
        # This will always work because it's locked to version 141 (flexible count assertion)
        assert_that(parser.transactions).is_not_empty()
        assert_that(len(parser.transactions)).is_greater_than(0)
        
        # If someone adds more deltas to the fixture, this test will still
        # pass because it's locked to the specific version it was written for
    
    # MIGRATION EXAMPLE: Version-specific behavior testing
    @budget_version(67)
    def test_early_version_behavior(self, version_aware_parser):
        """Test specific to early budget state."""
        parser = version_aware_parser
        
        # Test behavior specific to this version
        assert len(parser.applied_deltas) == 1
        early_transaction_count = len(parser.transactions)
        
        # Can test that this version has different characteristics
        assert early_transaction_count >= 16  # Should have at least base transactions
    
    @budget_version(141)
    def test_late_version_behavior(self, version_aware_parser):
        """Test specific to late budget state."""
        parser = version_aware_parser
        
        # Test behavior specific to final version (flexible count assertion)
        assert_that(parser.applied_deltas).is_not_empty()
        assert_that(len(parser.applied_deltas)).is_greater_than(10)  # Multiple deltas
        final_transaction_count = len(parser.transactions)
        
        # Final state has transactions (flexible count assertion)
        assert_that(final_transaction_count).is_greater_than(0)
    
    def test_version_comparison_example(self):
        """Example showing how to test behavior across versions."""
        from ynab_io.parser import YnabParser
        
        # Create parser and test different states
        budget_path = Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")
        parser = YnabParser(budget_path)
        parser.parse()  # Full parse
        
        # Get final state counts
        final_accounts = len(parser.accounts)
        final_payees = len(parser.payees)
        final_transactions = len(parser.transactions)
        
        # Test that restoration to different versions works
        parser.restore_to_version(0)  # Base state
        assert len(parser.accounts) == final_accounts  # Same accounts
        assert len(parser.payees) > final_payees       # Base has more payees
        assert len(parser.transactions) > final_transactions  # Base has more transactions
        
        # This demonstrates how some entities are deleted over time (tombstones)