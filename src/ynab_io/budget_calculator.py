from collections.abc import Generator
from datetime import date

from ynab_io.models import Budget, MonthlyBudget, MonthlyCategoryBudget


class BudgetCalculator:
    def __init__(self, budget: Budget):
        self.budget = budget

    def get_account_balance(self, account_id: str) -> tuple[float, float]:
        """
        Calculate the account balance as (cleared_balance, uncleared_balance).

        This method excludes transactions from the current date (today) to ensure
        balance calculations are stable and don't include pending same-day transactions
        that may still be processing.

        Args:
            account_id: The unique identifier of the account

        Returns:
            A tuple of (cleared_balance, uncleared_balance) where:
            - cleared_balance: Sum of all Cleared/Reconciled transactions (excluding today)
            - uncleared_balance: Sum of all other transactions (excluding today)
        """
        cleared_balance = 0.0
        uncleared_balance = 0.0
        current_date = date.today().strftime("%Y-%m-%d")

        for transaction in self.budget.transactions:
            # Skip same-day transactions to avoid including pending/processing transactions
            if transaction.accountId == account_id and transaction.date != current_date:
                if transaction.cleared in ["Cleared", "Reconciled"]:
                    cleared_balance += transaction.amount
                else:
                    uncleared_balance += transaction.amount

        return cleared_balance, uncleared_balance

    def get_monthly_budget_summary(self, month: str) -> dict[str, dict[str, float]]:
        """
        Calculate the monthly budget summary showing budgeted amounts and outflows for each category.

        Args:
            month: Month in YYYY-MM format (e.g., "2025-08")

        Returns:
            Dictionary with category names as keys, each containing:
            - "budgeted": budgeted amount for the category
            - "outflow": total outflow (negative transactions) for the category
        """
        monthly_budget = self._find_monthly_budget(month)
        if not monthly_budget:
            return {}

        result = {}
        for mcb in self._get_category_budgets_for_month(monthly_budget.entityId):
            category_name = self._get_category_name(mcb.categoryId)
            if category_name:
                outflow = self._calculate_category_outflow(month, mcb.categoryId)
                result[category_name] = {"budgeted": mcb.budgeted, "outflow": outflow}

        return result

    def _find_monthly_budget(self, month: str) -> MonthlyBudget | None:
        """Find the monthly budget for the given month."""
        return next((mb for mb in self.budget.monthly_budgets if mb.month.startswith(month)), None)

    def _get_category_budgets_for_month(self, monthly_budget_id: str) -> Generator[MonthlyCategoryBudget, None, None]:
        """Get category budgets for a specific month that have positive budgeted amounts."""
        return (
            mcb
            for mcb in self.budget.monthly_category_budgets
            if mcb.parentMonthlyBudgetId == monthly_budget_id and mcb.budgeted > 0
        )

    def _get_category_name(self, category_id: str) -> str | None:
        """Get the name of a category by its ID."""
        return next((cat.name for cat in self.budget.categories if cat.entityId == category_id), None)

    def _calculate_category_outflow(self, month: str, category_id: str) -> float:
        """Calculate outflow for a category based on negative transactions in the specified month."""
        return sum(
            abs(txn.amount)
            for txn in self.budget.transactions
            if (txn.date.startswith(month) and txn.amount < 0 and txn.categoryId == category_id)
        )
