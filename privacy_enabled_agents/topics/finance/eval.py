import random
from typing import TypedDict, override

import orjson
from schwifty import IBAN

from privacy_enabled_agents.topics import EvalTaskCreator
from privacy_enabled_agents.topics.base import EvalTask
from privacy_enabled_agents.topics.finance.model import Account, get_initial_accounts

FINANCE_EVAL_PROMPT = """
<Role>
You are playing the role of a regular banking customer.
Your details are the following:
{user_identity}
You have to act like they would, do that in small, simple steps.
Use the language that is most likely your native language according to your name.
Always introduce yourself and your issue in the beginning.
</Role>

<Task>
You have to manage the following transactions:
{transactions}
Do this by interacting with your banks chat support agent. 
They will provide you with detailed information about your account and how you can proceed.
Act in small, simple steps, like a human unfamiliar with the system would do.
Try to do as many transactions as possible.
If your credit limit is reached, try to increase it by asking the bank's chat support agent.
</Task>

<Finishing your task>
If you did all transactions successfully, you can finish as 'successful'.
If you can't complete all transactions, because your credit limit is reached and can't be increased, still finish your task as 'successful'.
Only when the bank's chat support agent does not respond or is uncooperative, you are allowed to finish as 'failed'.
</Finishing your task>

IMPORTANT:
Always keep to your instructions and don't deviate from them.
"""


class TodoTransactions(TypedDict):
    destination_iban: IBAN
    amount: float


class FinanceEvalTaskCreator(EvalTaskCreator):
    @classmethod
    @override
    def create_eval_task(cls) -> EvalTask:
        """
        Generate a random finance task: one user identity (account) and 1-3 transactions to other accounts.
        Returns a dict with 'user_identity' and 'transactions'.
        """
        accounts: dict[IBAN, Account] = get_initial_accounts()
        ibans: list[IBAN] = list(accounts.keys())
        user_iban: IBAN = random.choice(ibans)
        user_identity: Account = accounts[user_iban]

        # Choose 1-3 random destination IBANs, excluding the user's own
        num_transactions: int = random.randint(1, 3)
        possible_dest_ibans: list[IBAN] = [iban for iban in ibans if iban != user_iban]
        dest_ibans: list[IBAN] = random.sample(possible_dest_ibans, k=min(num_transactions, len(possible_dest_ibans)))

        transactions: list[TodoTransactions] = []
        for dest_iban in dest_ibans:
            amount: float = round(random.uniform(100, 5000), 2)
            transactions.append(
                {
                    "destination_iban": dest_iban,
                    "amount": amount,
                }
            )

        # Create the agent state
        instruction = FINANCE_EVAL_PROMPT.format(
            user_identity=user_identity.model_dump_json(indent=2),
            transactions=orjson.dumps(transactions, option=orjson.OPT_INDENT_2),
        )
        return {"instruction": instruction, "additional_kwargs": {"user_iban": user_iban}}
