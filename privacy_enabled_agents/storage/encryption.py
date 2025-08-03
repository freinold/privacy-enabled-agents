from collections.abc import Iterator
from uuid import UUID

from cryptography.fernet import Fernet

from privacy_enabled_agents.storage.base import BaseStorage


class EncryptionStorage(BaseStorage):
    """Mock encryption storage class because data is encrypted in the replacement instead of stored."""

    def __init__(self):
        self._storage: dict[UUID, list[str]] = {}

    def put(self, text: str, label: str, replacement: str, context_id: UUID) -> None:
        raise NotImplementedError("EncryptionStorage does not support put operation.")

    def inc_label_counter(self, label: str, context_id: UUID) -> int:
        raise NotImplementedError("EncryptionStorage does not support inc_label_counter operation.")

    def get_text(self, replacement: str, context_id: UUID) -> tuple[str, str]:
        # Create a fernet object using the context_id as key
        fernet = Fernet(key=context_id.bytes)
        # Decrypt the replacement text
        decrypted_text = fernet.decrypt(replacement.encode())
        # Find the label in the storage
        return decrypted_text.decode(), "unknown"

    def get_replacement(self, text: str, context_id: UUID) -> str:
        # Create a fernet object using the context_id as key
        fernet = Fernet(key=context_id.bytes)
        # Encrypt the text
        encrypted_text: bytes = fernet.encrypt(text.encode())
        # Store the encrypted text in the storage
        self._storage.setdefault(context_id, []).append(encrypted_text.decode())
        # Return the encrypted text as a string
        return encrypted_text.decode()

    def clear(self, context_id: UUID | None = None) -> None:
        if context_id is None:
            self._storage.clear()
        else:
            self._storage.pop(context_id, None)

    def delete(self, replacement: str, context_id: UUID) -> None:
        self._storage.get(context_id, []).remove(replacement)

    def exists(self, replacement: str, context_id: UUID) -> bool:
        raise NotImplementedError("EncryptionStorage does not support exists operation.")

    def list_replacements(self, context_id: UUID) -> list[str]:
        return self._storage.get(context_id, [])

    def get_all_context_data(self, context_id: UUID) -> dict[str, tuple[str, str]]:
        raise NotImplementedError("EncryptionStorage does not support get_all_context_data operation.")

    def get_stats(self) -> dict[str, int]:
        return {
            "total_contexts": len(self._storage),
            "total_replacements": sum(len(replacements) for replacements in self._storage.values()),
        }

    def iterate_entries(self, context_id: UUID | None = None) -> Iterator[tuple[str, str, str, UUID]]:
        for context_id, replacements in self._storage.items():
            for replacement in replacements:
                yield (replacement, "unknown", "unknown", context_id)

    def close(self) -> None:
        del self._storage
