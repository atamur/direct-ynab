from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any


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
    payeeId: Optional[str] = None
    amount: float
    date: str
    cleared: str
    accepted: bool
    entityVersion: str
    memo: Optional[str] = None


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
    cachedBalance: Optional[Any] = None


class MonthlyBudget(BaseModel):
    """Monthly budget data for a specific month."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    month: str
    entityVersion: str
    monthlySubCategoryBudgets: Optional[List[Any]] = None


class MonthlyCategoryBudget(BaseModel):
    """Monthly category budget allocation within a specific month."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    entityVersion: str
    categoryId: str
    parentMonthlyBudgetId: str
    budgeted: float
    overspendingHandling: Optional[str] = None
    note: Optional[str] = None


class ScheduledTransaction(BaseModel):
    """Recurring/scheduled transaction in YNAB4."""

    model_config = ConfigDict(extra="ignore")
    entityId: str
    frequency: str
    amount: float
    entityVersion: str
    payeeId: Optional[str] = None
    accountId: Optional[str] = None
    date: Optional[str] = None


class Budget(BaseModel):
    accounts: List[Account]
    payees: List[Payee]
    transactions: List[Transaction]
    master_categories: List[MasterCategory]
    categories: List[Category]
    monthly_budgets: List[MonthlyBudget]
    monthly_category_budgets: List[MonthlyCategoryBudget]
    scheduled_transactions: List[ScheduledTransaction]
