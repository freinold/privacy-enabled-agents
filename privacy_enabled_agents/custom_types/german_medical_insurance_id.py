from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema


class GermanMedicalInsuranceID(str):
    """Represents a german medical insurance ID and provides methods for validation and serialization."""

    @classmethod
    def __get_pydantic_core_schema(cls, sources: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Return a Pydantic CoreSchema with the german medical insurance ID validation.

        Args:
            source: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the german medical insurance ID validation.

        """
        return core_schema.with_info_before_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, __input_value: str, _: Any) -> str:
        """Validate a german medical insurance ID from the provided str value.

        Args:
            __input_value: The str value to be validated.
            _: The source type to be converted.

        Returns:
            The validated german medical insurance ID.

        Raises:
            PydanticCustomError: If the input is not a valid id.
        """
        cls.validate_german_medical_insurance_id(__input_value)
        return __input_value

    @staticmethod
    def validate_german_medical_insurance_id(value: str) -> None:
        """Validate a german medical insurance ID from the provided str value.

        Args:
            value: The str value to be validated.

        Raises:
            PydanticCustomError: If the input is not a valid id.
        """
        input_length = len(value)
        if input_length != 10:
            raise PydanticCustomError("german_medical_insurance_id_length", f"ID must be 10 characters long, not {input_length}")

        first_letter = value[0].upper()
        if not first_letter.isalpha():
            raise PydanticCustomError(
                "german_medical_insurance_id_invalid_characters", f"First character of ID must be a letter, not {first_letter}"
            )

        other_letters = value[1:]
        if not other_letters.isnumeric():
            raise PydanticCustomError(
                "german_medical_insurance_id_invalid_characters", "All characters of ID after the first must be numbers."
            )

        first_letter_value = ord(first_letter) - ord("A") + 1
        first_letter_value = f"{first_letter_value:02}"

        digits = [int(digit) for digit in first_letter_value + other_letters]
        checksum = digits.pop(-1)

        weights = [1, 2] * 5
        weighted_digits_sum = sum([digit * weight for digit, weight in zip(digits, weights)])

        calculated_checksum = weighted_digits_sum % 10
        if calculated_checksum != checksum:
            raise PydanticCustomError("german_medical_insurance_id_invalid_checksum", "Invalid ID checksum.")
