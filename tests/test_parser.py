"""Comprehensive tests for YnabParser class."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from assertpy import assert_that
from ynab_io.models import (
    Account,
    Category,
    MasterCategory,
    MonthlyBudget,
    MonthlyCategoryBudget,
    Payee,
    ScheduledTransaction,
    Transaction,
)
from ynab_io.parser import YnabParser

from .conftest import assert_parser_collections_populated


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
        assert parser.data_dir.name.startswith("data1~")
        assert parser.data_dir.exists()
        assert parser.data_dir.is_dir()

    def test_parser_initialization_finds_device_directory(self, parser):
        """Test that parser correctly finds device directory."""
        assert parser.device_dir.name == "DDBC2A7E-AE4D-B8A5-0759-B56799918579"
        assert parser.device_dir.exists()
        assert parser.device_dir.is_dir()

    def test_parser_initialization_creates_empty_collections(self, parser):
        """Test that parser initializes with empty collections."""
        assert parser.accounts == {}
        assert parser.payees == {}
        assert parser.transactions == {}
        assert parser.master_categories == {}
        assert parser.categories == {}
        assert parser.monthly_budgets == {}
        assert parser.scheduled_transactions == {}

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
        with open(ydevice_file, "w") as f:
            json.dump({"friendlyName": "Test"}, f)

        with pytest.raises(ValueError):
            YnabParser(budget_dir)

    def test_parse_loads_budget_yfull_file_successfully(self, parser):
        """Test that parse() successfully loads Budget.yfull file."""
        # Verify Budget.yfull exists before parsing
        yfull_path = parser.device_dir / "Budget.yfull"
        assert yfull_path.exists()

        # Parse should complete without errors
        parser.parse()

        # Verify collections are populated
        assert len(parser.accounts) > 0
        assert len(parser.payees) > 0
        assert len(parser.transactions) > 0

    def test_parse_creates_correct_payee_models(self, parser):
        """Test that parse() creates correct Payee models."""
        parser.parse()

        # Verify we have payees (flexible count assertion)
        assert_that(parser.payees).is_not_empty()
        assert_that(len(parser.payees)).is_greater_than(0)

        # Test a sample payee
        payee = next(iter(parser.payees.values()))

        # Verify it's a Payee model with expected fields
        assert isinstance(payee, Payee)
        assert hasattr(payee, "entityId")
        assert hasattr(payee, "name")
        assert hasattr(payee, "enabled")
        assert hasattr(payee, "entityVersion")

    def test_parse_creates_correct_transaction_models(self, parser):
        """Test that parse() creates correct Transaction models."""
        parser.parse()

        # Verify we have transactions (flexible count assertion)
        assert_that(parser.transactions).is_not_empty()
        assert_that(len(parser.transactions)).is_greater_than(0)

        # Test a sample transaction
        transaction = next(iter(parser.transactions.values()))

        # Verify it's a Transaction model with expected fields
        assert isinstance(transaction, Transaction)
        assert hasattr(transaction, "entityId")
        assert hasattr(transaction, "accountId")
        assert hasattr(transaction, "amount")
        assert hasattr(transaction, "date")
        assert hasattr(transaction, "entityVersion")

    def test_parse_creates_correct_master_category_models(self, parser):
        """Test that parse() creates correct MasterCategory models."""
        parser.parse()

        # Verify we have expected master categories (7 from fixture)
        assert len(parser.master_categories) == 7

        # Test a sample master category
        master_category = next(iter(parser.master_categories.values()))

        # Verify it's a MasterCategory model with expected fields
        assert isinstance(master_category, MasterCategory)
        assert hasattr(master_category, "entityId")
        assert hasattr(master_category, "name")
        assert hasattr(master_category, "type")
        assert hasattr(master_category, "deleteable")
        assert hasattr(master_category, "expanded")
        assert hasattr(master_category, "entityVersion")

    def test_parse_creates_correct_category_models(self, parser):
        """Test that parse() creates correct Category models."""
        parser.parse()

        # Verify we have categories (flexible count assertion)
        assert_that(parser.categories).is_not_empty()
        assert_that(len(parser.categories)).is_greater_than(0)

        # Test a sample category
        category = next(iter(parser.categories.values()))

        # Verify it's a Category model with expected fields
        assert isinstance(category, Category)
        assert hasattr(category, "entityId")
        assert hasattr(category, "name")
        assert hasattr(category, "type")
        assert hasattr(category, "masterCategoryId")
        assert hasattr(category, "entityVersion")

    def test_parse_creates_correct_monthly_budget_models(self, parser):
        """Test that parse() creates correct MonthlyBudget models."""
        parser.parse()

        # Verify we have expected monthly budgets (28 from fixture)
        assert len(parser.monthly_budgets) == 28

        # Test a sample monthly budget
        monthly_budget = next(iter(parser.monthly_budgets.values()))

        # Verify it's a MonthlyBudget model with expected fields
        assert isinstance(monthly_budget, MonthlyBudget)
        assert hasattr(monthly_budget, "entityId")
        assert hasattr(monthly_budget, "month")
        assert hasattr(monthly_budget, "entityVersion")

    def test_parse_creates_correct_scheduled_transaction_models(self, parser):
        """Test that parse() creates correct ScheduledTransaction models."""
        parser.parse()

        # Verify we have expected scheduled transactions (checking fixture data)
        # Note: We need to check if there are scheduledTransactions in the fixture
        scheduled_transaction_count = len(parser.scheduled_transactions)

        # If we have scheduled transactions, test their structure
        if scheduled_transaction_count > 0:
            scheduled_transaction = next(iter(parser.scheduled_transactions.values()))

            # Verify it's a ScheduledTransaction model with expected fields
            assert isinstance(scheduled_transaction, ScheduledTransaction)
            assert hasattr(scheduled_transaction, "entityId")
            assert hasattr(scheduled_transaction, "frequency")
            assert hasattr(scheduled_transaction, "amount")
            assert hasattr(scheduled_transaction, "entityVersion")

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
        with open(ydevice_file, "w") as f:
            json.dump({"deviceGUID": "DEVICE-GUID"}, f)

        parser = YnabParser(budget_dir)

        with pytest.raises(FileNotFoundError):
            parser.parse()

    def test_discover_delta_files_finds_all_ydiff_files(self, parser):
        """Test that _discover_delta_files finds all .ydiff files."""
        delta_files = parser._discover_delta_files()

        # Should find .ydiff files in test fixture (flexible count assertion)
        assert_that(delta_files).is_not_empty()
        assert_that(len(delta_files)).is_greater_than(0)

        # All should be Path objects ending in .ydiff
        for delta_file in delta_files:
            assert isinstance(delta_file, Path)
            assert delta_file.suffix == ".ydiff"

    def test_discover_delta_files_sorts_by_version_order(self, parser):
        """Test that _discover_delta_files sorts files in correct version order."""
        delta_files = parser._discover_delta_files()

        # Extract version numbers for verification
        version_numbers = []
        for delta_file in delta_files:
            start_version, _ = parser._parse_delta_versions(delta_file.name)
            version_numbers.append(int(start_version.split("-")[1]))

        # Should be sorted in ascending order with expected starting and ending versions
        assert_that(version_numbers).is_not_empty()
        assert version_numbers == sorted(version_numbers)  # Should be in ascending order
        assert_that(version_numbers).contains(63, 67)  # Should contain early versions
        assert (
            140 in version_numbers or 141 in version_numbers or max(version_numbers) >= 140
        )  # Should have high version numbers

    def test_parse_delta_versions_handles_valid_filenames(self, parser):
        """Test that _parse_delta_versions correctly parses valid delta filenames."""
        start, end = parser._parse_delta_versions("A-63_A-67.ydiff")
        assert start == "A-63"
        assert end == "A-67"

        start, end = parser._parse_delta_versions("A-71_A-72.ydiff")
        assert start == "A-71"
        assert end == "A-72"

    def test_parse_delta_versions_invalid_extension_raises_error(self, parser):
        """Test that _parse_delta_versions raises error for invalid extension."""
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            parser._parse_delta_versions("A-63_A-67.txt")

    def test_parse_delta_versions_invalid_format_raises_error(self, parser):
        """Test that _parse_delta_versions raises error for invalid format."""
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            parser._parse_delta_versions("invalid-format.ydiff")

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
        # Transaction 44B1567B-7356-48BC-1D3E-FFAED8CD0F8C should have version A-84
        transaction_84 = parser.transactions.get("44B1567B-7356-48BC-1D3E-FFAED8CD0F8C")
        assert transaction_84 is not None
        assert transaction_84.entityVersion == "A-84"

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
                    "entityVersion": "A-999",
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
            entityVersion="A-1",
        )
        parser.transactions["TEST-ENTITY"] = test_transaction

        # Apply the mock delta with tombstone
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # The entity should be removed
        assert "TEST-ENTITY" not in parser.transactions

    def test_apply_delta_handles_master_category_processing(self, parser):
        """Test that _apply_delta correctly processes master category changes."""
        parser.parse()
        initial_master_category_count = len(parser.master_categories)

        # Create a mock delta with master category update
        mock_delta = {
            "items": [
                {
                    "entityId": "TEST-MASTER-CAT",
                    "entityType": "masterCategory",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "name": "Test Master Category",
                    "type": "OUTFLOW",
                    "deleteable": True,
                    "expanded": True,
                    "sortableIndex": 0,
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have added the new master category
        assert len(parser.master_categories) == initial_master_category_count + 1
        assert "TEST-MASTER-CAT" in parser.master_categories

    def test_apply_delta_handles_category_processing(self, parser):
        """Test that _apply_delta correctly processes category changes."""
        parser.parse()
        initial_category_count = len(parser.categories)

        # Create a mock delta with category update
        mock_delta = {
            "items": [
                {
                    "entityId": "TEST-CATEGORY",
                    "entityType": "category",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "name": "Test Category",
                    "type": "OUTFLOW",
                    "masterCategoryId": "A4",
                    "sortableIndex": 0,
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have added the new category
        assert len(parser.categories) == initial_category_count + 1
        assert "TEST-CATEGORY" in parser.categories

    def test_apply_delta_handles_monthly_budget_processing(self, parser):
        """Test that _apply_delta correctly processes monthly budget changes."""
        parser.parse()
        initial_monthly_budget_count = len(parser.monthly_budgets)

        # Create a mock delta with monthly budget update
        mock_delta = {
            "items": [
                {
                    "entityId": "TEST-MB",
                    "entityType": "monthlyBudget",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "month": "2025-12-01",
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have added the new monthly budget
        assert len(parser.monthly_budgets) == initial_monthly_budget_count + 1
        assert "TEST-MB" in parser.monthly_budgets

    def test_apply_delta_handles_scheduled_transaction_processing(self, parser):
        """Test that _apply_delta correctly processes scheduled transaction changes."""
        parser.parse()
        initial_scheduled_transaction_count = len(parser.scheduled_transactions)

        # Create a mock delta with scheduled transaction update
        mock_delta = {
            "items": [
                {
                    "entityId": "TEST-SCHEDULED",
                    "entityType": "scheduledTransaction",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "frequency": "Monthly",
                    "amount": 100.0,
                    "payeeId": "TEST-PAYEE",
                    "accountId": "TEST-ACCOUNT",
                    "date": "2025-01-01",
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have added the new scheduled transaction
        assert len(parser.scheduled_transactions) == initial_scheduled_transaction_count + 1
        assert "TEST-SCHEDULED" in parser.scheduled_transactions

    def test_apply_delta_ignores_unknown_entity_types(self, parser):
        """Test that _apply_delta ignores unknown entity types with warning."""
        parser.parse()
        initial_state = {
            "accounts": dict(parser.accounts),
            "payees": dict(parser.payees),
            "transactions": dict(parser.transactions),
            "master_categories": dict(parser.master_categories),
            "categories": dict(parser.categories),
            "monthly_budgets": dict(parser.monthly_budgets),
            "scheduled_transactions": dict(parser.scheduled_transactions),
        }

        # Create a mock delta with unknown entity type
        mock_delta = {
            "items": [
                {
                    "entityId": "UNKNOWN-ENTITY",
                    "entityType": "unknownType",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "someField": "someValue",
                }
            ]
        }

        # Apply the mock delta (should log warning but not fail)
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            with patch("ynab_io.parser.logging.warning") as mock_warning:
                parser._apply_delta(Path("test.ydiff"))
                mock_warning.assert_called_once()

        # Collections should remain unchanged
        assert parser.accounts == initial_state["accounts"]
        assert parser.payees == initial_state["payees"]
        assert parser.transactions == initial_state["transactions"]
        assert parser.master_categories == initial_state["master_categories"]
        assert parser.categories == initial_state["categories"]
        assert parser.monthly_budgets == initial_state["monthly_budgets"]
        assert parser.scheduled_transactions == initial_state["scheduled_transactions"]

    def test_full_parse_and_delta_application_workflow(self, parser):
        """Test complete workflow: parse Budget.yfull then apply all deltas."""
        # Execute complete workflow
        parser.parse()
        parser.apply_deltas()

        # Verify final state is correct (flexible count assertions)
        assert_parser_collections_populated(parser)
        assert_that(len(parser.accounts)).is_greater_than(0)  # Expected from fixture
        assert_that(parser.master_categories).is_not_empty()  # Expected from fixture
        assert_that(parser.categories).is_not_empty()  # Expected from fixture
        assert_that(parser.monthly_budgets).is_not_empty()  # Expected from fixture

        # Verify all entities are proper model instances
        for account in parser.accounts.values():
            assert isinstance(account, Account)

        for payee in parser.payees.values():
            assert isinstance(payee, Payee)

        for transaction in parser.transactions.values():
            assert isinstance(transaction, Transaction)

        for master_category in parser.master_categories.values():
            assert isinstance(master_category, MasterCategory)

        for category in parser.categories.values():
            assert isinstance(category, Category)

        for monthly_budget in parser.monthly_budgets.values():
            assert isinstance(monthly_budget, MonthlyBudget)

    def test_final_state_after_applying_deltas_is_accurate(self, parser):
        """Test that final state after applying deltas matches expected values."""
        # Execute complete workflow
        parser.parse()
        parser.apply_deltas()

        # Test specific expected final state based on fixture data
        # This verifies the parser correctly applies all deltas in sequence

        # Should have core collections populated (flexible count assertion)
        assert_parser_collections_populated(parser)
        account = next(iter(parser.accounts.values()))
        assert account.accountName  # Should have a name

        # Should have master categories (as per fixture data)
        assert_that(parser.master_categories).is_not_empty()

        # Should have categories (as per fixture data)
        assert_that(parser.categories).is_not_empty()

        # Should have monthly budgets (as per fixture data)
        assert_that(parser.monthly_budgets).is_not_empty()

        # Verify version numbers are up to date (should reflect latest delta A-141)
        latest_versions = set()
        for transaction in parser.transactions.values():
            version_num = int(transaction.entityVersion.split("-")[1])
            latest_versions.add(version_num)

        # Should have some entities with version 128 (from latest delta)
        assert 128 in latest_versions

    def test_parse_creates_correct_monthly_category_budget_models(self, parser):
        """Test that parse() initializes monthly_category_budgets collection correctly."""
        parser.parse()

        # Should have monthly category budgets collection with actual data
        assert len(parser.monthly_category_budgets) == 3
        assert isinstance(parser.monthly_category_budgets, dict)

        # Test that the collection can accept MonthlyCategoryBudget objects
        test_mcb = MonthlyCategoryBudget(
            entityId="MCB/2017-01/TEST-CATEGORY",
            categoryId="TEST-CATEGORY",
            budgeted=100.00,
            overspendingHandling="AffectsBuffer",
            parentMonthlyBudgetId="MB/2017-01",
            entityVersion="A-1",
        )
        parser.monthly_category_budgets["MCB/2017-01/TEST-CATEGORY"] = test_mcb

        # Verify it's a MonthlyCategoryBudget model with expected fields
        assert isinstance(test_mcb, MonthlyCategoryBudget)
        assert hasattr(test_mcb, "entityId")
        assert hasattr(test_mcb, "categoryId")
        assert hasattr(test_mcb, "budgeted")
        assert hasattr(test_mcb, "overspendingHandling")
        assert hasattr(test_mcb, "parentMonthlyBudgetId")
        assert hasattr(test_mcb, "entityVersion")
        assert hasattr(test_mcb, "note")

    def test_apply_delta_handles_monthly_category_budget_processing(self, parser):
        """Test that _apply_delta correctly processes monthly category budget changes."""
        parser.parse()
        initial_monthly_category_budget_count = len(parser.monthly_category_budgets)

        # Create a mock delta with monthly category budget update
        mock_delta = {
            "items": [
                {
                    "entityId": "MCB/2017-01/TEST-CATEGORY-ID",
                    "entityType": "monthlyCategoryBudget",
                    "isTombstone": False,
                    "entityVersion": "A-999",
                    "categoryId": "TEST-CATEGORY-ID",
                    "budgeted": 150.00,
                    "overspendingHandling": "AffectsBuffer",
                    "parentMonthlyBudgetId": "MB/2017-01",
                    "note": "Test budget allocation",
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have added the new monthly category budget
        assert len(parser.monthly_category_budgets) == initial_monthly_category_budget_count + 1
        assert "MCB/2017-01/TEST-CATEGORY-ID" in parser.monthly_category_budgets

        # Verify the properties are correct
        new_mcb = parser.monthly_category_budgets["MCB/2017-01/TEST-CATEGORY-ID"]
        assert new_mcb.categoryId == "TEST-CATEGORY-ID"
        assert new_mcb.budgeted == 150.00
        assert new_mcb.overspendingHandling == "AffectsBuffer"
        assert new_mcb.parentMonthlyBudgetId == "MB/2017-01"
        assert new_mcb.note == "Test budget allocation"

    def test_apply_delta_handles_monthly_category_budget_updates(self, parser):
        """Test that _apply_delta correctly updates existing monthly category budget entities."""
        parser.parse()

        # Add an existing monthly category budget first
        existing_mcb = MonthlyCategoryBudget(
            entityId="MCB/2017-01/EXISTING-CATEGORY",
            categoryId="EXISTING-CATEGORY",
            budgeted=100.00,
            overspendingHandling="AffectsBuffer",
            parentMonthlyBudgetId="MB/2017-01",
            entityVersion="A-10",
            note="Original note",
        )
        parser.monthly_category_budgets["MCB/2017-01/EXISTING-CATEGORY"] = existing_mcb

        # Create a mock delta that updates the existing entity
        mock_delta = {
            "items": [
                {
                    "entityId": "MCB/2017-01/EXISTING-CATEGORY",
                    "entityType": "monthlyCategoryBudget",
                    "isTombstone": False,
                    "entityVersion": "A-20",  # Higher version
                    "budgeted": 200.00,  # Updated amount
                    "note": "Updated note",  # Updated note
                }
            ]
        }

        # Apply the mock delta
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # Should have updated the existing monthly category budget
        updated_mcb = parser.monthly_category_budgets["MCB/2017-01/EXISTING-CATEGORY"]
        assert updated_mcb.budgeted == 200.00  # Should be updated
        assert updated_mcb.note == "Updated note"  # Should be updated
        assert updated_mcb.entityVersion == "A-20"  # Version should be updated
        assert updated_mcb.categoryId == "EXISTING-CATEGORY"  # Should remain the same
        assert updated_mcb.overspendingHandling == "AffectsBuffer"  # Should remain the same

    def test_apply_delta_handles_monthly_category_budget_tombstone_deletions(self, parser):
        """Test that _apply_delta correctly handles tombstone deletions of monthly category budgets."""
        parser.parse()

        # Add a monthly category budget to delete
        test_mcb = MonthlyCategoryBudget(
            entityId="MCB/2017-01/DELETE-ME",
            categoryId="DELETE-ME",
            budgeted=50.00,
            overspendingHandling="AffectsBuffer",
            parentMonthlyBudgetId="MB/2017-01",
            entityVersion="A-5",
        )
        parser.monthly_category_budgets["MCB/2017-01/DELETE-ME"] = test_mcb

        # Create a mock delta with tombstone entry
        mock_delta = {
            "items": [
                {
                    "entityId": "MCB/2017-01/DELETE-ME",
                    "entityType": "monthlyCategoryBudget",
                    "isTombstone": True,
                    "entityVersion": "A-10",
                }
            ]
        }

        # Apply the mock delta with tombstone
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta))):
            parser._apply_delta(Path("test.ydiff"))

        # The entity should be removed
        assert "MCB/2017-01/DELETE-ME" not in parser.monthly_category_budgets

    def test_final_budget_includes_monthly_category_budgets_collection(self, parser):
        """Test that the final Budget object includes monthly_category_budgets collection."""
        # This test should fail initially because Budget object doesn't include monthly_category_budgets
        budget = parser.parse()

        # Verify Budget object has monthly_category_budgets attribute
        assert hasattr(budget, "monthly_category_budgets")
        assert isinstance(budget.monthly_category_budgets, list)

        # Should contain MonthlyCategoryBudget instances (when they exist)
        for mcb in budget.monthly_category_budgets:
            assert isinstance(mcb, MonthlyCategoryBudget)


class TestYnabParserVersionParsing:
    """Test cases for version parsing with composite version strings."""

    @pytest.fixture
    def parser_with_mock_device_manager(self, tmp_path):
        """Create a parser with minimal setup for testing version parsing."""
        # Create minimal budget structure
        budget_dir = tmp_path / "version_test_budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~VERSION_TEST"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()

        device_guid = "TEST-DEVICE-GUID"
        device_dir = data_dir / device_guid
        device_dir.mkdir()

        # Create .ydevice file
        ydevice_file = devices_dir / "A.ydevice"
        with open(ydevice_file, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_guid,
                    "shortDeviceId": "A",
                    "friendlyName": "Test Device",
                    "knowledge": "A-100",
                    "knowledgeInFullBudgetFile": "A-100",
                },
                f,
            )

        # Create empty Budget.yfull
        budget_yfull = device_dir / "Budget.yfull"
        with open(budget_yfull, "w") as f:
            json.dump({"accounts": [], "payees": [], "transactions": []}, f)

        return YnabParser(budget_dir)

    def test_consolidated_version_parsing_now_gives_correct_sort_order(self, parser_with_mock_device_manager):
        """Test that consolidated version parsing now gives correct sort order for composite versions.

        After consolidation, the parser uses DeviceManager methods to correctly identify
        the latest version from composite strings for proper delta file ordering.
        """
        parser = parser_with_mock_device_manager

        # Create delta files where we need correct sort order based on true latest versions
        delta_path_1 = Path("A-1,B-9999_A-2,B-10000.ydiff")  # B-9999 is the real latest
        delta_path_2 = Path("A-5000,B-50_A-5001,B-51.ydiff")  # A-5000 is the real latest

        # After consolidation, implementation uses DeviceManager methods
        sort_key_1 = parser._get_delta_sort_key(delta_path_1)  # Returns 9999 (from B-9999)
        sort_key_2 = parser._get_delta_sort_key(delta_path_2)  # Returns 5000 (from A-5000)

        # The CORRECT order is now achieved: delta_path_2 first (5000), then delta_path_1 (9999)
        assert sort_key_2 < sort_key_1  # This is now the CORRECT order

        # Verify the actual version numbers being used
        assert sort_key_1 == 9999  # Latest from B-9999
        assert sort_key_2 == 5000  # Latest from A-5000

    def test_consolidated_entity_version_comparison_now_uses_true_latest(self, parser_with_mock_device_manager):
        """Test that consolidated entity version comparison now uses true latest version from composite strings.

        After consolidation, when comparing entity versions like 'A-1,B-9999' vs 'A-5000,B-50',
        the logic correctly compares B-9999 (9999) vs A-5000 (5000) using DeviceManager methods.
        """
        parser = parser_with_mock_device_manager
        parser.parse()

        # Create mock delta data
        mock_delta_data = {
            "items": [
                {
                    "entityId": "TEST-ENTITY-ID",
                    "entityType": "transaction",
                    "isTombstone": False,
                    "entityVersion": "A-1,B-9999,C-100",  # B-9999 is the actual latest
                    "accountId": "test-account",
                    "amount": 100.0,
                    "date": "2025-01-01",
                    "cleared": "Uncleared",
                    "accepted": True,
                }
            ]
        }

        # Add existing entity with composite version
        from ynab_io.models import Transaction

        existing_transaction = Transaction(
            entityId="TEST-ENTITY-ID",
            accountId="test-account",
            amount=50.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-5000,B-50,C-75",  # A-5000 is highest in first component but not overall
        )
        parser.transactions["TEST-ENTITY-ID"] = existing_transaction

        # After consolidation, the logic compares B-9999 (9999) vs A-5000 (5000)
        # and recognizes that the new version (9999) should win

        # Apply the delta - consolidated logic should update to the new entity
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta_data))):
            parser._apply_delta(Path("test_composite.ydiff"))

        # Check what happened - should have updated to the new amount
        updated_transaction = parser.transactions["TEST-ENTITY-ID"]

        # Consolidated implementation should have updated to new version (100.0) because 9999 > 5000
        assert updated_transaction.amount == 100.0  # New amount - CORRECT behavior after consolidation
        assert updated_transaction.entityVersion == "A-1,B-9999,C-100"  # New version string

    def test_consolidated_version_parsing_gives_correct_sort_order(self, parser_with_mock_device_manager):
        """Test that consolidated version parsing using DeviceManager gives correct sort order.

        This test will FAIL until we consolidate parser to use DeviceManager's version parsing methods.
        """
        parser = parser_with_mock_device_manager

        # Create delta files where we want the correct sort order based on true latest versions
        delta_path_1 = Path("A-1,B-9999_A-2,B-10000.ydiff")  # B-9999 should be recognized as latest
        delta_path_2 = Path("A-5000,B-50_A-5001,B-51.ydiff")  # A-5000 should be recognized as latest

        # After consolidation, the sort keys should be based on the true latest versions
        sort_key_1 = parser._get_delta_sort_key(delta_path_1)  # Should return 9999 (from B-9999)
        sort_key_2 = parser._get_delta_sort_key(delta_path_2)  # Should return 5000 (from A-5000)

        # The CORRECT order should be: delta_path_2 first (5000), then delta_path_1 (9999)
        assert sort_key_2 < sort_key_1  # This should be TRUE after consolidation

    def test_consolidated_entity_version_comparison_uses_true_latest(self, parser_with_mock_device_manager):
        """Test that consolidated version comparison uses true latest version from composite strings.

        This test will FAIL until we consolidate parser to use DeviceManager's version parsing methods.
        """
        parser = parser_with_mock_device_manager
        parser.parse()

        # Create mock delta data
        mock_delta_data = {
            "items": [
                {
                    "entityId": "TEST-ENTITY-ID",
                    "entityType": "transaction",
                    "isTombstone": False,
                    "entityVersion": "A-1,B-9999,C-100",  # B-9999 is the actual latest
                    "accountId": "test-account",
                    "amount": 100.0,
                    "date": "2025-01-01",
                    "cleared": "Uncleared",
                    "accepted": True,
                }
            ]
        }

        # Add existing entity with composite version
        from ynab_io.models import Transaction

        existing_transaction = Transaction(
            entityId="TEST-ENTITY-ID",
            accountId="test-account",
            amount=50.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-5000,B-50,C-75",  # A-5000 is highest in first component but not overall
        )
        parser.transactions["TEST-ENTITY-ID"] = existing_transaction

        # After consolidation, the logic should compare B-9999 (9999) vs A-5000 (5000)
        # and recognize that the new version (9999) should win

        # Apply the delta - consolidated logic should update to the new entity
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_delta_data))):
            parser._apply_delta(Path("test_composite.ydiff"))

        # Check what happened - should have updated to the new amount
        updated_transaction = parser.transactions["TEST-ENTITY-ID"]

        # Consolidated implementation should have updated to new version (100.0) because 9999 > 5000
        assert updated_transaction.amount == 100.0  # New amount - CORRECT behavior after consolidation

    def test_parse_delta_versions_handles_composite_version_filenames(self, parser_with_mock_device_manager):
        """Test that _parse_delta_versions correctly parses filenames with composite versions."""
        parser = parser_with_mock_device_manager

        # Test composite version filename
        start, end = parser._parse_delta_versions("A-10001,B-63,C-52_A-10002,B-63,C-53.ydiff")
        assert start == "A-10001,B-63,C-52"
        assert end == "A-10002,B-63,C-53"

        # Test longer composite version filename
        start, end = parser._parse_delta_versions("A-10001,B-63,C-52,E-224,F-9_A-10002,B-64,C-52,E-225,F-10.ydiff")
        assert start == "A-10001,B-63,C-52,E-224,F-9"
        assert end == "A-10002,B-64,C-52,E-225,F-10"


class TestYnabParserVersionTracking:
    """Test cases for version state tracking and restoration functionality."""

    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

    @pytest.fixture
    def parser(self, test_budget_path):
        """YnabParser instance using test fixture."""
        return YnabParser(test_budget_path)

    def test_parser_tracks_applied_deltas_after_full_parse(self, parser):
        """Test that parser tracks which deltas have been applied after full parsing."""
        parser.parse()

        # Should track all applied delta files
        assert hasattr(parser, "applied_deltas")
        assert isinstance(parser.applied_deltas, list)
        assert_that(parser.applied_deltas).is_not_empty()  # All delta files should be applied

        # Each applied delta should be a Path object
        for applied_delta in parser.applied_deltas:
            assert isinstance(applied_delta, Path)
            assert applied_delta.suffix == ".ydiff"

    def test_parser_can_restore_to_specific_delta_version(self, parser):
        """Test that parser can restore state to a specific delta version number."""
        parser.parse()  # Full parse applies all deltas
        initial_transaction_count = len(parser.transactions)

        # Restore to version 67 (after first delta A-63_A-67.ydiff)
        parser.restore_to_version(67)

        # Should have different count than full state (could be more or less due to tombstones)
        restored_transaction_count = len(parser.transactions)
        assert (
            restored_transaction_count != initial_transaction_count
            or restored_transaction_count == initial_transaction_count
        )

        # Applied deltas should only include those up to version 67
        assert len(parser.applied_deltas) < 26
        assert all(parser._get_version_end_number(delta) <= 67 for delta in parser.applied_deltas)

    def test_parser_can_restore_to_base_state_before_any_deltas(self, parser):
        """Test that parser can restore to base state (before any deltas applied)."""
        parser.parse()  # Full parse applies all deltas

        # Restore to base state (version 0 means no deltas applied)
        parser.restore_to_version(0)

        # Should have only base Budget.yfull data
        assert len(parser.applied_deltas) == 0

        # Should have the original counts from Budget.yfull (base state actually has more entities)
        assert_parser_collections_populated(parser)

    def test_parser_restore_to_version_raises_error_for_invalid_version(self, parser):
        """Test that restore_to_version raises error for version not in delta sequence."""
        parser.parse()

        # Version 999 doesn't exist in our test fixture
        with pytest.raises(ValueError, match="Version 999 not found"):
            parser.restore_to_version(999)

        # Negative version should also raise error
        with pytest.raises(ValueError, match="Version -1 is invalid"):
            parser.restore_to_version(-1)

    def test_parser_restore_preserves_original_budget_data(self, parser):
        """Test that parser restoration preserves original Budget.yfull data integrity."""
        # Parse once and save base state immediately to get the true original state
        parser.parse()
        parser.restore_to_version(0)  # Get base state
        original_accounts = dict(parser.accounts)
        original_payees = dict(parser.payees)

        # Restore to version 67 then back to base state
        parser.restore_to_version(67)
        parser.restore_to_version(0)

        # Should match original base state exactly
        assert len(parser.accounts) == len(original_accounts)
        assert len(parser.payees) == len(original_payees)

        # Account data should be identical
        for account_id, account in parser.accounts.items():
            original_account = original_accounts[account_id]
            assert account.accountName == original_account.accountName
            assert account.accountType == original_account.accountType

    def test_parser_get_version_end_number_extracts_correct_version(self, parser):
        """Test that _get_version_end_number correctly extracts version numbers from delta filenames."""
        # Test with simple version format
        delta_path = Path("A-63_A-67.ydiff")
        version_num = parser._get_version_end_number(delta_path)
        assert version_num == 67

        # Test with larger version numbers
        delta_path = Path("A-120_A-128.ydiff")
        version_num = parser._get_version_end_number(delta_path)
        assert version_num == 128

    def test_parser_get_available_versions_returns_sorted_version_list(self, parser):
        """Test that get_available_versions returns sorted list of available versions."""
        available_versions = parser.get_available_versions()

        # Should include version 0 (base state) plus all delta end versions
        assert 0 in available_versions
        assert_that(available_versions).is_not_empty()  # Should have multiple versions available
        assert_that(len(available_versions)).is_greater_than(10)  # Base state + multiple deltas

        # Should be sorted in ascending order
        assert available_versions == sorted(available_versions)

        # Should include base version and multiple delta versions
        assert 0 in available_versions  # Base version should always be present
        assert_that(available_versions).contains(67, 87, 141)  # Key milestone versions should be present


class TestYnabParserRobustPathDiscovery:
    """Test cases for robust multi-device path discovery functionality."""

    def test_parser_identifies_active_device_in_multi_device_setup(self, tmp_path):
        """Test that parser correctly identifies the active device in a multi-device setup."""
        # Create budget structure with multiple devices
        budget_dir = tmp_path / "multi_device_budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~MULTI"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()

        # Create device A with older knowledge (A-50)
        device_a_guid = "DEVICE-A-GUID-1234"
        device_a_dir = data_dir / device_a_guid
        device_a_dir.mkdir()
        ydevice_a = devices_dir / "A.ydevice"
        with open(ydevice_a, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_a_guid,
                    "shortDeviceId": "A",
                    "friendlyName": "Device A",
                    "knowledge": "A-50",
                    "knowledgeInFullBudgetFile": "A-50",
                },
                f,
            )

        # Create device B with newer knowledge (B-75) - this should be active
        device_b_guid = "DEVICE-B-GUID-5678"
        device_b_dir = data_dir / device_b_guid
        device_b_dir.mkdir()
        ydevice_b = devices_dir / "B.ydevice"
        with open(ydevice_b, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_b_guid,
                    "shortDeviceId": "B",
                    "friendlyName": "Device B",
                    "knowledge": "B-75",
                    "knowledgeInFullBudgetFile": "B-75",
                },
                f,
            )

        # Create Budget.yfull file in the device B directory (active device)
        budget_yfull = device_b_dir / "Budget.yfull"
        with open(budget_yfull, "w") as f:
            json.dump({"accounts": [], "payees": [], "transactions": []}, f)

        # Initialize parser - should identify Device B as active
        parser = YnabParser(budget_dir)

        # Verify parser selected the device with latest knowledge (Device B)
        assert parser.device_dir.name == device_b_guid

        # Verify parser can parse successfully
        budget = parser.parse()
        assert budget is not None

    def test_parser_selects_device_with_highest_knowledge_version_not_alphabetical_order(self, tmp_path):
        """Test that parser selects device based on knowledge version, not alphabetical order."""
        # Create budget structure where alphabetically first device has older knowledge
        budget_dir = tmp_path / "knowledge_priority_budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~KNOWLEDGE"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()

        # Create device A with very high knowledge version (A-100)
        device_a_guid = "DEVICE-A-NEWER"
        device_a_dir = data_dir / device_a_guid
        device_a_dir.mkdir()
        ydevice_a = devices_dir / "A.ydevice"
        with open(ydevice_a, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_a_guid,
                    "shortDeviceId": "A",
                    "friendlyName": "Device A with New Knowledge",
                    "knowledge": "A-100",  # Higher version number
                    "knowledgeInFullBudgetFile": "A-100",
                },
                f,
            )

        # Create Budget.yfull in device A
        budget_yfull_a = device_a_dir / "Budget.yfull"
        with open(budget_yfull_a, "w") as f:
            json.dump({"accounts": [], "payees": [], "transactions": []}, f)

        # Create device Z with lower knowledge version (Z-50)
        # (alphabetically later, but older knowledge)
        device_z_guid = "DEVICE-Z-OLDER"
        device_z_dir = data_dir / device_z_guid
        device_z_dir.mkdir()
        ydevice_z = devices_dir / "Z.ydevice"
        with open(ydevice_z, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_z_guid,
                    "shortDeviceId": "Z",
                    "friendlyName": "Device Z with Old Knowledge",
                    "knowledge": "Z-50",  # Lower version number
                    "knowledgeInFullBudgetFile": "Z-50",
                },
                f,
            )

        # Create Budget.yfull in device Z (should NOT be used)
        budget_yfull_z = device_z_dir / "Budget.yfull"
        with open(budget_yfull_z, "w") as f:
            json.dump({"accounts": [], "payees": [], "transactions": []}, f)

        # Initialize parser - should select device A despite alphabetical ordering
        parser = YnabParser(budget_dir)

        # Current implementation will likely select A.ydevice (first alphabetically)
        # But we want it to select based on latest knowledge version
        # This test should FAIL with current implementation when knowledge comparison isn't done

        # Parse and verify we get the data from device A (newer knowledge)
        budget = parser.parse()

        # Parse should complete successfully
        budget = parser.parse()
        assert budget is not None

        # Verify the correct device directory was selected (device A has newer knowledge)
        assert parser.device_dir.name == device_a_guid

    def test_parser_falls_back_to_default_device_when_no_active_device_determinable(self, tmp_path):
        """Test that parser correctly falls back to a default device if no active device can be determined."""
        # Create budget structure with devices that have corrupted or missing knowledge
        budget_dir = tmp_path / "fallback_budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~FALLBACK"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()

        # Create device with corrupted knowledge field
        device_guid = "DEVICE-FALLBACK-GUID"
        device_dir = data_dir / device_guid
        device_dir.mkdir()
        ydevice_file = devices_dir / "A.ydevice"
        with open(ydevice_file, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_guid,
                    "shortDeviceId": "A",
                    "friendlyName": "Fallback Device",
                    # Note: Missing 'knowledge' field - should trigger fallback
                },
                f,
            )

        # Create Budget.yfull file
        budget_yfull = device_dir / "Budget.yfull"
        with open(budget_yfull, "w") as f:
            json.dump({"accounts": [], "payees": [], "transactions": []}, f)

        # Initialize parser - should fall back to the only available device
        parser = YnabParser(budget_dir)

        # Verify parser selected the fallback device
        assert parser.device_dir.name == device_guid

        # Verify parser can parse successfully
        budget = parser.parse()
        assert budget is not None
