from ynab_io.models import Budget


class BudgetCalculator:
    def __init__(self, budget: Budget):
        self.budget = budget

    def get_account_balance(self, account_id: str) -> tuple[float, float]:
        cleared_balance = 0.0
        uncleared_balance = 0.0

        for transaction in self.budget.transactions:
            if transaction.accountId == account_id:
                if transaction.cleared in ["Cleared", "Reconciled"]:
                    cleared_balance += transaction.amount
                else:
                    uncleared_balance += transaction.amount

        return cleared_balance, uncleared_balance
