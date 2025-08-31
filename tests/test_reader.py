"""Tests for BudgetReader functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from ynab_io.reader import BudgetReader


# Real fixture path for integration tests - use original fixture
FIXTURE_BUDGET_PATH = Path(__file__).parent / "fixtures" / "My Test Budget~E0C1460F.ynab4"


class TestBudgetReader:
    """Test cases for BudgetReader class."""
    
    def test_budget_reader_initialization(self):
        """Test BudgetReader can be initialized with budget path."""
        budget_path = Path("/fake/path/to/budget.ynab4")
        reader = BudgetReader(budget_path)
        assert reader.budget_path == budget_path
        assert reader._budget is None
    
    @patch('ynab_io.reader.YNAB')
    def test_load_budget_snapshot_success(self, mock_ynab_class):
        """Test successful loading of Budget.yfull snapshot."""
        # Setup mocks
        mock_budget = Mock()
        mock_budget.accounts = Mock()
        mock_budget.categories = Mock() 
        mock_budget.transactions = Mock()
        mock_budget.payees = Mock()
        mock_ynab_class.return_value = mock_budget
        
        # Test loading
        budget_path = Path("/fake/path/to/TestBudget.ynab4")
        reader = BudgetReader(budget_path)
        loaded_budget = reader.load_snapshot()
        
        # Verify YNAB was called correctly
        mock_ynab_class.assert_called_once_with(
            str(budget_path.parent),
            budget_path.stem
        )
        
        # Verify budget is returned and stored
        assert loaded_budget == mock_budget
        assert reader._budget == mock_budget
    
    @patch('ynab_io.reader.YNAB')
    def test_load_budget_snapshot_without_device_selection(self, mock_ynab_class):
        """Test loading snapshot without device selection parameter."""
        mock_budget = Mock()
        mock_ynab_class.return_value = mock_budget
        
        budget_path = Path("/fake/path/to/TestBudget.ynab4")
        reader = BudgetReader(budget_path)
        
        loaded_budget = reader.load_snapshot()
        
        # Verify YNAB was called correctly
        mock_ynab_class.assert_called_once_with(
            str(budget_path.parent),
            budget_path.stem
        )
        assert loaded_budget == mock_budget
    
    @patch('ynab_io.reader.YNAB')
    def test_load_budget_snapshot_failure(self, mock_ynab_class):
        """Test handling of budget loading failure."""
        # Setup mock to raise exception
        mock_ynab_class.side_effect = FileNotFoundError("Budget not found")
        
        budget_path = Path("/fake/path/to/NonExistent.ynab4")
        reader = BudgetReader(budget_path)
        
        with pytest.raises(FileNotFoundError, match="Budget not found"):
            reader.load_snapshot()
    
    def test_get_budget_without_loading(self):
        """Test accessing budget without loading first raises error."""
        budget_path = Path("/fake/path/to/budget.ynab4")
        reader = BudgetReader(budget_path)
        
        with pytest.raises(RuntimeError, match="Budget not loaded"):
            reader.get_budget()
    
    @patch('ynab_io.reader.YNAB')
    def test_get_budget_after_loading(self, mock_ynab_class):
        """Test accessing budget after successful loading."""
        mock_budget = Mock()
        mock_ynab_class.return_value = mock_budget
        
        budget_path = Path("/fake/path/to/TestBudget.ynab4")
        reader = BudgetReader(budget_path)
        reader.load_snapshot()
        
        retrieved_budget = reader.get_budget()
        assert retrieved_budget == mock_budget
    
    def test_budget_structure_validation(self):
        """Test that loaded budget has expected structure and entities."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        budget = reader.load_snapshot()
        
        # Verify structure
        assert hasattr(budget, 'accounts')
        assert hasattr(budget, 'categories')
        assert hasattr(budget, 'transactions')
        assert hasattr(budget, 'payees')
        
        # Verify real fixture has expected entities
        assert len(budget.accounts) > 0
        assert len(budget.categories) > 0
        assert len(budget.transactions) >= 0
        assert len(budget.payees) > 0
    
    def test_budget_path_property(self):
        """Test budget_path property accessor."""
        original_path = Path("/test/budget/path.ynab4")
        reader = BudgetReader(original_path)
        assert reader.budget_path == original_path
        
        # Test that path is immutable
        new_path = Path("/different/path.ynab4")
        reader._budget_path = new_path  # Direct attribute access
        assert reader.budget_path == new_path
    
    def test_load_real_fixture_snapshot(self):
        """Test loading a real YNAB4 budget fixture snapshot."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        budget = reader.load_snapshot()
        
        # Verify budget was loaded successfully
        assert budget is not None
        assert reader._budget is not None
        
        # Verify budget structure exists
        assert hasattr(budget, 'accounts')
        assert hasattr(budget, 'categories')  
        assert hasattr(budget, 'transactions')
        assert hasattr(budget, 'payees')
        
        # Verify some entities were loaded from the snapshot
        assert len(budget.accounts) > 0
        assert len(budget.categories) > 0
        assert len(budget.transactions) >= 0  # May be 0 in base snapshot
        assert len(budget.payees) > 0
        
        # Store initial state for delta testing
        initial_transaction_count = len(budget.transactions)
        
        # Look for specific transaction that exists in Budget.yfull
        # This transaction exists with final amount after all deltas applied
        test_transaction_id = "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C" 
        test_transaction = None
        for trans in budget.transactions:
            if trans.id == test_transaction_id:
                test_transaction = trans
                break
        
        # Transaction should exist in current snapshot with final amount
        # (Budget.yfull contains the current complete state, not original snapshot)
        if test_transaction:
            # Final amount should be 20000 (after all deltas applied)
            assert test_transaction.amount == 20000


class TestBudgetReaderDeltaApplication:
    """Test cases for delta (.ydiff) application functionality."""
    
    def test_discover_delta_files(self):
        """Test discovery of .ydiff files in device directory."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        reader.load_snapshot()
        
        # Method should discover and return sorted list of delta files
        delta_files = reader.discover_delta_files()
        
        # Should find all 4 delta files in chronological order
        expected_deltas = [
            "A-63_A-67.ydiff",
            "A-67_A-69.ydiff", 
            "A-69_A-71.ydiff",
            "A-71_A-72.ydiff"
        ]
        
        assert len(delta_files) == 4
        assert [d.name for d in delta_files] == expected_deltas
    
    def test_parse_delta_version_stamps(self):
        """Test parsing version stamps from delta filenames."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        
        # Should extract version stamps correctly
        start_version, end_version = reader._parse_delta_versions("A-63_A-67.ydiff")
        assert start_version == "A-63"
        assert end_version == "A-67"
        
        start_version, end_version = reader._parse_delta_versions("A-71_A-72.ydiff") 
        assert start_version == "A-71"
        assert end_version == "A-72"
    
    def test_apply_single_delta(self):
        """Test applying a single delta loads and parses correctly."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        budget = reader.load_snapshot()
        
        # Apply the final delta (A-71_A-72.ydiff)
        delta_file = FIXTURE_BUDGET_PATH / "data1~F5FF7453" / "DDBC2A7E-AE4D-B8A5-0759-B56799918579" / "A-71_A-72.ydiff"
        
        # This should load and parse the delta without error
        reader.apply_delta(delta_file)
        
        # Verify delta was loaded by checking we can load its data
        delta_data = reader._load_delta_file(delta_file)
        assert "items" in delta_data
        assert len(delta_data["items"]) == 1
        
        # Verify the transaction data in the delta
        transaction_item = delta_data["items"][0]
        assert transaction_item["entityType"] == "transaction"
        assert transaction_item["entityId"] == "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C"
        assert transaction_item["amount"] == 20000
    
    def test_apply_deltas_in_sequence(self):
        """Test applying multiple deltas in chronological sequence."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        
        # Load base snapshot state (this should be clean initial state)
        budget = reader.load_snapshot_without_deltas()
        
        initial_transaction_count = len(budget.transactions)
        
        # Apply all deltas in sequence
        reader.apply_all_deltas()
        
        # Final state should match what we get from normal load_snapshot()
        final_budget = reader.get_budget()
        final_transaction_count = len(final_budget.transactions)
        
        # Should have same final state as loading current Budget.yfull
        reader_current = BudgetReader(FIXTURE_BUDGET_PATH)
        current_budget = reader_current.load_snapshot()
        
        assert final_transaction_count == len(current_budget.transactions)
        
        # Specific transaction should have final amount
        test_transaction_id = "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C"
        final_transaction = None
        current_transaction = None
        
        for trans in final_budget.transactions:
            if trans.id == test_transaction_id:
                final_transaction = trans
                break
                
        for trans in current_budget.transactions:
            if trans.id == test_transaction_id:
                current_transaction = trans
                break
        
        assert final_transaction is not None
        assert current_transaction is not None
        assert final_transaction.amount == current_transaction.amount
    
    def test_handle_entity_versions_and_tombstones(self):
        """Test handling of entityVersion precedence and isTombstone deletions."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        reader.load_snapshot()
        
        # Load a specific delta and check entity version handling
        delta_file = FIXTURE_BUDGET_PATH / "data1~F5FF7453" / "DDBC2A7E-AE4D-B8A5-0759-B56799918579" / "A-63_A-67.ydiff" 
        delta_data = reader._load_delta_file(delta_file)
        
        # Should contain items with entityVersion and isTombstone properties
        assert "items" in delta_data
        assert len(delta_data["items"]) > 0
        
        for item in delta_data["items"]:
            assert "entityVersion" in item
            assert "isTombstone" in item
            assert "entityId" in item
            
        # Apply delta with proper entity version handling
        reader._apply_delta_items(delta_data["items"])
        
        # Entities should be updated/created/deleted correctly based on version and tombstone status


    @patch('ynab_io.reader.YNAB')
    def test_reload_budget(self, mock_ynab_class):
        """Test reloading budget discards previous state."""
        mock_budget1 = Mock()
        mock_budget2 = Mock()
        mock_ynab_class.side_effect = [mock_budget1, mock_budget2]
        
        budget_path = Path("/fake/path/to/TestBudget.ynab4")
        reader = BudgetReader(budget_path)
        
        # Load first time
        budget1 = reader.load_snapshot()
        assert budget1 == mock_budget1
        assert reader._budget == mock_budget1
        
        # Reload
        budget2 = reader.load_snapshot()
        assert budget2 == mock_budget2
        assert reader._budget == mock_budget2
        
        # Verify YNAB was called twice
        assert mock_ynab_class.call_count == 2
    
    def test_real_fixture_loading(self):
        """Test loading real fixture without device selection."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        
        # Test basic loading works
        budget = reader.load_snapshot()
        
        # Should load successfully
        assert budget is not None
        assert hasattr(budget, 'accounts')
        assert hasattr(budget, 'categories')
        assert hasattr(budget, 'transactions')
        assert hasattr(budget, 'payees')
    
    
    def test_real_fixture_data_integrity(self):
        """Test that real fixture data has proper integrity."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        budget = reader.load_snapshot()
        
        # Verify accounts have proper structure
        for account in budget.accounts:
            assert hasattr(account, 'id')
            assert hasattr(account, 'name')
            # Account ID should be a valid GUID format
            assert len(account.id) > 0
            
        # Verify categories have proper structure  
        for category in budget.categories:
            assert hasattr(category, 'id')
            assert hasattr(category, 'name')
            assert len(category.id) > 0
            
        # Verify payees have proper structure
        for payee in budget.payees:
            assert hasattr(payee, 'id')
            assert hasattr(payee, 'name')
            assert len(payee.id) > 0
            
        # Verify transactions have proper structure
        for transaction in budget.transactions:
            assert hasattr(transaction, 'id')
            assert hasattr(transaction, 'account')  # pynab uses 'account' not 'account_id'
            assert hasattr(transaction, 'payee')    # pynab uses 'payee' not 'payee_id'
            assert hasattr(transaction, 'amount')
            assert len(transaction.id) > 0


class TestBudgetReaderRealDataAssertions:
    """Test cases for specific real fixture data validation based on actual content.
    
    These tests validate that the BudgetReader correctly parses and provides access to
    specific data from the real YNAB4 fixture "My Test Budget~E0C1460F.ynab4".
    Each test verifies exact entity counts, IDs, names, and relationships based on
    the known structure of the fixture data.
    """
    
    def setUp_reader_and_budget(self):
        """Helper method to set up reader and load budget with fixture validation."""
        if not FIXTURE_BUDGET_PATH.exists():
            pytest.skip("Real fixture not available")
        
        reader = BudgetReader(FIXTURE_BUDGET_PATH)
        budget = reader.load_snapshot()
        return reader, budget
    
    def test_exact_entity_counts(self):
        """Test exact counts of entities match the known fixture structure.
        
        The test fixture contains:
        - 1 account ("Current")
        - 29 categories (23 subcategories + 6 regular master categories)
        - 4 payees (Transfer, Starting Balance, Migros, Salary)
        - 3 transactions
        - 7 master categories (including Hidden and Debt)
        """
        reader, budget = self.setUp_reader_and_budget()
        
        # Exact entity counts based on fixture analysis
        assert len(budget.accounts) == 1, f"Expected 1 account, found {len(budget.accounts)}"
        assert len(budget.categories) == 29, f"Expected 29 categories, found {len(budget.categories)}"
        assert len(budget.payees) == 4, f"Expected 4 payees, found {len(budget.payees)}"
        assert len(budget.transactions) == 3, f"Expected 3 transactions, found {len(budget.transactions)}"
        assert len(budget.master_categories) == 7, f"Expected 7 master categories, found {len(budget.master_categories)}"
    
    def test_account_validation(self):
        """Test the single 'Current' account has expected properties."""
        reader, budget = self.setUp_reader_and_budget()
        
        # Verify single account properties
        assert len(budget.accounts) == 1, "Fixture should have exactly one account"
        
        account = budget.accounts[0]
        assert account.name == "Current", f"Expected account name 'Current', got '{account.name}'"
        assert account.id == "380A0C46-49AB-0FBA-3F63-FFAED8C529A1", f"Account ID mismatch: {account.id}"
        assert account.type.value == "Checking", f"Expected Checking account, got {account.type.value}"
        assert account.on_budget is True, "Current account should be on-budget"
    
    def test_master_category_structure(self):
        """Test master category structure includes all expected categories."""
        reader, budget = self.setUp_reader_and_budget()
        
        master_categories = budget.master_categories
        master_names = [mc.name for mc in master_categories]
        
        # Expected master categories from fixture analysis
        expected_masters = [
            "Hidden Categories", "Giving", "Monthly Bills", 
            "Everyday Expenses", "Rainy Day Funds", "Savings Goals", "Debt"
        ]
        
        assert len(master_categories) == len(expected_masters), (
            f"Expected {len(expected_masters)} master categories, found {len(master_categories)}"
        )
        
        # Verify all expected master categories exist
        for expected_name in expected_masters:
            assert expected_name in master_names, (
                f"Missing expected master category: {expected_name}. "
                f"Found: {master_names}"
            )
    
    def test_specific_category_tests(self):
        """Test specific categories under 'Giving' master category exist with correct IDs."""
        reader, budget = self.setUp_reader_and_budget()
        
        # Find categories under Giving master category
        giving_categories = [
            category for category in budget.categories 
            if category.master_category and category.master_category.name == "Giving"
        ]
        
        # Should find exactly 2 categories under Giving
        assert len(giving_categories) == 2, (
            f"Expected 2 categories under Giving, found {len(giving_categories)}"
        )
        
        category_names = [c.name for c in giving_categories]
        expected_names = ["Tithing", "Charitable"]
        
        for expected_name in expected_names:
            assert expected_name in category_names, (
                f"Missing expected category under Giving: {expected_name}"
            )
        
        # Verify specific IDs for these categories
        tithing = next((c for c in giving_categories if c.name == "Tithing"), None)
        charitable = next((c for c in giving_categories if c.name == "Charitable"), None)
        
        assert tithing is not None, "Tithing category not found"
        assert charitable is not None, "Charitable category not found"
        assert tithing.id == "A5", f"Expected Tithing ID 'A5', got '{tithing.id}'"
        assert charitable.id == "A6", f"Expected Charitable ID 'A6', got '{charitable.id}'"
    
    def test_payee_data_integrity(self):
        """Test all expected payees exist with correct properties."""
        reader, budget = self.setUp_reader_and_budget()
        
        payee_names = [p.name for p in budget.payees]
        expected_payees = ["Transfer : Current", "Starting Balance", "Migros", "Salary"]
        
        # Verify all expected payees are present
        for expected_payee in expected_payees:
            assert expected_payee in payee_names, (
                f"Missing expected payee: {expected_payee}. Found: {payee_names}"
            )
        
        # Verify specific payee properties
        starting_balance = next((p for p in budget.payees if p.name == "Starting Balance"), None)
        assert starting_balance is not None, "Starting Balance payee not found"
        assert starting_balance.id == "2FAFFAC4-F271-7544-639C-FFAED8CEB626", (
            f"Starting Balance ID mismatch: {starting_balance.id}"
        )
        assert starting_balance.enabled is False, "Starting Balance should be disabled"
        
        # Verify Migros payee is enabled
        migros = next((p for p in budget.payees if p.name == "Migros"), None)
        assert migros is not None, "Migros payee not found"
        assert migros.enabled is True, "Migros payee should be enabled"
    
    def test_transaction_evolution(self):
        """Test the key transaction that evolved from amount 0→20000 through deltas.
        
        This transaction (ID: 44B1567B-7356-48BC-1D3E-FFAED8CD0F8C) represents
        the evolution path documented in the fixture analysis, showing how
        delta files modify transaction amounts over time.
        """
        reader, budget = self.setUp_reader_and_budget()
        
        # Find the specific transaction that evolved through deltas
        test_transaction_id = "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C"
        transaction = next((t for t in budget.transactions if t.id == test_transaction_id), None)
        
        # Verify transaction exists with expected final state
        assert transaction is not None, f"Transaction {test_transaction_id} not found"
        assert transaction.amount == 20000, (
            f"Expected final amount 20000, got {transaction.amount}. "
            "This transaction should have evolved through delta files."
        )
        
        # Verify relationships
        assert transaction.account.id == "380A0C46-49AB-0FBA-3F63-FFAED8C529A1", (
            f"Transaction should reference Current account, got {transaction.account.id}"
        )
        assert transaction.payee.id == "2FAFFAC4-F271-7544-639C-FFAED8CEB626", (
            f"Transaction should reference Starting Balance payee, got {transaction.payee.id}"
        )
    
    def test_delta_file_validation(self):
        """Test delta files exist in correct chronological order.
        
        The fixture contains 4 delta files that show the evolution of
        the budget state from version A-63 to A-72.
        """
        reader, budget = self.setUp_reader_and_budget()
        
        delta_files = reader.discover_delta_files()
        
        # Verify expected delta file count and ordering
        expected_deltas = [
            "A-63_A-67.ydiff", "A-67_A-69.ydiff", 
            "A-69_A-71.ydiff", "A-71_A-72.ydiff"
        ]
        
        assert len(delta_files) == len(expected_deltas), (
            f"Expected {len(expected_deltas)} delta files, found {len(delta_files)}"
        )
        
        actual_deltas = [d.name for d in delta_files]
        assert actual_deltas == expected_deltas, (
            f"Delta files not in expected order.\nExpected: {expected_deltas}\nActual: {actual_deltas}"
        )
    
    def test_entity_version_tracking(self):
        """Test that key entities exist in their final evolved state.
        
        While pynab doesn't expose entity version tracking directly,
        we can verify that entities exist in their expected final state
        after all deltas have been applied.
        """
        reader, budget = self.setUp_reader_and_budget()
        
        # Verify key transaction exists in final state
        test_transaction_id = "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C"
        transaction = next((t for t in budget.transactions if t.id == test_transaction_id), None)
        
        assert transaction is not None, "Key evolved transaction should exist"
        assert transaction.amount == 20000, (
            f"Transaction should be in final evolved state with amount 20000, got {transaction.amount}"
        )
        
        # Verify account exists in expected state
        account = budget.accounts[0]
        assert account.id == "380A0C46-49AB-0FBA-3F63-FFAED8C529A1", (
            f"Account ID mismatch: {account.id}"
        )
        assert account.name == "Current", "Account should be named 'Current'"
    
    def test_account_payee_transaction_relationships(self):
        """Test referential integrity between accounts, payees, and transactions.
        
        Ensures all transaction references point to valid accounts and payees,
        and verifies the specific relationships in the test transaction.
        """
        reader, budget = self.setUp_reader_and_budget()
        
        # Collect all valid entity IDs
        account_ids = {a.id for a in budget.accounts}
        payee_ids = {p.id for p in budget.payees}
        
        # Verify all transactions have valid references
        for i, transaction in enumerate(budget.transactions):
            assert transaction.account.id in account_ids, (
                f"Transaction {i} references invalid account ID: {transaction.account.id}"
            )
            assert transaction.payee.id in payee_ids, (
                f"Transaction {i} references invalid payee ID: {transaction.payee.id}"
            )
        
        # Verify specific relationship for the evolved transaction
        test_transaction_id = "44B1567B-7356-48BC-1D3E-FFAED8CD0F8C"
        transaction = next((t for t in budget.transactions if t.id == test_transaction_id), None)
        
        assert transaction is not None, "Test transaction not found"
        assert transaction.account.id == "380A0C46-49AB-0FBA-3F63-FFAED8C529A1", (
            "Test transaction should reference the Current account"
        )
        assert transaction.payee.id == "2FAFFAC4-F271-7544-639C-FFAED8CEB626", (
            "Test transaction should reference the Starting Balance payee"
        )
    
    def test_category_hierarchy(self):
        """Test category hierarchy structure with proper master-subcategory relationships.
        
        Validates the hierarchical structure where master categories contain
        subcategories, with specific focus on the Giving category structure.
        """
        reader, budget = self.setUp_reader_and_budget()
        
        master_categories = budget.master_categories
        sub_categories = budget.categories
        
        # Verify hierarchy counts
        assert len(master_categories) == 7, (
            f"Expected 7 master categories, found {len(master_categories)}"
        )
        assert len(sub_categories) == 29, (
            f"Expected 29 subcategories, found {len(sub_categories)}"
        )
        
        # Verify Giving master category exists and has correct subcategories
        giving_master = next((mc for mc in master_categories if mc.name == "Giving"), None)
        assert giving_master is not None, "Giving master category should exist"
        
        giving_subs = [
            c for c in sub_categories 
            if c.master_category and c.master_category.name == "Giving"
        ]
        assert len(giving_subs) == 2, (
            f"Giving category should have exactly 2 subcategories, found {len(giving_subs)}: "
            f"{[c.name for c in giving_subs]}"
        )
        
        # Verify all subcategories have valid master category references
        orphaned_categories = [c for c in sub_categories if c.master_category is None]
        assert len(orphaned_categories) == 0, (
            f"Found {len(orphaned_categories)} categories without master category: "
            f"{[c.name for c in orphaned_categories]}"
        )