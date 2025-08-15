from datetime import datetime, timedelta
from random import random
from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import ArgsSchema, BaseTool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field

from .model import (
    Citizen,
    ParkingPermit,
    PublicServiceState,
)


class CheckParkingPermitsTool(BaseTool):
    """Tool to check the current citizen's parking permits."""

    name: str = "check_parking_permits"
    description: str = "Check all parking permits for the current citizen."
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(self, state: Annotated[PublicServiceState, InjectedState]) -> str:
        citizen_permits: list[ParkingPermit] = [
            permit for permit in state.parking_permits.values() if permit["citizen_id"] == state.current_citizen_id
        ]

        if not citizen_permits:
            return f"No parking permits found for citizen {state.current_citizen_id}."

        result: str = f"Parking permits for citizen {state.current_citizen_id}:\n"
        for permit in citizen_permits:
            result += (
                f"- Permit {permit['permit_id']}: {permit['permit_type']} permit for vehicle {permit['vehicle_plate']} "
                f"in {permit['zone']}, valid from {permit['start_date'].strftime('%Y-%m-%d')} to "
                f"{permit['end_date'].strftime('%Y-%m-%d')}, status: {permit['status']}\n"
            )

        return result


class ApplyParkingPermitInput(BaseModel):
    """Input schema for the apply_parking_permit tool."""

    permit_type: Literal["residential", "visitor", "business"] = Field(description="The type of parking permit to apply for.")
    vehicle_plate: str = Field(
        description="The license plate of the vehicle.",
        min_length=3,
        max_length=10,
    )
    zone: str = Field(description="The parking zone for the permit.", pattern="^Zone [A-Z]$")


class ApplyParkingPermitTool(BaseTool):
    """Tool to apply for a new parking permit."""

    name: str = "apply_parking_permit"
    description: str = "Apply for a new parking permit."
    args_schema: ArgsSchema | None = ApplyParkingPermitInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        permit_type: Literal["residential", "visitor", "business"],
        vehicle_plate: str,
        zone: str,
        state: Annotated[PublicServiceState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        citizen: Citizen | None = state.citizens.get(state.current_citizen_id)

        if not citizen:
            raise ValueError(f"Citizen {state.current_citizen_id} not found.")

        # Check if citizen already has an active permit for this vehicle
        existing_permit: ParkingPermit | None = next(
            (
                permit
                for permit in state.parking_permits.values()
                if permit["citizen_id"] == state.current_citizen_id
                and permit["vehicle_plate"] == vehicle_plate
                and permit["status"] == "active"
            ),
            None,
        )

        if existing_permit:
            raise ValueError(f"Active permit already exists for vehicle {vehicle_plate}.")

        # Check if citizen has been registered for at least 30 days
        if citizen["registration_date"] > datetime.now() - timedelta(days=30):
            raise ValueError("Citizen must be registered for at least 30 days to apply for a parking permit.")

        # Simulate application processing delay
        if random() < 0.1:
            raise ValueError("Application processing failed due to system error. Please try again later.")

        # Determine permit fee based on type
        permit_fees: dict[str, float] = {
            "residential": 120.0,
            "visitor": 50.0,
            "business": 300.0,
        }

        # Generate new permit ID
        permit_count: int = len(state.parking_permits)
        new_permit_id: str = f"PP{permit_count + 1:03d}"

        # Create new permit
        new_permit: ParkingPermit = {
            "permit_id": new_permit_id,
            "citizen_id": state.current_citizen_id,
            "permit_type": permit_type,
            "vehicle_plate": vehicle_plate,
            "start_date": datetime.now(),
            "end_date": datetime.now() + timedelta(days=365),
            "status": "pending",
            "fee_paid": False,
            "zone": zone,
            "annual_fee": permit_fees[permit_type],
        }

        state.parking_permits[new_permit_id] = new_permit

        return Command(
            update={
                "parking_permits": state.parking_permits,
                "messages": [
                    ToolMessage(
                        content=(
                            f"Parking permit application submitted successfully. "
                            f"Permit ID: {new_permit_id}, Annual fee: ${new_permit['annual_fee']:.2f}. "
                            f"Please pay the fee to activate the permit."
                        ),
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )


class PayParkingPermitFeeInput(BaseModel):
    """Input schema for the pay_parking_permit_fee tool."""

    permit_id: str = Field(description="The ID of the parking permit to pay for.")


class PayParkingPermitFeeTool(BaseTool):
    """Tool to pay the fee for a parking permit."""

    name: str = "pay_parking_permit_fee"
    description: str = "Pay the annual fee for a parking permit to activate it."
    args_schema: ArgsSchema | None = PayParkingPermitFeeInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        permit_id: str,
        state: Annotated[PublicServiceState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        permit: ParkingPermit | None = state.parking_permits.get(permit_id)

        if not permit:
            raise ValueError(f"Parking permit {permit_id} not found.")

        if permit["citizen_id"] != state.current_citizen_id:
            raise ValueError(f"Permit {permit_id} does not belong to current citizen.")

        if permit["fee_paid"]:
            raise ValueError(f"Fee for permit {permit_id} has already been paid.")

        if permit["status"] not in ["pending", "expired"]:
            raise ValueError(f"Cannot pay fee for permit {permit_id} with status {permit['status']}.")

        # Simulate payment processing
        if random() < 0.05:
            raise ValueError("Payment processing failed. Please try again later.")

        # Update permit status
        permit["fee_paid"] = True
        permit["status"] = "active"

        # If permit was expired, extend validity for another year
        if permit["status"] == "expired":
            permit["start_date"] = datetime.now()
            permit["end_date"] = datetime.now() + timedelta(days=365)

        state.parking_permits[permit_id] = permit

        return Command(
            update={
                "parking_permits": state.parking_permits,
                "messages": [
                    ToolMessage(
                        content=(
                            f"Payment of ${permit['annual_fee']:.2f} processed successfully for permit {permit_id}. "
                            f"Permit is now active and valid until {permit['end_date'].strftime('%Y-%m-%d')}."
                        ),
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )


class RenewParkingPermitInput(BaseModel):
    """Input schema for the renew_parking_permit tool."""

    permit_id: str = Field(description="The ID of the parking permit to renew.")


class RenewParkingPermitTool(BaseTool):
    """Tool to renew an existing parking permit."""

    name: str = "renew_parking_permit"
    description: str = "Renew an existing parking permit for another year."
    args_schema: ArgsSchema | None = RenewParkingPermitInput
    return_direct: bool = False
    response_format: Literal["content", "content_and_artifact"] = "content"

    def _run(
        self,
        permit_id: str,
        state: Annotated[PublicServiceState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        permit: ParkingPermit | None = state.parking_permits.get(permit_id)

        if not permit:
            raise ValueError(f"Parking permit {permit_id} not found.")

        if permit["citizen_id"] != state.current_citizen_id:
            raise ValueError(f"Permit {permit_id} does not belong to current citizen.")

        if permit["status"] not in ["active", "expired"]:
            raise ValueError(f"Cannot renew permit {permit_id} with status {permit['status']}.")

        # Check if permit is close to expiry (within 30 days) or already expired
        days_until_expiry: int = (permit["end_date"] - datetime.now()).days
        if days_until_expiry > 30 and permit["status"] == "active":
            raise ValueError(f"Permit {permit_id} can only be renewed within 30 days of expiry.")

        # Simulate renewal processing
        if random() < 0.05:
            raise ValueError("Renewal processing failed due to system error. Please try again later.")

        # Update permit dates and set to pending payment
        permit["start_date"] = permit["end_date"]  # Start from current end date
        permit["end_date"] = permit["start_date"] + timedelta(days=365)
        permit["status"] = "pending"
        permit["fee_paid"] = False

        state.parking_permits[permit_id] = permit

        return Command(
            update={
                "parking_permits": state.parking_permits,
                "messages": [
                    ToolMessage(
                        content=(
                            f"Parking permit {permit_id} renewed successfully. "
                            f"Annual fee: ${permit['annual_fee']:.2f}. "
                            f"Please pay the fee to activate the renewed permit."
                        ),
                        tool_call_id=tool_call_id,
                        status="success",
                    )
                ],
            }
        )
