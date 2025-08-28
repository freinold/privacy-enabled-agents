import csv
import random
from datetime import date, datetime, timedelta
from json import dumps
from pathlib import Path
from typing import TypedDict, override

from privacy_enabled_agents.custom_types.german_medical_insurance_id import GermanMedicalInsuranceID
from privacy_enabled_agents.topics import EvalTaskCreator
from privacy_enabled_agents.topics.base import EvalTask

MEDICAL_EVAL_PROMPT = """
<Role>
You are playing the role of a patient or family member seeking medical transportation services.
Your details are the following:
{patient_identity}
You have to act like they would, do that in small, simple steps.
Use the language that is most likely your native language according to your name.
Always introduce yourself and your situation in the beginning.
</Role>

<Task>
You need to complete the following medical transportation tasks:
{transport_tasks}
Do this by interacting with the medical transport service chat agent.
They will help you coordinate your medical transportation needs.
Act in small, simple steps, like a person would when dealing with medical services.
Be patient and provide all requested information clearly.
Try to complete as many tasks as possible.
</Task>

<Finishing your task>
If you successfully completed all transportation tasks, you can finish as 'successful'.
If you completed most tasks but encountered minor issues (like scheduling conflicts), still finish as 'successful'.
Only when the medical transport agent does not respond properly or cannot help at all, you are allowed to finish as 'failed'.
</Finishing your task>

IMPORTANT:
Always keep to your instructions and don't deviate from them.
Act professionally and courteously as you would with real medical services.
"""


class PatientIdentity(TypedDict):
    name: str
    date_of_birth: date
    medical_insurance_id: GermanMedicalInsuranceID
    current_address: str


class TransportTask(TypedDict):
    task_type: str
    destination_facility: str
    transport_datetime: datetime
    direction: str
    patient_location: str


def load_sample_patients() -> list[PatientIdentity]:
    """Load sample patients from CSV file in the data directory."""
    # Get the path to the CSV file relative to the project root
    project_root = Path(__file__).parent.parent.parent.parent
    csv_path = project_root / "data" / "medical_sample_patients.csv"

    patients = []
    with open(csv_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            patient = PatientIdentity(
                name=row["name"],
                date_of_birth=date.fromisoformat(row["date_of_birth"]),
                medical_insurance_id=GermanMedicalInsuranceID(row["medical_insurance_id"]),
                current_address=row["current_address"],
            )
            patients.append(patient)

    return patients


# Sample patient identities loaded from CSV
SAMPLE_PATIENTS: list[PatientIdentity] = load_sample_patients()

# Sample medical facilities and transport scenarios
MEDICAL_FACILITIES = [
    "Klinikum München",
    "München Klinik",
    "Hausarztpraxis München",
    "Facharztpraxis München",
]

TRANSPORT_SCENARIOS = [
    {
        "task_type": "Book appointment transport",
        "direction": "to_facility",
        "description": "regular medical appointment",
    },
    {
        "task_type": "Book return transport",
        "direction": "from_facility",
        "description": "return from medical procedure",
    },
    {
        "task_type": "Find nearby facilities",
        "direction": "to_facility",
        "description": "find closest medical facility and book transport",
    },
]


class MedicalEvalTaskCreator(EvalTaskCreator):
    @classmethod
    @override
    def create_eval_task(cls) -> EvalTask:
        """
        Generate a random medical task: one patient identity and 1-2 transportation tasks.
        Returns a dict with 'patient_identity' and 'transport_tasks'.
        """
        # Choose a random patient
        patient: PatientIdentity = random.choice(SAMPLE_PATIENTS)

        # Generate 1 transport task
        scenario = random.choice(TRANSPORT_SCENARIOS)
        facility = random.choice(MEDICAL_FACILITIES)

        # Generate a random future datetime (next 1-30 days)
        days_ahead = random.randint(1, 30)
        hours = random.randint(8, 17)  # Business hours
        minutes = random.choice([0, 15, 30, 45])  # Quarter hour intervals

        transport_datetime = datetime.now().replace(hour=hours, minute=minutes, second=0, microsecond=0) + timedelta(days=days_ahead)

        transport_task: TransportTask = {
            "task_type": scenario["task_type"],
            "destination_facility": facility,
            "transport_datetime": transport_datetime,
            "direction": scenario["direction"],
            "patient_location": patient["current_address"],
        }

        transport_tasks = [transport_task]

        # Create the agent instruction
        instruction = MEDICAL_EVAL_PROMPT.format(
            patient_identity=dumps(
                {
                    "name": patient["name"],
                    "date_of_birth": patient["date_of_birth"].isoformat(),
                    "medical_insurance_id": str(patient["medical_insurance_id"]),
                    "current_address": patient["current_address"],
                },
                indent=2,
            ),
            transport_tasks=dumps(
                [
                    {
                        **task,
                        "transport_datetime": task["transport_datetime"].isoformat(),
                    }
                    for task in transport_tasks
                ],
                indent=2,
            ),
        )

        return {
            "instruction": instruction,
            "additional_kwargs": {
                "patient_name": patient["name"],
                "patient_dob": patient["date_of_birth"],
                "medical_insurance_id": patient["medical_insurance_id"],
            },
        }
