from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class Account(BaseModel):
    model_config = ConfigDict(extra='ignore')
    entityId: str
    accountName: str
    accountType: str
    onBudget: bool
    sortableIndex: int
    hidden: bool
    entityVersion: str

class Payee(BaseModel):
    model_config = ConfigDict(extra='ignore')
    entityId: str
    name: str
    enabled: bool
    entityVersion: str

class Transaction(BaseModel):
    model_config = ConfigDict(extra='ignore')
    entityId: str
    accountId: str
    payeeId: Optional[str] = None
    amount: float
    date: str
    cleared: str
    accepted: bool
    entityVersion: str
    memo: Optional[str] = None

class Budget(BaseModel):
    accounts: List[Account]
    payees: List[Payee]
    transactions: List[Transaction]
