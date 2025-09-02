from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class Account(BaseModel):
    entityId: str
    accountName: str
    accountType: str
    onBudget: bool
    sortableIndex: int
    hidden: bool
    lastReconciledDate: Optional[str] = None
    lastReconciledBalance: Optional[float] = None
    lastEnteredCheckNumber: Optional[int] = None
    entityVersion: str

    model_config = ConfigDict(extra='ignore')

class Payee(BaseModel):
    entityId: str
    name: str
    enabled: bool
    autoFillCategoryId: Optional[str] = None
    autoFillMemo: Optional[str] = None
    autoFillAmount: Optional[float] = None
    renameConditions: Optional[List] = None
    targetAccountId: Optional[str] = None
    locations: Optional[List] = None
    entityVersion: str

    model_config = ConfigDict(extra='ignore')

class Transaction(BaseModel):
    entityId: str
    accountId: str
    payeeId: Optional[str] = None
    categoryId: Optional[str] = None
    date: str
    amount: float
    cleared: str
    accepted: bool
    entityVersion: str

    model_config = ConfigDict(extra='ignore')
