from typing import Callable, Sequence

from faker import Faker

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.replacement.base import BaseReplacer
from privacy_enabled_agents.storage.base import BaseStorage


class PseudonymReplacer(BaseReplacer):
    """
    Replacer that replaces entities with pseudonyms."
    """

    _supported_entities = ["person", "email", "phone number", "adress", "iban", "credit card number", "location"]

    def __init__(self, storage: BaseStorage, locale: str | Sequence[str] = "de_DE") -> None:
        super().__init__(storage)
        self.faker = Faker(locale=locale)
        self.faker.seed_instance(0)

        self.replacement_map: dict[str, Callable[None, str]] = {
            "person": self.faker.name,
            "email": self.faker.email,
            "phone number": self.faker.phone_number,
            "address": self.faker.address,
            "iban": self.faker.iban,
            "credit card number": self.faker.credit_card_number,
            "location": self.faker.city,
        }

    def create_replacement(self, entity: Entity) -> str:
        if entity.label not in self.replacement_map:
            raise ValueError(f"Unsupported entity type: {entity.label}")

        # Get the replacement function based on the entity label
        replacement_function = self.replacement_map[entity.label]
        # Generate the replacement value
        replacement = replacement_function()
        return replacement
