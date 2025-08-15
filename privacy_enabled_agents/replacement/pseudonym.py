from collections.abc import Callable, Sequence
from typing import Literal
from uuid import UUID

from faker import Faker

from privacy_enabled_agents import Entity
from privacy_enabled_agents.storage import BaseEntityStorage

from .base import BaseReplacer


class PseudonymReplacer(BaseReplacer):
    """
    Replacer that replaces entities with pseudonyms."
    """

    _supported_entities: set[str] | Literal["ANY"] = {
        "person",
        "email",
        "phone number",
        "address",
        "iban",
        "credit card number",
        "location",
    }

    def __init__(self, entity_storage: BaseEntityStorage, locale: str | Sequence[str] = "de_DE") -> None:
        super().__init__(entity_storage=entity_storage)
        self.faker = Faker(locale=locale)

        self.replacement_map: dict[str, Callable[[], str]] = {
            "person": lambda: self.faker.name(),
            "email": lambda: self.faker.email(),
            "phone number": lambda: self.faker.phone_number(),
            "address": lambda: self.faker.address(),
            "iban": lambda: self.faker.iban(),
            "credit card number": lambda: self.faker.credit_card_number(),
            "location": lambda: self.faker.city(),
        }

    def create_replacement(self, entity: Entity, thread_id: UUID) -> str:
        if entity.label not in self.replacement_map:
            raise ValueError(f"Unsupported entity type: {entity.label}")

        # Seed the faker instance with the context ID to ensure reproducibility as well as uniqueness between different contexts
        self.faker.seed_instance(thread_id.int)

        # Get the replacement function based on the entity label
        replacement_function: Callable[[], str] = self.replacement_map[entity.label]

        # Generate and return the replacement
        replacement: str = replacement_function()
        return replacement
