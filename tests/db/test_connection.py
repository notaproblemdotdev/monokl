"""Tests for database connection management."""

from __future__ import annotations

import pytest

from monokl.db.connection import DatabaseManager
from monokl.db.connection import get_db_manager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return str(db_path)


@pytest.fixture(autouse=True)
def reset_db_manager():
    """Reset the singleton instance before each test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


class TestDatabaseManager:
    """Test database connection management."""

    @pytest.mark.asyncio
    async def test_initialize_creates_connection(self, temp_db):
        """Test that initialize() creates a database connection."""
        db = DatabaseManager(temp_db)
        await db.initialize()

        conn = await db.get_connection()
        assert conn is not None

        await db.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db):
        """Test that context manager properly initializes and closes."""
        async with DatabaseManager(temp_db) as db:
            conn = await db.get_connection()
            assert conn is not None

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, temp_db):
        """Test that DatabaseManager is a singleton."""
        db1 = DatabaseManager(temp_db)
        db2 = DatabaseManager("/different/path.db")

        # Should be the same instance
        assert db1 is db2
        # Should use the first path
        assert str(db1.db_path) == temp_db

    @pytest.mark.asyncio
    async def test_get_connection_without_init(self):
        """Test that get_connection raises error if not initialized."""
        db = DatabaseManager()

        with pytest.raises(RuntimeError, match="not initialized"):
            await db.get_connection()

    @pytest.mark.asyncio
    async def test_schema_initialization(self, temp_db):
        """Test that schema is initialized on first connect."""
        async with DatabaseManager(temp_db) as db:
            conn = await db.get_connection()

            # Check that tables exist
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in await cursor.fetchall()]

            assert "cache_metadata" in tables
            assert "merge_requests" in tables
            assert "work_items" in tables
            assert "user_preferences" in tables
            assert "schema_version" in tables


class TestGetDbManager:
    """Test global database manager access."""

    def test_get_db_manager_returns_singleton(self, temp_db):
        """Test that get_db_manager returns singleton instance."""
        db1 = get_db_manager(temp_db)
        db2 = get_db_manager()

        assert db1 is db2
