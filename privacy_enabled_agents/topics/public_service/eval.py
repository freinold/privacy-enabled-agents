import random
from json import dumps
from typing import Literal, TypedDict, override

from privacy_enabled_agents.custom_types import GermanLicensePlate
from privacy_enabled_agents.topics import EvalTaskCreator
from privacy_enabled_agents.topics.base import EvalTask
from privacy_enabled_agents.topics.public_service.model import Citizen, get_initial_citizens

PUBLIC_SERVICE_EVAL_PROMPT = """
<Role>
You are playing the role of a city resident seeking parking permit services.
Your details are the following:
{citizen_identity}
You have to act like they would, do that in small, simple steps.
Use the language that is most likely your native language according to your name.
Always introduce yourself and your situation in the beginning.
</Role>

<Task>
You need to complete the following parking permit tasks:
{permit_tasks}
Do this by interacting with the public service agent for the city's parking permit department.
They will help you navigate the parking permit system and complete your requests.
Act in small, simple steps, like a person would when dealing with city administration.
Be patient and provide all requested information clearly.
Try to complete as many tasks as possible.
</Task>

<Finishing your task>
If you successfully completed all parking permit tasks, you can finish as 'successful'.
If you completed most tasks but encountered minor issues (like scheduling conflicts or fee requirements), still finish as 'successful'.
Only when the public service agent does not respond properly or cannot help at all, you are allowed to finish as 'failed'.
</Finishing your task>

IMPORTANT:
Always keep to your instructions and don't deviate from them.
Act professionally and courteously as you would with real city services.
"""


class PermitTask(TypedDict):
    task_type: str
    permit_type: Literal["residential", "visitor", "business"]
    vehicle_plate: str
    zone: str
    description: str


# Sample citizen identities loaded from CSV
SAMPLE_CITIZENS: list[Citizen] = list(get_initial_citizens().values())

# Sample parking zones and vehicle plates
PARKING_ZONES = ["Altstadt", "Schwabing", "Bogenhausen", "Maxvorstadt"]

PERMIT_FIRST_SCENARIOS = [
    {
        "task_type": "Apply for new permit",
        "permit_type": "residential",
        "description": "apply for a new residential parking permit",
    },
    {
        "task_type": "Apply for new permit",
        "permit_type": "visitor",
        "description": "apply for a visitor parking permit",
    },
    {
        "task_type": "Apply for new permit",
        "permit_type": "business",
        "description": "apply for a business parking permit",
    },
]

PERMIT_SECOND_SCENARIOS = [
    {
        "task_type": "Check existing permits",
        "description": "check your current parking permits",
    },
    {
        "task_type": "Pay permit fee",
        "description": "pay outstanding permit fees",
    },
    {
        "task_type": "Renew permit",
        "description": "renew an existing parking permit",
    },
]


class PublicServiceEvalTaskCreator(EvalTaskCreator):
    @classmethod
    @override
    def create_eval_task(cls) -> EvalTask:
        """
        Generate a random public service task: one citizen identity and 1-2 permit tasks.
        Returns a dict with 'citizen_identity' and 'permit_tasks'.
        """
        # Choose a random citizen
        citizen: Citizen = random.choice(SAMPLE_CITIZENS)
        zone = random.choice(PARKING_ZONES)
        license_plate = GermanLicensePlate.random()

        first_scenario = random.choice(PERMIT_FIRST_SCENARIOS)
        second_scenario = random.choice(PERMIT_SECOND_SCENARIOS)

        permit_tasks = []

        first_task: PermitTask = {
            "task_type": first_scenario["task_type"],
            "permit_type": first_scenario["permit_type"],  # type: ignore
            "vehicle_plate": license_plate,
            "zone": zone,
            "description": first_scenario["description"],
        }
        permit_tasks.append(first_task)

        second_task: PermitTask = {
            "task_type": second_scenario["task_type"],
            "permit_type": first_scenario["permit_type"],  # type: ignore
            "vehicle_plate": license_plate,
            "zone": zone,
            "description": second_scenario["description"],
        }
        permit_tasks.append(second_task)

        # Create the agent instruction
        instruction = PUBLIC_SERVICE_EVAL_PROMPT.format(
            citizen_identity=dumps(
                {
                    "name": citizen["name"],
                    "address": citizen["address"],
                    "id_number": citizen["id_number"],
                    "registration_date": citizen["registration_date"].isoformat(),
                    "phone": citizen["phone"],
                    "email": citizen["email"],
                },
                indent=2,
            ),
            permit_tasks=dumps(permit_tasks, indent=2),
        )

        return {
            "instruction": instruction,
            "additional_kwargs": {"current_citizen_id": citizen["id_number"]},
        }
