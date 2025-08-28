import random
import string
from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema


class GermanMedicalInsuranceID(str):
    """Represents a german medical insurance ID and provides methods for validation and serialization."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[Any], handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Return a Pydantic CoreSchema with the german medical insurance ID validation.

        Args:
            source: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the german medical insurance ID validation.

        """
        return core_schema.with_info_before_validator_function(
            function=cls._validate,
            schema=core_schema.str_schema(),
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
        input_length: int = len(value)
        if input_length != 10:
            raise PydanticCustomError(
                error_type="german_medical_insurance_id_length",
                message_template="ID must be 10 characters long, not {value}",
                context={"value": value},
            )

        first_letter: str = value[0].upper()
        if not first_letter.isalpha():
            raise PydanticCustomError(
                error_type="german_medical_insurance_id_invalid_characters",
                message_template="First character of ID must be a letter, not {value}",
                context={"value": first_letter},
            )

        other_letters: str = value[1:]
        if not other_letters.isnumeric():
            raise PydanticCustomError(
                error_type="german_medical_insurance_id_invalid_characters",
                message_template="All characters of ID after the first must be numbers, not {value}",
                context={"value": other_letters},
            )

        first_letter_value: int | str = ord(first_letter) - ord("A") + 1
        first_letter_value = f"{first_letter_value:02}"

        digits: list[int] = [int(digit) for digit in first_letter_value + other_letters]
        checksum: int = digits.pop(-1)

        weights: list[int] = [1, 2] * 5
        weighted_digits_sum: int = sum([digit * weight for digit, weight in zip(digits, weights)])

        calculated_checksum: int = weighted_digits_sum % 10
        if calculated_checksum != checksum:
            raise PydanticCustomError(
                error_type="german_medical_insurance_id_invalid_checksum",
                message_template="Invalid ID checksum {calculated_checksum}, expected {checksum}",
                context={"calculated_checksum": calculated_checksum, "checksum": checksum},
            )

    @classmethod
    def random(cls) -> Self:
        """Generate a random valid German medical insurance ID.

        Returns:
            A new instance with a randomly generated valid insurance ID.
        """
        # Generate random first letter
        first_letter = random.choice(string.ascii_uppercase)

        # Generate 8 random digits (9th digit will be the checksum)
        other_digits = "".join(random.choices(string.digits, k=8))

        # Calculate checksum
        first_letter_value = ord(first_letter) - ord("A") + 1
        first_letter_value_str = f"{first_letter_value:02}"

        # Combine first letter value and the 8 random digits
        digits = [int(digit) for digit in first_letter_value_str + other_digits]

        # Calculate weighted sum for checksum
        weights = [1, 2] * 5  # alternating 1, 2 pattern for 10 positions
        weighted_digits_sum = sum([digit * weight for digit, weight in zip(digits, weights)])

        # Calculate checksum
        checksum = weighted_digits_sum % 10

        # Create the complete ID
        random_id = first_letter + other_digits + str(checksum)
        return cls(random_id)
