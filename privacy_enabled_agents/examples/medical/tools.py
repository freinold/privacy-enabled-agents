from datetime import date, datetime
from functools import lru_cache
from random import randint
from typing import Annotated, Any, Generator, Literal

from geopy import Location
from geopy.distance import distance
from geopy.geocoders import Nominatim
from langchain_core.messages import ToolMessage
from langchain_core.tools import ArgsSchema, BaseTool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.runtime import get_runtime
from langgraph.types import Command
from phonenumbers import PhoneNumber
from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Coordinate
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from privacy_enabled_agents.custom_types.german_medical_insurance_id import (
    GermanMedicalInsuranceID,
)
from privacy_enabled_agents.examples.medical.agent import MedicalContext
from privacy_enabled_agents.examples.medical.model import (
    MedicalFacility,
    MedicalState,
    MedicalTransport,
)

GermanPhoneNumber = Annotated[
    str | PhoneNumber,
    PhoneNumberValidator(supported_regions=["DE"], default_region="DE"),
]


@lru_cache
def get_nominatim_geocoder() -> Nominatim:
    return Nominatim(user_agent="privacy_enabled_agents")


class GetCoordinateFromAddressInput(BaseModel):
    """Input schema for the get_coordinate_from_address tool."""

    address: str = Field(description="The coordinate to get the location for.")


class GetCoordinateFromAdressTool(BaseTool):
    """Tool to get the coordinate for a given address."""

    name: str = "get_coordinate_from_address"
    description: str = "Get the coordinate for a given address."
    args_schema: ArgsSchema | None = GetCoordinateFromAddressInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, input: GetCoordinateFromAddressInput) -> Coordinate:
        geocoder: Nominatim = get_nominatim_geocoder()
        location: Location | None = geocoder.geocode(input.address)  # type: ignore
        if location:
            return Coordinate(
                latitude=location.latitude,
                longitude=location.longitude,
            )
        raise ValueError("Could not find coordinates for address.")


class CheckServiceAreaInput(BaseModel):
    """Input schema for the check_service_area tool."""

    location: Coordinate = Field(description="The location which is to be checked if it is in the service area.")


class CheckServiceAreaTool(BaseTool):
    """Tool to check if a given location is in the service area."""

    name: str = "check_service_area"
    description: str = "Check if a given location is in the service area."
    args_schema: ArgsSchema | None = CheckServiceAreaInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, input: CheckServiceAreaInput) -> bool:
        geocoder: Nominatim = get_nominatim_geocoder()
        context: MedicalContext = get_runtime(MedicalContext).context

        location: Location | None = geocoder.reverse(
            query=(input.location.latitude, input.location.longitude),
            exactly_one=True,
        )  # type: ignore
        if location:
            return context.city in location.address
        raise ValueError("Could not find location for coordinates.")


class FindNearbyMedicalFacilitiesInput(BaseModel):
    """Input schema for the find_nearby_medical_facilities tool."""

    location: Coordinate = Field(
        description="The location as a pair of latitude and longitude coordinates to search for medical facilities."
    )


class FindNearbyMedicalFacilitiesTool(BaseTool):
    """Tool to find nearby medical facilities like hospitals, doctors offices, or pharmacies."""

    name: str = "find_nearby_medical_facilities"
    description: str = "Find nearby medical facilities like hospital or doctors office."
    args_schema: ArgsSchema | None = FindNearbyMedicalFacilitiesInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        input: FindNearbyMedicalFacilitiesInput,
        state: Annotated[MedicalState, InjectedState],
    ) -> list[MedicalFacility]:
        facilities: list[MedicalFacility] = state.facilities
        nearby_facilities: list[MedicalFacility] = []
        for facility in facilities:
            facility_distance: float = distance(
                (input.location.latitude, input.location.longitude),
                (facility.location.latitude, facility.location.longitude),
            ).km
            if facility_distance <= 10:
                nearby_facilities.append(facility)
        return sorted(
            nearby_facilities,
            key=lambda x: x.distance or float("inf"),
        )


class BookMedicalTransportInput(BaseModel):
    """Input schema for the book_medical_transport tool."""

    location: Coordinate = Field(description="The location of the medical transport as a pair of latitude and longitude coordinates.")
    facility: str = Field(
        description="The facility name where the medical transport should go to / from.",
    )
    transport_direction: Literal["to_facility", "from_facility"] = Field(description="The direction of the medical transport.")
    transport_datetime: datetime = Field(description="The date and time when the medical transport should take place.")
    patient_name: str = Field(description="The name of the patient who will be transported.")
    patient_dob: date = Field(description="The date of birth of the patient who will be transported.")
    patient_medical_insurance_id: GermanMedicalInsuranceID = Field(
        description="The german medical insurance ID of the patient who will be transported."
    )


class BookMedicalTransportTool(BaseTool):
    """Tool to book a medical transport to a hospital, doctors office, or other medical facility."""

    name: str = "book_medical_transport"
    description: str = "Book a medical transport to a hospital or doctors office."
    args_schema: ArgsSchema | None = BookMedicalTransportInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        input: BookMedicalTransportInput,
        state: Annotated[MedicalState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        facilities: list[MedicalFacility] = state.facilities

        facility = next(
            (f for f in facilities if f.name == input.facility),
            None,
        )

        if facility is None:
            raise ValueError(f"Facility '{input.facility}' not found in the service area.")

        if input.transport_direction == "to_facility":
            start_location: Coordinate = input.location
            destination_location: Coordinate = facility.location
        else:
            start_location: Coordinate = facility.location
            destination_location: Coordinate = input.location

        # Create a new random transport PIN
        transport_pin: str = f"{randint(0, 999999):06d}"
        transport_id: str = f"TR{state.transport_id_counter:04d}"
        state.transport_id_counter += 1

        transport = MedicalTransport(
            transport_id=transport_id,
            transport_pin=transport_pin,
            start_location=start_location,
            destination_location=destination_location,
            transport_datetime=input.transport_datetime.isoformat(),
            patient_name=input.patient_name,
            patient_dob=input.patient_dob,
            patient_medical_insurance_id=input.patient_medical_insurance_id,
        )

        state.transports.append(transport)
        return Command(
            update={
                "transports": state.transports,
                "transport_id_counter": state.transport_id_counter,
                "messages": [
                    ToolMessage(
                        content=f"Medical transport booked successfully! Transport PIN: {transport_pin}",
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )


class ListMedicalTransportsInput(BaseModel):
    """Input schema for the list_medical_transports tool."""

    patient_medical_insurance_id: GermanMedicalInsuranceID = Field(
        description="The german medical insurance ID of the patient who will be transported."
    )
    patient_dob: date = Field(description="The date of birth of the patient who will be transported.")


class ListMedicalTransportsTool(BaseTool):
    """Tool to list all medical transports for a given patient."""

    name: str = "list_medical_transports"
    description: str = "List all medical transports for a given patient."
    args_schema: ArgsSchema | None = ListMedicalTransportsInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, input: ListMedicalTransportsInput, state: Annotated[MedicalState, InjectedState]) -> list[dict[str, Any]]:
        transports: Generator = (
            t
            for t in state.transports
            if t.patient_medical_insurance_id == input.patient_medical_insurance_id and t.patient_dob == input.patient_dob
        )
        transports = (t.model_dump().pop("transport_pin") for t in transports)
        return list(transports)


class CancelMedicalTransportInput(BaseModel):
    """Input schema for the cancel_medical_transport tool."""

    transport_id: str = Field(description="The unique identifier for the medical transport to cancel.")
    transport_pin: str = Field(
        description="The PIN code for the transport, used for security and verification purposes.",
        max_length=6,
        min_length=6,
    )


class CancelMedicalTransportTool(BaseTool):
    """Tool to cancel a medical transport for a given patient."""

    name: str = "cancel_medical_transport"
    description: str = "Cancel a medical transport for a given patient."
    args_schema: ArgsSchema | None = CancelMedicalTransportInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        input: CancelMedicalTransportInput,
        state: Annotated[MedicalState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        transport: MedicalTransport | None = next((t for t in state.transports if t.transport_id == input.transport_id), None)
        if not transport:
            raise ValueError(f"Transport with ID {input.transport_id} not found.")

        if transport.transport_pin != input.transport_pin:
            raise ValueError("Invalid transport PIN provided.")

        state.transports.remove(transport)
        return Command(
            update={
                "transports": state.transports,
                "messages": [
                    ToolMessage(
                        content="Medical transport canceled successfully.",
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )
