from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Coordinate

from privacy_enabled_agents import PrivacyEnabledAgentState
from privacy_enabled_agents.custom_types.german_medical_insurance_id import GermanMedicalInsuranceID

MEDICAL_ENTITIES: set[str] = {
    "condition",
    "symptoms",
    "diagnosis",
    "treatment",
    "medication",
    "medical insurance id",
    "amount",
    "date",
    "age",
}


class MedicalContext(BaseModel):
    """Context for the medical agent."""

    city: str = Field(
        description="The city where the medical services are provided.",
        default="München",
    )


class MedicalFacility(BaseModel):
    """Model representing a medical facility."""

    name: str = Field(description="Name of the medical facility.")
    location: Coordinate = Field(description="Geographic coordinates of the medical facility.")
    type: Literal["hospital", "doctors office"] = Field(description="The type of the medical facility.")
    distance: float | None = Field(
        default=None,
        description="Distance from the user's location to the medical facility in kilometers.",
    )


class MedicalTransport(BaseModel):
    """Model representing a medical transport request."""

    transport_id: str = Field(description="Unique identifier for the medical transport request.")
    transport_pin: str = Field(
        description="A PIN code for the transport, used for security and verification purposes.",
        max_length=6,
        min_length=6,
    )
    start_location: Coordinate = Field(description="The starting location for the medical transport.")
    destination_location: Coordinate = Field(description="The destination location for the medical transport.")
    transport_datetime: str = Field(description="The date and time when the medical transport should take place.")
    patient_name: str = Field(description="The name of the patient who will be transported.")
    patient_dob: date = Field(description="The date of birth of the patient who will be transported.")
    patient_medical_insurance_id: GermanMedicalInsuranceID = Field(
        description="The German medical insurance ID of the patient who will be transported."
    )


def create_medical_facilities() -> list[MedicalFacility]:
    """Create a list of medical facilities in the service area."""
    return [
        MedicalFacility(
            name="Klinikum München",
            location=(48.1351, 11.582),  # type: ignore
            type="hospital",
        ),
        MedicalFacility(
            name="München Klinik",
            location=(48.1391, 11.5802),  # type: ignore
            type="hospital",
        ),
        MedicalFacility(
            name="Hausarztpraxis München",
            location=(48.1356, 11.5822),  # type: ignore
            type="doctors office",
        ),
        MedicalFacility(
            name="Facharztpraxis München",
            location=(48.1361, 11.5833),  # type: ignore
            type="doctors office",
        ),
    ]


class MedicalState(PrivacyEnabledAgentState):
    """State for the medical agent."""

    facilities: list[MedicalFacility] = Field(
        default_factory=create_medical_facilities,
        description="List of medical facilities in the service area.",
    )
    transports: list[MedicalTransport] = Field(
        default_factory=list,
        description="List of medical transport requests made by the user.",
    )
    transport_id_counter: int = Field(
        default=1,
        description="Counter for generating unique transport IDs.",
    )
