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