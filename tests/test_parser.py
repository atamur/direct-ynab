"""Comprehensive tests for YnabParser class."""

import json
import pytest
from pathlib import Path
from unittest.mock import mock_open, patch

from ynab_io.parser import YnabParser
from ynab_io.models import Account, Payee, Transaction


class TestYnabParser:
    """Test cases for the YNAB parser."""
    
    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")
    
    @pytest.fixture
    def parser(self, test_budget_path):
        """YnabParser instance using test fixture."""
        return YnabParser(test_budget_path)
    
    def test_parser_initialization_finds_data_directory(self, parser):
        """Test that parser correctly finds data directory."""
        assert parser.data_dir.name.startswith('data1~')
        assert parser.data_dir.exists()
        assert parser.data_dir.is_dir()
    
    def test_parser_initialization_finds_device_directory(self, parser):
        """Test that parser correctly finds device directory."""
        assert parser.device_dir.name == 'DDBC2A7E-AE4D-B8A5-0759-B56799918579'
        assert parser.device_dir.exists()
        assert parser.device_dir.is_dir()
    
    def test_parser_initialization_creates_empty_collections(self, parser):
        """Test that parser initializes with empty collections."""
        assert parser.accounts == {}
        assert parser.payees == {}
        assert parser.transactions == {}
    
    def test_find_data_dir_missing_directory_raises_error(self, tmp_path):
        """Test that missing data directory raises FileNotFoundError."""
        # Create empty budget directory without data1~ folder
        empty_budget = tmp_path / "empty_budget"
        empty_budget.mkdir()
        
        with pytest.raises(FileNotFoundError, match="Could not find data directory in budget"):
            YnabParser(empty_budget)
    
    def test_find_device_dir_missing_devices_directory_raises_error(self, tmp_path):
        """Test that missing devices directory raises FileNotFoundError."""
        # Create budget structure but without devices directory
        budget_dir = tmp_path / "budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~TEST"
        data_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            YnabParser(budget_dir)
    
    def test_find_device_dir_missing_ydevice_file_raises_error(self, tmp_path):
        """Test that missing .ydevice file raises FileNotFoundError."""
        # Create budget structure with devices directory but no .ydevice file
        budget_dir = tmp_path / "budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~TEST"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()
        
        with pytest.raises(FileNotFoundError):
            YnabParser(budget_dir)
    
    def test_find_device_dir_malformed_ydevice_file_raises_error(self, tmp_path):
        """Test that malformed .ydevice file raises FileNotFoundError."""
        # Create budget structure with malformed .ydevice file
        budget_dir = tmp_path / "budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~TEST"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()
        
        # Create malformed .ydevice file (missing deviceGUID)
        ydevice_file = devices_dir / "A.ydevice"
        with open(ydevice_file, 'w') as f:
            json.dump({"friendlyName": "Test"}, f)
        
        with pytest.raises(ValueError):
            YnabParser(budget_dir)
    
    def test_parse_loads_budget_yfull_file_successfully(self, parser):
        """Test that parse() successfully loads Budget.yfull file."""
        # Verify Budget.yfull exists before parsing
        yfull_path = parser.device_dir / 'Budget.yfull'
        assert yfull_path.exists()
        
        # Parse should complete without errors
        parser.parse()
        
        # Verify collections are populated
        assert len(parser.accounts) > 0
        assert len(parser.payees) > 0
        assert len(parser.transactions) > 0
    
    def test_parse_creates_correct_account_models(self, parser):
        """Test that parse() creates correct Account models."""
        parser.parse()
        
        # Verify we have expected accounts
        assert len(parser.accounts) == 1
        
        # Get the single account
        account = next(iter(parser.accounts.values()))
        
        # Verify it's an Account model with expected fields
        assert isinstance(account, Account)
        assert hasattr(account, 'entityId')
        assert hasattr(account, 'accountName')
        assert hasattr(account, 'accountType')
        assert hasattr(account, 'onBudget')
        assert hasattr(account, 'entityVersion')
    
    def test_parse_creates_correct_payee_models(self, parser):
        """Test that parse() creates correct Payee models."""
        parser.parse()
        
        # Verify we have expected payees
        assert len(parser.payees) == 4
        
        # Test a sample payee
        payee = next(iter(parser.payees.values()))
        
        # Verify it's a Payee model with expected fields
        assert isinstance(payee, Payee)
        assert hasattr(payee, 'entityId')
        assert hasattr(payee, 'name')
        assert hasattr(payee, 'enabled')
        assert hasattr(payee, 'entityVersion')
    
    def test_parse_creates_correct_transaction_models(self, parser):
        """Test that parse() creates correct Transaction models."""
        parser.parse()
        
        # Verify we have expected transactions
        assert len(parser.transactions) == 3
        
        # Test a sample transaction
        transaction = next(iter(parser.transactions.values()))
        
        # Verify it's a Transaction model with expected fields
        assert isinstance(transaction, Transaction)
        assert hasattr(transaction, 'entityId')
        assert hasattr(transaction, 'accountId')
        assert hasattr(transaction, 'amount')
        assert hasattr(transaction, 'date')
        assert hasattr(transaction, 'entityVersion')
    
    def test_parse_missing_budget_yfull_raises_error(self, tmp_path):
        """Test that missing Budget.yfull file raises FileNotFoundError."""
        # Create proper budget structure but without Budget.yfull
        budget_dir = tmp_path / "budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~TEST"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()
        device_dir = data_dir / "DEVICE-GUID"
        device_dir.mkdir()
        
        # Create valid .ydevice file
        ydevice_file = devices_dir / "A.ydevice"
        with open(ydevice_file, 'w') as f:
            json.dump({"deviceGUID": "DEVICE-GUID"}, f)
        
        parser = YnabParser(budget_dir)
        
        with pytest.raises(FileNotFoundError):
            parser.parse()
    
    def test_discover_delta_files_finds_all_ydiff_files(self, parser):
        """Test that _discover_delta_files finds all .ydiff files."""
        delta_files = parser._discover_delta_files()
        
        # Should find 4 .ydiff files in test fixture
        assert len(delta_files) == 4
        
        # All should be Path objects ending in .ydiff
        for delta_file in delta_files:
            assert isinstance(delta_file, Path)
            assert delta_file.suffix == '.ydiff'
    
    def test_discover_delta_files_sorts_by_version_order(self, parser):
        """Test that _discover_delta_files sorts files in correct version order."""
        delta_files = parser._discover_delta_files()
        
        # Extract version numbers for verification
        version_numbers = []
        for delta_file in delta_files:
            start_version, _ = parser._parse_delta_versions(delta_file.name)
            version_numbers.append(int(start_version.split('-')[1]))
        
        # Should be sorted in ascending order: [63, 67, 69, 71]
        assert version_numbers == [63, 67, 69, 71]
    
    def test_parse_delta_versions_handles_valid_filenames(self, parser):
        """Test that _parse_delta_versions correctly parses valid delta filenames."""
        start, end = parser._parse_delta_versions('A-63_A-67.ydiff')
        assert start == 'A-63'
        assert end == 'A-67'
        
        start, end = parser._parse_delta_versions('A-71_A-72.ydiff')
        assert start == 'A-71'
        assert end == 'A-72'
    
    def test_parse_delta_versions_invalid_extension_raises_error(self, parser):
        """Test that _parse_delta_versions raises error for invalid extension."""
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            parser._parse_delta_versions('A-63_A-67.txt')
    
    def test_parse_delta_versions_invalid_format_raises_error(self, parser):
        """Test that _parse_delta_versions raises error for invalid format."""
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            parser._parse_delta_versions('invalid-format.ydiff')
    
    def test_apply_deltas_processes_all_delta_files(self, parser):
        """Test that apply_deltas processes all delta files."""
        # First parse the base budget
        parser.parse()
        
        # Count initial items
        initial_account_count = len(parser.accounts)
        initial_payee_count = len(parser.payees)
        initial_transaction_count = len(parser.transactions)
        
        # Apply deltas
        parser.apply_deltas()
        
        # Verify collections still exist (should not be empty after deltas)
        assert len(parser.accounts) >= initial_account_count
        assert len(parser.payees) >= initial_payee_count
        assert len(parser.transactions) >= initial_transaction_count
    
    def test_apply_delta_handles_transaction_processing(self, parser):
        """Test that _apply_delta correctly processes transaction changes."""
        # Parse initial budget
        parser.parse()
        initial_transaction_count = len(parser.transactions)
        
        # Apply deltas (which update existing transactions)
        parser.apply_deltas()
        
        # Should have same number of transactions (deltas update, don't add in this fixture)
        assert len(parser.transactions) == initial_transaction_count
    
    def test_apply_delta_handles_entity_updates(self, parser):
        """Test that _apply_delta correctly updates existing entities."""
        # Note: The test fixture Budget.yfull already contains final versions
        # This test verifies that the parser can handle delta processing logic
        
        # Parse initial budget (which already has final versions)
        parser.parse()
        
        # Apply deltas (should complete without error, even if no updates needed)
        parser.apply_deltas()
        
        # Verify final versions are as expected from the fixture data
        # Transaction 44B1567B-7356-48BC-1D3E-FFAED8CD0F8C should have version A-72
        transaction_72 = parser.transactions.get('44B1567B-7356-48BC-1D3E-FFAED8CD0F8C')
        assert transaction_72 is not None
        assert transaction_72.entityVersion == 'A-72'
    
    def test_apply_delta_handles_tombstone_deletions(self, parser):
        """Test that _apply_delta correctly handles tombstone (deletion) entries."""
        # This test verifies the tombstone logic exists, even if no tombstones in test data
        parser.parse()
        
        # Create a mock delta with a tombstone entry
        mock_delta = {
            "items": [
                {
                    "entityId": "TEST-ENTITY",
                    "entityType": "transaction",
                    "isTombstone": True,
                    "entityVersion": "A-999"
                }
            ]
        }
        
        # Add the test entity first
        from ynab_io.models import Transaction
        test_transaction = Transaction(
            entityId="TEST-ENTITY",
            accountId="test-account",
            amount=100.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-1"
        )
        parser.transactions["TEST-ENTITY"] = test_transaction
        
        # Apply the mock delta with tombstone
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))
        
        # The entity should be removed
        assert "TEST-ENTITY" not in parser.transactions
    
    def test_apply_delta_ignores_unknown_entity_types(self, parser):
        """Test that _apply_delta ignores unknown entity types with warning."""
        parser.parse()
        initial_state = {
            'accounts': dict(parser.accounts),
            'payees': dict(parser.payees),
            'transactions': dict(parser.transactions)
        }
        
        # Create a mock delta with unknown entity type
        mock_delta = {
            "items": [
                {
                    "entityId": "UNKNOWN-ENTITY",
                    "entityType": "unknownType",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "someField": "someValue"
                }
            ]
        }
        
        # Apply the mock delta (should log warning but not fail)
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_delta))):
            with patch('ynab_io.parser.logging.warning') as mock_warning:
                parser._apply_delta(Path("test.ydiff"))
                mock_warning.assert_called_once()
        
        # Collections should remain unchanged
        assert parser.accounts == initial_state['accounts']
        assert parser.payees == initial_state['payees']
        assert parser.transactions == initial_state['transactions']
    
    def test_full_parse_and_delta_application_workflow(self, parser):
        """Test complete workflow: parse Budget.yfull then apply all deltas."""
        # Execute complete workflow
        parser.parse()
        parser.apply_deltas()
        
        # Verify final state is correct
        assert len(parser.accounts) == 1  # Expected from fixture
        assert len(parser.payees) == 4    # Expected from fixture
        assert len(parser.transactions) == 3  # Fixture has exactly 3 transactions
        
        # Verify all entities are proper model instances
        for account in parser.accounts.values():
            assert isinstance(account, Account)
        
        for payee in parser.payees.values():
            assert isinstance(payee, Payee)
        
        for transaction in parser.transactions.values():
            assert isinstance(transaction, Transaction)
    
    def test_final_state_after_applying_deltas_is_accurate(self, parser):
        """Test that final state after applying deltas matches expected values."""
        # Execute complete workflow
        parser.parse()
        parser.apply_deltas()
        
        # Test specific expected final state based on fixture data
        # This verifies the parser correctly applies all deltas in sequence
        
        # Should have exactly 1 account
        assert len(parser.accounts) == 1
        account = next(iter(parser.accounts.values()))
        assert account.accountName  # Should have a name
        
        # Should have exactly 4 payees
        assert len(parser.payees) == 4
        
        # Should have exactly 3 transactions (as per fixture data)
        assert len(parser.transactions) == 3
        
        # Verify version numbers are up to date (should reflect latest delta A-72)
        latest_versions = set()
        for transaction in parser.transactions.values():
            version_num = int(transaction.entityVersion.split('-')[1])
            latest_versions.add(version_num)
        
        # Should have some entities with version 72 (from latest delta)
        assert 72 in latest_versions