"""Database connection management for monokl.

Provides async SQLite connection management with singleton pattern.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiosqlite

from monokl.db.schema import init_schema


class DatabaseManager:
    """Async SQLite database manager with connection pooling.

    Uses a singleton pattern to maintain a single connection per process.
    Supports context manager protocol for automatic cleanup.

    Example:
        # As context manager (recommended)
        async with DatabaseManager(db_path) as db:
            conn = await db.get_connection()

        # Or manual lifecycle
        db = DatabaseManager(db_path)
        await db.initialize()
        conn = await db.get_connection()
        await db.close()
    """

    _instance: DatabaseManager | None = None

    def __new__(cls, db_path: str | Path | None = None) -> DatabaseManager:
        """Singleton pattern - return existing instance if available."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses default.
        """
        if not self._initialized:
            self._db_path = self._resolve_db_path(db_path)
            self._connection: aiosqlite.Connection | None = None
            self._initialized = True

    @staticmethod
    def _resolve_db_path(db_path: str | Path | None) -> Path:
        """Resolve database path from parameter or environment."""
        if db_path:
            return Path(db_path).expanduser().resolve()

        # Check environment variable first
        env_path = os.getenv("MONOKL_DB_PATH")
        if env_path:
            return Path(env_path).expanduser().resolve()

        # Default to XDG config directory
        config_dir = Path.home() / ".config" / "monokl"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "monokl.db"

    async def __aenter__(self) -> DatabaseManager:
        """Async context manager entry - initializes database."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - closes connection."""
        await self.close()

    async def initialize(self) -> None:
        """Initialize database connection and schema.

        Creates parent directories if needed and initializes schema.
        Safe to call multiple times (idempotent).
        """
        if self._connection is not None:
            return

        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create connection with useful defaults
        self._connection = await aiosqlite.connect(
            str(self._db_path),
            timeout=10.0,  # Wait up to 10s for locks
            isolation_level=None,  # Autocommit mode for simplicity
        )

        # Enable foreign keys and WAL mode for better performance
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA synchronous = NORMAL")

        # Initialize schema
        await init_schema(self._connection)

    async def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def get_connection(self) -> aiosqlite.Connection:
        """Get current database connection.

        Returns:
            Active SQLite connection.

        Raises:
            RuntimeError: If database not initialized.
        """
        if self._connection is None:
            raise RuntimeError(
                "Database not initialized. Call initialize() or use context manager."
            )
        return self._connection

    @property
    def db_path(self) -> Path:
        """Get database file path."""
        return self._db_path

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (mainly for testing)."""
        cls._instance = None


def get_db_manager(db_path: str | Path | None = None) -> DatabaseManager:
    """Get DatabaseManager instance.

    Args:
        db_path: Optional path override (ignored if instance already exists).

    Returns:
        DatabaseManager instance.
    """
    return DatabaseManager(db_path)
