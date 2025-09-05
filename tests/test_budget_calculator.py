
import pytest
from pathlib import Path
from ynab_io.parser import YnabParser
from ynab_io.models import Budget

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

def test_budget_calculator_initialization(budget: Budget):
    """Tests that the BudgetCalculator can be initialized."""
    # This will fail until BudgetCalculator is implemented
    calculator = BudgetCalculator(budget)
    assert calculator.budget == budget
