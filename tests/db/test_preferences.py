"""Tests for preferences management."""

from __future__ import annotations

import pytest

from monokl.db.connection import DatabaseManager
from monokl.db.preferences import PreferencesManager


@pytest.fixture
def prefs_manager():
    """Create a preferences manager for testing."""
    return PreferencesManager()


@pytest.fixture(autouse=True)
def reset_db_manager():
    """Reset the singleton instance before each test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


class TestPreferencesManager:
    """Test preferences operations."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, tmp_path, prefs_manager):
        """Test setting and getting preferences."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Set a preference
        await prefs_manager.set("test_key", "test_value")

        # Get the preference
        value = await prefs_manager.get("test_key")
        assert value == "test_value"

        # Get with default
        default_value = await prefs_manager.get("nonexistent", default="default")
        assert default_value == "default"

        await db.close()

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, tmp_path, prefs_manager):
        """Test getting non-existent preference."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Get non-existent key
        value = await prefs_manager.get("does_not_exist")
        assert value is None

        # Get with default
        value = await prefs_manager.get("does_not_exist", default="fallback")
        assert value == "fallback"

        await db.close()

    @pytest.mark.asyncio
    async def test_complex_values(self, tmp_path, prefs_manager):
        """Test storing complex values."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Store complex types
        await prefs_manager.set("list", [1, 2, 3])
        await prefs_manager.set("dict", {"key": "value", "number": 42})
        await prefs_manager.set("bool", True)
        await prefs_manager.set("int", 123)
        await prefs_manager.set("float", 3.14)
        await prefs_manager.set("none", None)

        # Retrieve and verify
        assert await prefs_manager.get("list") == [1, 2, 3]
        assert await prefs_manager.get("dict") == {"key": "value", "number": 42}
        assert await prefs_manager.get("bool") is True
        assert await prefs_manager.get("int") == 123
        assert await prefs_manager.get("float") == 3.14
        assert await prefs_manager.get("none") is None

        await db.close()

    @pytest.mark.asyncio
    async def test_delete(self, tmp_path, prefs_manager):
        """Test deleting preferences."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Set and verify
        await prefs_manager.set("to_delete", "value")
        assert await prefs_manager.get("to_delete") == "value"

        # Delete
        deleted = await prefs_manager.delete("to_delete")
        assert deleted is True

        # Verify deleted
        assert await prefs_manager.get("to_delete") is None

        # Delete non-existent
        deleted = await prefs_manager.delete("nonexistent")
        assert deleted is False

        await db.close()

    @pytest.mark.asyncio
    async def test_get_all(self, tmp_path, prefs_manager):
        """Test getting all preferences."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Clear any existing preferences
        await prefs_manager.clear()

        # Set some preferences
        await prefs_manager.set("key1", "value1")
        await prefs_manager.set("key2", "value2")
        await prefs_manager.set("key3", 123)

        # Get all
        all_prefs = await prefs_manager.get_all()
        assert len(all_prefs) == 3
        assert all_prefs["key1"] == "value1"
        assert all_prefs["key2"] == "value2"
        assert all_prefs["key3"] == 123

        await db.close()

    @pytest.mark.asyncio
    async def test_ui_state_methods(self, tmp_path, prefs_manager):
        """Test UI state convenience methods."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Test section methods
        await prefs_manager.set_last_active_section("work")
        assert await prefs_manager.get_last_active_section() == "work"

        # Test default
        assert await prefs_manager.get_last_active_section(default="mr") == "work"

        # Test MR subsection methods
        await prefs_manager.set_last_mr_subsection("opened")
        assert await prefs_manager.get_last_mr_subsection() == "opened"

        await db.close()

    @pytest.mark.asyncio
    async def test_update_existing(self, tmp_path, prefs_manager):
        """Test updating existing preferences."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Set initial value
        await prefs_manager.set("counter", 1)
        assert await prefs_manager.get("counter") == 1

        # Update value
        await prefs_manager.set("counter", 2)
        assert await prefs_manager.get("counter") == 2

        await db.close()

    @pytest.mark.asyncio
    async def test_clear(self, tmp_path, prefs_manager):
        """Test clearing all preferences."""
        db_path = tmp_path / "test_clear.db"
        DatabaseManager.reset_instance()
        db = DatabaseManager(str(db_path))
        await db.initialize()

        # Set some preferences
        await prefs_manager.set("clear_key1", "value1")
        await prefs_manager.set("clear_key2", "value2")

        # Verify they exist
        prefs_before = await prefs_manager.get_all()
        assert "clear_key1" in prefs_before
        assert "clear_key2" in prefs_before

        # Clear all
        await prefs_manager.clear()

        # Verify cleared
        prefs_after = await prefs_manager.get_all()
        assert "clear_key1" not in prefs_after
        assert "clear_key2" not in prefs_after
        assert await prefs_manager.get("clear_key1") is None

        await db.close()
        DatabaseManager.reset_instance()
