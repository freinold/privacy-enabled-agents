import random
from datetime import datetime
from typing import Literal, TypedDict

import pandas as pd
from pydantic import Field

from privacy_enabled_agents import PrivacyEnabledAgentState

PUBLIC_SERVICE_ENTITIES: set[str] = {
    "id number",
    "permit id",
    "vehicle plate",
    "parking zone",
}


class Citizen(TypedDict):
    name: str
    address: str
    id_number: str
    registration_date: datetime
    phone: str
    email: str


class ParkingPermit(TypedDict):
    permit_id: str
    citizen_id_number: str
    permit_type: Literal["residential", "visitor", "business"]
    vehicle_plate: str
    start_date: datetime
    end_date: datetime
    status: Literal["active", "expired", "pending", "rejected"]
    fee_paid: bool
    zone: str
    annual_fee: float


def get_initial_citizens() -> dict[str, Citizen]:
    """Load initial citizen data."""
    df = pd.read_csv("data/public_service_sample_citizens.csv")
    return {
        row["id_number"]: {
            "name": row["name"],
            "address": row["address"],
            "id_number": row["id_number"],
            "registration_date": pd.to_datetime(row["registration_date"]),
            "phone": row["phone"],
            "email": row["email"],
        }
        for _, row in df.iterrows()
    }


class PublicServiceState(PrivacyEnabledAgentState):
    """State for the public service agent."""

    citizens: dict[str, Citizen] = Field(
        default_factory=get_initial_citizens,
        description="A dictionary of citizens indexed by their city IDs.",
    )
    parking_permits: dict[str, ParkingPermit] = Field(
        default_factory=dict,
        description="A dictionary of parking permits indexed by permit IDs.",
    )
    current_citizen_id: str = Field(
        default_factory=lambda: random.choice(list(get_initial_citizens().values()))["id_number"],
        description="The current citizen's ID for the public service agent.",
    )
