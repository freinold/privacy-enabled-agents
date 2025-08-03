from datetime import datetime, timedelta
from random import random
from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import ArgsSchema, BaseTool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field
from schwifty import IBAN

from privacy_enabled_agents.examples.finance.model import Account, FinanceState


class CheckBalanceTool(BaseTool):
    """Tool to check the balance of an account."""

    name: str = "check_balance"
    description: str = "Check the balance of an account."
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, state: Annotated[FinanceState, InjectedState]) -> str:
        account: Account | None = state.accounts.get(state.user_iban)

        if not account:
            raise ValueError(f"Account {state.user_iban} not found.")

        return f"Balance for account {state.user_iban}: {account['balance']} {account['currency']}."


class TransferMoneyInput(BaseModel):
    """Input schema for the transfer_money tool."""

    amount: float = Field(description="The amount of money to transfer.", ge=0.01)
    destination_iban: IBAN = Field(description="The IBAN of the account to transfer money to.")


class TransferMoneyTool(BaseTool):
    """Tool to transfer money from one account to another."""

    name: str = "transfer_money"
    description: str = "Transfer money from one account to another."
    args_schema: ArgsSchema | None = TransferMoneyInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        input: TransferMoneyInput,
        state: Annotated[FinanceState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        source_account: Account | None = state.accounts.get(state.user_iban)
        destination_account: Account | None = state.accounts.get(input.destination_iban)

        if not source_account:
            raise ValueError(f"Source account {state.user_iban} not found.")
        if not destination_account:
            raise ValueError(f"Destination account {input.destination_iban} not found.")

        if source_account["balance"] + source_account["credit_limit"] < input.amount:
            raise ValueError(f"Insufficient funds / credit in source account {state.user_iban}.")

        # Simulate a transfer delay
        if random() < 0.1:
            raise ValueError("Transfer failed due to a network error. Please try again later.")

        # Update balances
        source_account["balance"] -= input.amount
        destination_account["balance"] += input.amount

        # Log the transfer
        state.transfers.append(
            {
                "source_iban": state.user_iban,
                "destination_iban": input.destination_iban,
                "amount": input.amount,
                "timestamp": datetime.now(),
            }
        )

        state.accounts[state.user_iban] = source_account
        state.accounts[input.destination_iban] = destination_account

        return Command(
            update={
                "accounts": state.accounts,
                "transfers": state.transfers,
                "messages": [
                    ToolMessage(
                        content=f"Transferred {input.amount} from {state.user_iban} to {input.destination_iban}.",
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )


class IncreaseCreditLimitInput(BaseModel):
    """Input schema for the increase_credit_limit tool."""

    iban: IBAN = Field(description="The IBAN of the account to increase the credit limit for.")
    amount: float = Field(description="The amount to increase the credit limit by.", ge=0.01)


class IncreaseCreditLimitTool(BaseTool):
    """Tool to increase the credit limit of an account."""

    name: str = "increase_credit_limit"
    description: str = "Increase the credit limit of an account."
    args_schema: ArgsSchema | None = IncreaseCreditLimitInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        input: IncreaseCreditLimitInput,
        state: Annotated[FinanceState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        account: Account | None = state.accounts.get(input.iban)

        if not account:
            raise ValueError(f"Account {input.iban} not found.")

        # The account must be at least 30 days old to increase credit limit
        if account["account_created"] > datetime.now() - timedelta(days=30):
            raise ValueError(f"Account {input.iban} must be at least 30 days old to increase credit limit.")

        # The new credit limit must not exceed 10,000
        if account["credit_limit"] + input.amount > 10000:
            raise ValueError(f"Credit limit for account {input.iban} exceeded.")

        # The account holder must be at least 18 years old
        if account["holder_age"] < 18:
            raise ValueError(f"Account holder for {input.iban} must be at least 18 years old to increase credit limit.")

        # The new credit limit must not exceed the triple of the monthly income
        if account["monthly_income"] * 3 < account["credit_limit"] + input.amount:
            raise ValueError(f"Insufficient income to increase credit limit for account {input.iban}.")

        # If all checks pass, increase the credit limit
        account["credit_limit"] += input.amount
        state.accounts[input.iban] = account

        return Command(
            update={
                "accounts": state.accounts,
                "messages": [
                    ToolMessage(
                        content=f"Credit limit for account {input.iban} increased by {input.amount} to {account['credit_limit']}.",
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )
