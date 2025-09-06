from typing import Any

from pydantic import BaseModel, ConfigDict


class Account(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entityId: str
    accountName: str
    accountType: str
    onBudget: bool
    sortableIndex: int
    hidden: bool
    entityVersion: str


class Payee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entityId: str
    name: str
    enabled: bool
    entityVersion: str


class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entityId: str
    accountId: str
    payeeId: str | None = None
    amount: float
    date: str
    cleared: str
    accepted: bool
    entityVersion: str
    memo: str | None = None


class MasterCategory(BaseModel):
    """Master category (category group) in YNAB4."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    name: str
    type: str
    deleteable: bool
    expanded: bool
    sortableIndex: int
    entityVersion: str


class Category(BaseModel):
    """Individual budget category within a master category."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    name: str
    type: str
    masterCategoryId: str
    sortableIndex: int
    entityVersion: str
    cachedBalance: Any | None = None


class MonthlyBudget(BaseModel):
    """Monthly budget data for a specific month."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    month: str
    entityVersion: str
    monthlySubCategoryBudgets: list[Any] | None = None


class MonthlyCategoryBudget(BaseModel):
    """Monthly category budget allocation within a specific month."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    entityVersion: str
    categoryId: str
    parentMonthlyBudgetId: str
    budgeted: float
    overspendingHandling: str | None = None
    note: str | None = None


class ScheduledTransaction(BaseModel):
    """Recurring/scheduled transaction in YNAB4."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    frequency: str
    amount: float
    entityVersion: str
    payeeId: str | None = None
    accountId: str | None = None
    date: str | None = None


class Budget(BaseModel):
    accounts: list[Account]
    payees: list[Payee]
    transactions: list[Transaction]
    master_categories: list[MasterCategory]
    categories: list[Category]
    monthly_budgets: list[MonthlyBudget]
    monthly_category_budgets: list[MonthlyCategoryBudget]
    scheduled_transactions: list[ScheduledTransaction]
