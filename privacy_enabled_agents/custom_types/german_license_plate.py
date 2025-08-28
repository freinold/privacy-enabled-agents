import random
import re
import string
from typing import Self


class GermanLicensePlate(str):
    """Represents a 'naive' German license plate and provides methods for validation and serialization."""

    regex: re.Pattern[str] = re.compile(r"^[A-Z]{1,3}-[A-Z]{1,2}\d{1,4}$")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> Self:
        if not cls.regex.match(value):
            raise ValueError("invalid_german_license_plate", "Invalid German license plate format")
        return cls(value)

    @classmethod
    def random(cls) -> Self:
        handle_length: int = random.randint(1, 3)
        handle = "".join(random.choices(string.ascii_uppercase, k=handle_length))

        letters_length: int = random.randint(1, 2)
        letters = "".join(random.choices(string.ascii_uppercase, k=letters_length))

        numbers = random.randint(1, 9999)

        return cls(f"{handle}-{letters}{numbers}")
