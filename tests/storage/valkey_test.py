import uuid
from typing import AsyncIterator, Dict, List, Set, Tuple

import pytest
import pytest_asyncio

from privacy_enabled_agents.storage.valkey import ValkeyStorage

# Set the loop scope to session on tests that need it
pytestmark = pytest.mark.asyncio(scope="session")


@pytest_asyncio.fixture(scope="function")
async def valkey_storage() -> AsyncIterator[ValkeyStorage]:
    """
    Fixture to provide a ValkeyStorage instance for testing.
    Creates a fresh instance for each test and cleans up afterward.
    """
    # Set up: Create a new storage instance
    storage = ValkeyStorage(host="localhost", port=6379, db=0)

    yield storage

    # Tear down: Clear all data after the test
    await storage.clear()
    # Properly close the Valkey client connection to prevent "Event loop is closed" errors
    await storage.close()


@pytest_asyncio.fixture(scope="function")
async def test_context() -> uuid.UUID:
    """Fixture to provide a unique context ID for each test."""
    return uuid.uuid4()


@pytest_asyncio.fixture(scope="function")
async def populated_storage(
    valkey_storage: ValkeyStorage, test_context: uuid.UUID
) -> Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]:
    """
    Fixture to provide a storage populated with test data.
    Returns the storage, context ID, and a dictionary of the added data.
    """
    storage = valkey_storage
    context_id = test_context

    # Sample data to add
    test_data: List[Tuple[str, str, str]] = [
        ("John Smith", "PERSON", "PERSON_1"),
        ("jane.doe@example.com", "EMAIL", "EMAIL_1"),
        ("123-456-7890", "PHONE", "PHONE_1"),
        ("New York", "LOCATION", "LOCATION_1"),
    ]

    # Add the data to storage
    for text, label, replacement in test_data:
        await storage.put(text, label, replacement, context_id)

    # Return storage, context ID, and the test data for verification
    return storage, context_id, test_data


@pytest.mark.asyncio
async def test_put_and_get(valkey_storage: ValkeyStorage, test_context: uuid.UUID) -> None:
    """Test putting and getting entries from storage."""
    storage = valkey_storage
    context_id = test_context

    # Test data
    text: str = "John Smith"
    label: str = "PERSON"
    replacement: str = "PERSON_1"

    # Put the test data
    await storage.put(text, label, replacement, context_id)

    # Get the data back and verify
    retrieved_text, retrieved_label = await storage.get_text(replacement, context_id)

    assert retrieved_text == text
    assert retrieved_label == label


@pytest.mark.asyncio
async def test_exists(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test checking if entries exist in storage."""
    storage, context_id, _ = populated_storage

    # Check existing entry
    assert await storage.exists("PERSON_1", context_id) is True

    # Check non-existent entry
    assert await storage.exists("NONEXISTENT", context_id) is False


@pytest.mark.asyncio
async def test_delete(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test deleting entries from storage."""
    storage, context_id, _ = populated_storage

    # Verify entry exists before deletion
    assert await storage.exists("PHONE_1", context_id) is True

    # Delete the entry
    await storage.delete("PHONE_1", context_id)

    # Verify entry no longer exists
    assert await storage.exists("PHONE_1", context_id) is False


@pytest.mark.asyncio
async def test_delete_nonexistent_entry(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test deleting a non-existent entry raises a ValueError."""
    storage, context_id, _ = populated_storage

    with pytest.raises(ValueError):
        await storage.delete("NONEXISTENT", context_id)


@pytest.mark.asyncio
async def test_list_replacements(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test listing all replacements in a context."""
    storage, context_id, test_data = populated_storage

    # Get replacements
    replacements: List[str] = await storage.list_replacements(context_id)

    # Verify all expected replacements are present
    expected_replacements: List[str] = [repl for _, _, repl in test_data]
    assert sorted(replacements) == sorted(expected_replacements)
    assert len(replacements) == len(test_data)


@pytest.mark.asyncio
async def test_get_all_context_data(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test getting all data for a context."""
    storage, context_id, test_data = populated_storage

    # Get all context data
    context_data: Dict[str, Tuple[str, str]] = await storage.get_all_context_data(context_id)

    # Verify all expected data is present
    assert len(context_data) == len(test_data)

    for text, label, replacement in test_data:
        assert replacement in context_data
        retrieved_text, retrieved_label = context_data[replacement]
        assert retrieved_text == text
        assert retrieved_label == label


@pytest.mark.asyncio
async def test_clear_specific_context(valkey_storage: ValkeyStorage) -> None:
    """Test clearing a specific context."""
    storage = valkey_storage

    # Create two context IDs
    context1: uuid.UUID = uuid.uuid4()
    context2: uuid.UUID = uuid.uuid4()

    # Add data to both contexts
    await storage.put("Text1", "Label1", "Repl1", context1)
    await storage.put("Text2", "Label2", "Repl2", context2)

    # Clear only the first context
    await storage.clear(context1)

    # Verify first context is cleared
    assert await storage.list_replacements(context1) == []

    # Verify second context is untouched
    assert len(await storage.list_replacements(context2)) == 1
    assert await storage.exists("Repl2", context2) is True


@pytest.mark.asyncio
async def test_clear_all(valkey_storage: ValkeyStorage) -> None:
    """Test clearing all contexts."""
    storage = valkey_storage

    # Create two context IDs
    context1: uuid.UUID = uuid.uuid4()
    context2: uuid.UUID = uuid.uuid4()

    # Add data to both contexts
    await storage.put("Text1", "Label1", "Repl1", context1)
    await storage.put("Text2", "Label2", "Repl2", context2)

    # Clear all contexts
    await storage.clear()

    # Verify both contexts are cleared
    assert await storage.list_replacements(context1) == []
    assert await storage.list_replacements(context2) == []


@pytest.mark.asyncio
async def test_iterate_entries(populated_storage: Tuple[ValkeyStorage, uuid.UUID, List[Tuple[str, str, str]]]) -> None:
    """Test iterating through all entries in a context."""
    storage, context_id, test_data = populated_storage

    # Create a set of expected entries
    expected: Set[Tuple[str, str, str, uuid.UUID]] = {(text, label, repl, context_id) for text, label, repl in test_data}

    # Collect entries via iteration
    actual: Set[Tuple[str, str, str, uuid.UUID]] = set()
    async for text, label, repl, ctx in storage.iterate_entries(context_id):
        actual.add((text, label, repl, ctx))

    # Verify all expected entries were iterated over
    assert actual == expected


@pytest.mark.asyncio
async def test_context_isolation(valkey_storage: ValkeyStorage) -> None:
    """Test that operations in one context don't affect another context."""
    storage = valkey_storage

    # Create two context IDs
    context1: uuid.UUID = uuid.uuid4()
    context2: uuid.UUID = uuid.uuid4()

    # Add same original text with different replacements to both contexts
    await storage.put("John Smith", "PERSON", "PERSON_1", context1)
    await storage.put("John Smith", "PERSON", "PERSON_A", context2)

    # Delete from first context
    await storage.delete("PERSON_1", context1)

    # Verify it's deleted from first context
    assert await storage.exists("PERSON_1", context1) is False

    # Verify the entry in second context is still there
    assert await storage.exists("PERSON_A", context2) is True

    # Verify the content of the entry in the second context
    text, label = await storage.get_text("PERSON_A", context2)
    assert text == "John Smith"
    assert label == "PERSON"


@pytest.mark.asyncio
async def test_get_stats(valkey_storage: ValkeyStorage) -> None:
    """Test getting storage statistics."""
    storage = valkey_storage

    # Create two contexts
    context1: uuid.UUID = uuid.uuid4()
    context2: uuid.UUID = uuid.uuid4()

    # Add data to both contexts
    await storage.put("Text1", "Label1", "Repl1", context1)
    await storage.put("Text2", "Label2", "Repl2", context1)
    await storage.put("Text3", "Label3", "Repl3", context2)

    # Get stats
    stats: Dict[str, int] = await storage.get_stats()

    # Verify stats
    assert stats["contexts"] == 2
    assert stats["total_entries"] == 3
