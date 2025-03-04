from datetime import date
from typing import Annotated, Any, Type, Union

from langchain_core.tools import BaseTool
from phonenumbers import PhoneNumber
from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Coordinate
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from src.custom_types.german_medical_insurance_id import GermanMedicalInsuranceID

GermanPhoneNumber = Annotated[Union[str, PhoneNumber], PhoneNumberValidator(supported_regions=["DE"], default_region="DE")]


class GetCoordinateFromAdressInput(BaseModel):
    """Input schema for the get_coordinate_from_address tool."""

    address: str = Field(description="The coordinate to get the location for.")


class GetCoordinateFromAdressTool(BaseTool):
    """Tool to get the coordinate for a given address."""

    name: str = "get_coordinate_from_address"
    description: str = "Get the coordinate for a given address."
    args_schema: Type[BaseModel] = GetCoordinateFromAdressInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: GetCoordinateFromAdressInput) -> tuple[str, list[Any]]:
        return "Coordinate found!", [None]  # TODO: Implement this tool


class CheckLocationInServiceAreaInput(BaseModel):
    """Input schema for the check_coordinate_in_service_area tool."""

    location: Coordinate = Field(description="The location to check for if it is in the service area.")


class CheckCoordinateInServiceAreaTool(BaseTool):
    """Tool to check if a given location is in the service area."""

    name: str = "check_coordinate_in_service_area"
    description: str = "Check if a given location is in the service area."
    args_schema: Type[BaseModel] = CheckLocationInServiceAreaInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: CheckLocationInServiceAreaInput) -> tuple[str, list[Any]]:
        return "Location is in the service area!", [None]  # TODO: Implement this tool


class FindNearbyMedicalFacilitiesInput(BaseModel):
    """Input schema for the find_nearby_medical_facilities tool."""

    location: Coordinate = Field(
        description="The location as a pair of latitude and longitude coordinates to search for medical facilities."
    )


class FindNearbyMedicalFacilitiesTool(BaseTool):
    """Tool to find nearby medical facilities like hospitals, doctors offices, or pharmacies."""

    name: str = "find_nearby_medical_facilities"
    description: str = "Find nearby medical facilities like hospitals, doctors offices, or pharmacies."
    args_schema: Type[BaseModel] = FindNearbyMedicalFacilitiesInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: FindNearbyMedicalFacilitiesInput) -> tuple[str, list[Any]]:
        return "Medical facilities listed!", [None]  # TODO: Implement this tool


class BookMedicalTransportInput(BaseModel):
    """Input schema for the book_medical_transport tool."""

    start_location: Coordinate = Field(
        description="The starting location of the medical transport as a pair of latitude and longitude coordinates."
    )
    destination_location: Coordinate = Field(
        description="The destination location of the medical transport as a pair of latitude and longitude coordinates."
    )
    patient_name: str = Field(description="The name of the patient who will be transported.")
    patient_surname: str = Field(description="The surname of the patient who will be transported.")
    patient_dob: date = Field(description="The date of birth of the patient who will be transported.")
    patient_medical_insurance_id: GermanMedicalInsuranceID = Field(
        description="The german medical insurance ID of the patient who will be transported."
    )
    patient_phone_number: GermanPhoneNumber = Field(description="The phone number of the patient who will be transported.")
    patient_email: str = Field(description="The email of the patient who will be transported.")
    patient_special_needs: list[str] = Field(description="Any special needs the patient has.")


class BookMedicalTransportTool(BaseTool):
    """Tool to book a medical transport to a hospital, doctors office, or other medical facility."""

    name: str = "book_medical_transport"
    description: str = "Book a medical transport to a hospital, doctors office, or other medical facility."
    args_schema: Type[BaseModel] = BookMedicalTransportInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components: # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: BookMedicalTransportInput) -> tuple[str, list[Any]]:
        return "Medical transport booked!", [None]  # TODO: Implement this tool


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
    args_schema: Type[BaseModel] = ListMedicalTransportsInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: ListMedicalTransportsInput) -> tuple[str, list[Any]]:
        return "Medical transports listed!", [None]  # TODO: Implement this tool


class CancelMedicalTransportInput(BaseModel):
    """Input schema for the cancel_medical_transport tool."""

    patient_medical_insurance_id: GermanMedicalInsuranceID = Field(
        description="The german medical insurance ID of the patient who will be transported."
    )
    patient_dob: date = Field(description="The date of birth of the patient who will be transported.")
    transport_id: str = Field(description="The ID of the transport to cancel.")


class CancelMedicalTransportTool(BaseTool):
    """Tool to cancel a medical transport for a given patient."""

    name: str = "cancel_medical_transport"
    description: str = "Cancel a medical transport for a given patient."
    args_schema: Type[BaseModel] = CancelMedicalTransportInput
    return_direct: bool = False
    response_format: str = "content_and_artifact"  # Artifact can not be seen by the model, but is available to the other chain components

    def _run(self, input: CancelMedicalTransportInput) -> tuple[str, list[Any]]:
        return "Medical transport canceled!", [None]  # TODO: Implement this tool
