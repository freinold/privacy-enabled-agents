import random
from datetime import date, datetime
from functools import lru_cache
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field
from schwifty import IBAN

from privacy_enabled_agents import PrivacyEnabledAgentState

FINANCE_ENTITIES: set[str] = {
    "iban",
    "balance",
    "currency",
    "account_number",
    "amount",
    "date",
    "age",
}


class Account(BaseModel):
    balance: float
    currency: Literal["EUR"]
    iban: IBAN
    holder_name: str
    holder_age: int
    account_created: date
    credit_limit: float
    monthly_income: float


class Transfer(BaseModel):
    source_iban: IBAN
    destination_iban: IBAN
    amount: float
    timestamp: datetime


@lru_cache
def get_initial_accounts() -> dict[IBAN, Account]:
    accounts: pd.DataFrame = pd.read_csv(
        "data/finance_initial_accounts.csv",
    )
    return {
        IBAN(row["iban"]): Account(
            balance=row["balance"],
            currency=row["currency"],
            holder_name=row["holder_name"],
            holder_age=row["holder_age"],
            account_created=date.fromisoformat(row["account_created"]),
            credit_limit=row["credit_limit"],
            monthly_income=row["monthly_income"],
            iban=IBAN(row["iban"]),
        )
        for _, row in accounts.iterrows()
    }


class FinanceState(PrivacyEnabledAgentState):
    """State for the finance agent."""

    accounts: dict[IBAN, Account] = Field(
        default_factory=get_initial_accounts,
        description="A dictionary of accounts indexed by their IBANs.",
    )
    transfers: list[Transfer] = Field(
        default_factory=list,
        description="A list of transfers that have been made.",
    )
    user_iban: IBAN = Field(
        default_factory=lambda: random.choice(list(get_initial_accounts().keys())),
        description="The user's IBAN for the finance agent.",
    )
