from datetime import date

from ynab_io.models import Budget


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
