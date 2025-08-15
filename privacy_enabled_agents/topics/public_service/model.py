from datetime import datetime
from typing import Literal, TypedDict

from pydantic import Field

from privacy_enabled_agents import PrivacyEnabledAgentState

PUBLIC_SERVICE_ENTITIES: set[str] = {
    "passport number",
    "permit_id",
    "vehicle_plate",
    "zone",
}


class Citizen(TypedDict):
    name: str
    address: str
    city_id: str
    registration_date: datetime
    phone: str
    email: str


class ParkingPermit(TypedDict):
    permit_id: str
    citizen_id: str
    permit_type: Literal["residential", "visitor", "business"]
    vehicle_plate: str
    start_date: datetime
    end_date: datetime
    status: Literal["active", "expired", "pending", "rejected"]
    fee_paid: bool
    zone: str
    annual_fee: float


def create_initial_citizens() -> dict[str, Citizen]:
    """Create initial citizen data."""
    return {
        "CIT001": {
            "name": "John Doe",
            "address": "123 Main Street",
            "city_id": "CIT001",
            "registration_date": datetime(2020, 1, 15),
            "phone": "+1-555-0123",
            "email": "john.doe@email.com",
        },
        "CIT002": {
            "name": "Jane Smith",
            "address": "456 Oak Avenue",
            "city_id": "CIT002",
            "registration_date": datetime(2019, 8, 22),
            "phone": "+1-555-0456",
            "email": "jane.smith@email.com",
        },
    }


def create_initial_parking_permits() -> dict[str, ParkingPermit]:
    """Create initial parking permit data."""
    return {
        "PP001": {
            "permit_id": "PP001",
            "citizen_id": "CIT001",
            "permit_type": "residential",
            "vehicle_plate": "ABC123",
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 12, 31),
            "status": "active",
            "fee_paid": True,
            "zone": "Zone A",
            "annual_fee": 120.0,
        },
        "PP002": {
            "permit_id": "PP002",
            "citizen_id": "CIT002",
            "permit_type": "business",
            "vehicle_plate": "XYZ789",
            "start_date": datetime(2025, 3, 1),
            "end_date": datetime(2026, 2, 28),
            "status": "active",
            "fee_paid": True,
            "zone": "Zone B",
            "annual_fee": 300.0,
        },
    }


class PublicServiceState(PrivacyEnabledAgentState):
    """State for the public service agent."""

    citizens: dict[str, Citizen] = Field(
        default_factory=create_initial_citizens,
        description="A dictionary of citizens indexed by their city IDs.",
    )
    parking_permits: dict[str, ParkingPermit] = Field(
        default_factory=create_initial_parking_permits,
        description="A dictionary of parking permits indexed by permit IDs.",
    )
    current_citizen_id: str = Field(
        default="CIT001",
        description="The current citizen's ID for the public service agent.",
    )
