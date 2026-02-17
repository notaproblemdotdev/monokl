"""Database schema definitions and migrations for monocli.

Provides schema creation and version-based migration system.
"""

from __future__ import annotations

import aiosqlite

# Current schema version
SCHEMA_VERSION = 2

# Schema creation SQL
SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unified cache table with source granularity (v2)
CREATE TABLE IF NOT EXISTS cached_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL,
    data_type TEXT NOT NULL,
    source TEXT NOT NULL,
    subsection TEXT,
    raw_json TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER NOT NULL,
    fetch_count INTEGER DEFAULT 0,
    last_error TEXT,
    UNIQUE(cache_key)
);

-- Indexes for cached_data
CREATE INDEX IF NOT EXISTS idx_cached_data_key ON cached_data(cache_key);
CREATE INDEX IF NOT EXISTS idx_cached_data_type ON cached_data(data_type);
CREATE INDEX IF NOT EXISTS idx_cached_data_source ON cached_data(source);
CREATE INDEX IF NOT EXISTS idx_cached_data_cached_at ON cached_data(cached_at);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_schema(conn: aiosqlite.Connection) -> None:
    """Initialize database schema.

    Creates all tables if they don't exist and sets schema version.
    Safe to call multiple times (idempotent).

    Args:
        conn: Active SQLite connection.
    """
    # Execute schema creation
    await conn.executescript(SCHEMA_SQL)

    # Record schema version if not already set
    cursor = await conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    row = await cursor.fetchone()

    if row is None:
        await conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    elif row[0] < SCHEMA_VERSION:
        # Migration needed
        await migrate_schema(conn, from_version=row[0], to_version=SCHEMA_VERSION)


async def migrate_schema(conn: aiosqlite.Connection, from_version: int, to_version: int) -> None:
    """Migrate database schema from one version to another.

    Args:
        conn: Active SQLite connection.
        from_version: Current schema version.
        to_version: Target schema version.
    """
    if from_version < 2:
        # Migration v1 -> v2: Drop old cache tables, create new unified cache
        await conn.execute("DROP TABLE IF EXISTS cache_metadata")
        await conn.execute("DROP TABLE IF EXISTS merge_requests")
        await conn.execute("DROP TABLE IF EXISTS work_items")

        # Create new unified cache table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cached_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL,
                data_type TEXT NOT NULL,
                source TEXT NOT NULL,
                subsection TEXT,
                raw_json TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ttl_seconds INTEGER NOT NULL,
                fetch_count INTEGER DEFAULT 0,
                last_error TEXT,
                UNIQUE(cache_key)
            )
        """)

        # Create indexes
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cached_data_key ON cached_data(cache_key)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cached_data_type ON cached_data(data_type)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cached_data_source ON cached_data(source)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cached_data_cached_at ON cached_data(cached_at)"
        )

    # Update schema version
    await conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (to_version,))
