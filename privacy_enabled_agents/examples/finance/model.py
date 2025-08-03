from datetime import datetime
from typing import TypedDict

from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic
from pydantic import Field


class Account(TypedDict):
    balance: float
    currency: str
    holder_name: str
    holder_age: int
    account_created: datetime
    credit_limit: float
    monthly_income: float


class Transfer(TypedDict):
    source_iban: str
    destination_iban: str
    amount: float
    timestamp: datetime


def create_initial_accounts() -> dict[str, Account]:
    # TODO: Enhance this with more realistic data or a database connection
    return {
        "DE89370400440532013000": {
            "balance": 1000.0,
            "currency": "EUR",
            "holder_name": "Alice Smith",
            "holder_age": 30,
            "account_created": datetime(2020, 1, 1),
            "credit_limit": 5000.0,
            "monthly_income": 3000.0,
        }
    }


class FinanceState(AgentStatePydantic):
    """State for the finance agent."""

    accounts: dict[str, Account] = Field(
        default_factory=create_initial_accounts,
        description="A dictionary of accounts indexed by their IBANs.",
    )
    transfers: list[Transfer] = Field(
        default_factory=list,
        description="A list of transfers that have been made.",
    )
    user_iban: str = Field(
        default="DE89370400440532013000",  # TODO: Pick a random IBAN from the accounts
        description="The user's IBAN for the finance agent.",
    )
