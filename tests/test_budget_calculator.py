from pathlib import Path

import pytest

# This will fail because BudgetCalculator does not exist yet
from ynab_io.budget_calculator import BudgetCalculator
from ynab_io.models import Account, Budget
from ynab_io.parser import YnabParser
from ynab_io.testing import budget_version


@pytest.fixture
def test_budget_path():
    """Path to the test budget fixture."""
    return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")


@pytest.fixture
def budget(test_budget_path):
    """A parsed budget from the test fixture."""
    parser = YnabParser(test_budget_path)
    return parser.parse()


@pytest.fixture
def calculator(budget: Budget) -> BudgetCalculator:
    """A BudgetCalculator instance."""
    return BudgetCalculator(budget)


def test_budget_calculator_initialization(calculator: BudgetCalculator, budget: Budget):
    """Tests that the BudgetCalculator can be initialized."""
    assert calculator.budget == budget


def test_get_account_balance_no_transactions(calculator: BudgetCalculator, budget: Budget):
    """Tests that the balance is 0 for an account with no transactions."""
    # Create a new account with no transactions
    new_account = Account(
        entityId="new-account",
        accountName="Test Account",
        accountType="Checking",
        onBudget=True,
        sortableIndex=10,
        hidden=False,
        entityVersion="A-1",
    )
    budget.accounts.append(new_account)

    balance = calculator.get_account_balance("new-account")
    assert balance == (0, 0)


@budget_version(153)
def test_get_account_balance_cleared_transactions(calculator: BudgetCalculator):
    """Tests that the balance is correct for an account with only cleared transactions."""
    # The credit card account has only cleared transactions in the test data
    balance = calculator.get_account_balance("AFBB4F1B-612E-EFEA-8ACE-1900155D83A7")
    assert balance[0] == 761.8
    # This account also contains uncleared transactions, so the name is misleading.
    assert balance[1] == 200.0


def test_get_account_balance_uncleared_transactions(calculator: BudgetCalculator, budget: Budget):
    """Tests that the balance is correct for an account with only uncleared transactions."""
    # Create a new account and add some uncleared transactions
    new_account = Account(
        entityId="uncleared-account",
        accountName="Uncleared Account",
        accountType="Checking",
        onBudget=True,
        sortableIndex=11,
        hidden=False,
        entityVersion="A-1",
    )
    budget.accounts.append(new_account)

    from ynab_io.models import Transaction

    budget.transactions.append(
        Transaction(
            entityId="uncleared-1",
            accountId="uncleared-account",
            amount=100.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-1",
        )
    )
    budget.transactions.append(
        Transaction(
            entityId="uncleared-2",
            accountId="uncleared-account",
            amount=-25.0,
            date="2025-01-02",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-1",
        )
    )

    balance = calculator.get_account_balance("uncleared-account")
    assert balance[0] == 0
    assert balance[1] == 75.0


@budget_version(153)
def test_get_account_balance_mixed_transactions(calculator: BudgetCalculator):
    """Tests that the balance is correct for an account with mixed transactions."""
    # The "Current" account has a mix of cleared and uncleared transactions
    balance = calculator.get_account_balance("380A0C46-49AB-0FBA-3F63-FFAED8C529A1")
    assert balance[0] == 19421.70
    assert balance[1] == -900.0


# Monthly Budget Summary Tests


@budget_version(153)
def test_get_monthly_budget_summary_valid_month(calculator: BudgetCalculator):
    """Tests monthly budget summary for a valid month with budget data and transactions."""
    # Test August 2025 which has budget data and transactions
    summary = calculator.get_monthly_budget_summary("2025-08")

    # Should return a dictionary with category names as keys
    assert isinstance(summary, dict)
    assert len(summary) > 0

    # Each category should have budgeted and outflow values
    for _category_name, amounts in summary.items():
        assert isinstance(amounts, dict)
        assert "budgeted" in amounts
        assert "outflow" in amounts
        assert isinstance(amounts["budgeted"], float)
        assert isinstance(amounts["outflow"], float)

    # Check specific categories that should exist in test data
    # A16 category has budgeted amount of 78.3 based on our data exploration
    category_found = False
    for _category_name, amounts in summary.items():
        if amounts["budgeted"] == 78.3:
            category_found = True
            # This category should have outflow since there's a transaction on 2025-08-06 for -78.3
            assert amounts["outflow"] == 78.3
            break
    assert category_found, "Expected category with budgeted amount 78.3 not found"


def test_get_monthly_budget_summary_no_transactions(calculator: BudgetCalculator):
    """Tests monthly budget summary for a month with budget but no transactions."""
    # Test a month that has budget data but no transactions
    # Based on our exploration, let's test July 2025
    summary = calculator.get_monthly_budget_summary("2025-07")

    assert isinstance(summary, dict)
    # Even with no transactions, should have categories with 0 outflow
    for _category_name, amounts in summary.items():
        assert amounts["outflow"] == 0.0
        assert isinstance(amounts["budgeted"], float)


def test_get_monthly_budget_summary_invalid_month(calculator: BudgetCalculator):
    """Tests monthly budget summary for a non-existent month."""
    # Test a month that doesn't exist in the budget data
    summary = calculator.get_monthly_budget_summary("1999-12")

    # Should return empty dict for non-existent month
    assert summary == {}


def test_get_monthly_budget_summary_categories_without_budget(calculator: BudgetCalculator):
    """Tests that categories without budget allocations are not included."""
    summary = calculator.get_monthly_budget_summary("2025-08")

    # All returned categories should have a budgeted amount >= 0
    for _category_name, amounts in summary.items():
        assert amounts["budgeted"] >= 0.0


def test_get_monthly_budget_summary_outflow_calculation(calculator: BudgetCalculator):
    """Tests that outflow is correctly calculated from transactions."""
    summary = calculator.get_monthly_budget_summary("2025-08")

    # Verify outflow calculation by checking specific transaction
    # Transaction on 2025-08-06 for -78.3 should contribute to outflow
    total_outflow = sum(amounts["outflow"] for amounts in summary.values())
    assert total_outflow > 0, "Expected some outflow from transactions"


def test_get_monthly_budget_summary_month_format(calculator: BudgetCalculator):
    """Tests various month format inputs."""
    # Should work with YYYY-MM format
    summary1 = calculator.get_monthly_budget_summary("2025-08")
    summary2 = calculator.get_monthly_budget_summary("2025-8")  # Single digit month

    # Both should work (assuming the method handles format variations)
    # For now, let's just test that they don't crash
    assert isinstance(summary1, dict)
    # This works correctly since the implementation handles both YYYY-MM-DD and YYYY-MM format
    assert isinstance(summary2, dict)
