
import pytest
from pathlib import Path
from ynab_io.parser import YnabParser
from ynab_io.models import Budget

from ynab_io.models import Budget, Account

# This will fail because BudgetCalculator does not exist yet
from ynab_io.budget_calculator import BudgetCalculator

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
        entityVersion="A-1"
    )
    budget.accounts.append(new_account)

    balance = calculator.get_account_balance("new-account")
    assert balance == (0, 0)

def test_get_account_balance_cleared_transactions(calculator: BudgetCalculator):
    """Tests that the balance is correct for an account with only cleared transactions."""
    # The credit card account has only cleared transactions in the test data
    balance = calculator.get_account_balance("AFBB4F1B-612E-EFEA-8ACE-1900155D83A7")
    assert balance[0] == 761.8
    assert balance[1] == 0

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
        entityVersion="A-1"
    )
    budget.accounts.append(new_account)

    from ynab_io.models import Transaction
    budget.transactions.append(Transaction(
        entityId="uncleared-1",
        accountId="uncleared-account",
        amount=100.0,
        date="2025-01-01",
        cleared="Uncleared",
        accepted=True,
        entityVersion="A-1"
    ))
    budget.transactions.append(Transaction(
        entityId="uncleared-2",
        accountId="uncleared-account",
        amount=-25.0,
        date="2025-01-02",
        cleared="Uncleared",
        accepted=True,
        entityVersion="A-1"
    ))

    balance = calculator.get_account_balance("uncleared-account")
    assert balance[0] == 0
    assert balance[1] == 75.0

def test_get_account_balance_mixed_transactions(calculator: BudgetCalculator):
    """Tests that the balance is correct for an account with mixed transactions."""
    # The "Current" account has a mix of cleared and uncleared transactions
    balance = calculator.get_account_balance("380A0C46-49AB-0FBA-3F63-FFAED8C529A1")
    assert balance[0] == 19421.7
    assert balance[1] == -1000.0
