import random
import string
from typing import Self


class GermanIDNumber(str):
    """A custom type representing a German ID number."""

    valid_letters: str = "CFGHJKLMNPRTVWXYZ"

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> Self:
        if len(value) != 9:
            raise ValueError("invalid_german_id_number_length", "German ID number must be 9 characters long")

        if value[0] not in cls.valid_letters:
            raise ValueError("invalid_german_id_number_format", "German ID number must start with a valid letter")

        for char in value[1:]:
            if char not in cls.valid_letters and not char.isdigit():
                raise ValueError("invalid_german_id_number_format", "German ID number must contain only allowed letters and digits")

        if not any(char.isdigit() for char in value[1:]):
            raise ValueError("invalid_german_id_number_format", "German ID number must contain at least one digit")

        return cls(value)

    @classmethod
    def random(cls) -> Self:
        first_char = random.choice(cls.valid_letters)
        other_chars = [random.choice(cls.valid_letters + string.digits) for _ in range(8)]

        if not any(char.isdigit() for char in other_chars):
            other_chars[random.randint(0, 7)] = random.choice(string.digits)

        return cls(f"{first_char}{''.join(other_chars)}")
