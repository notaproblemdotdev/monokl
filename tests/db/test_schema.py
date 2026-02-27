"""Tests for database schema."""

from __future__ import annotations

import pytest

from monokl.db.connection import DatabaseManager
from monokl.db.schema import SCHEMA_VERSION


@pytest.fixture(autouse=True)
def reset_db_manager():
    """Reset the singleton instance before each test."""
    DatabaseManager.reset_instance()
    yield
    DatabaseManager.reset_instance()


class TestSchema:
    """Test database schema."""

    @pytest.mark.asyncio
    async def test_schema_version(self, tmp_path):
        """Test that schema version is recorded."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = await cursor.fetchone()

        assert row is not None
        assert row[0] == SCHEMA_VERSION

        await db.close()

    @pytest.mark.asyncio
    async def test_required_tables_exist(self, tmp_path):
        """Test that all required tables are created."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in await cursor.fetchall()]

        # Check all expected tables exist
        assert "cache_metadata" in tables
        assert "merge_requests" in tables
        assert "schema_version" in tables
        assert "user_preferences" in tables
        assert "work_items" in tables

        await db.close()

    @pytest.mark.asyncio
    async def test_indexes_exist(self, tmp_path):
        """Test that expected indexes are created."""
        db_path = tmp_path / "test.db"
        db = DatabaseManager(str(db_path))
        await db.initialize()

        conn = await db.get_connection()
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in await cursor.fetchall()]

        # Check expected indexes
        assert "idx_mr_subsection" in indexes
        assert "idx_mr_cached_at" in indexes
        assert "idx_wi_adapter_type" in indexes
        assert "idx_wi_cached_at" in indexes

        await db.close()
