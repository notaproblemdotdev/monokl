"""Preferences management for monocli.

Provides persistent storage for user preferences and UI state.
"""

from __future__ import annotations

import json
from typing import Any

from monocli import get_logger
from monocli.db.connection import get_db_manager

logger = get_logger(__name__)


class PreferencesManager:
    """Manage user preferences with persistent storage.

    Provides typed storage and retrieval of user preferences.
    All values are JSON-serialized for flexibility.

    Example:
        prefs = PreferencesManager()

        # Save a preference
        await prefs.set("last_active_section", "mr")

        # Retrieve with default
        section = await prefs.get("last_active_section", default="mr")

        # Delete a preference
        await prefs.delete("temp_value")
    """

    async def get(self, key: str, default: Any = None) -> Any:
        """Get preference value.

        Args:
            key: Preference key.
            default: Default value if key not found.

        Returns:
            Deserialized preference value, or default if not found.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            cursor = await conn.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = await cursor.fetchone()

            if row is None:
                return default

            # Deserialize JSON
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                # Fallback to raw string for legacy values
                return row[0]

        except Exception as e:
            logger.error("Failed to get preference", key=key, error=str(e))
            return default

    async def set(self, key: str, value: Any) -> None:
        """Set preference value.

        Args:
            key: Preference key.
            value: Value to store (will be JSON-serialized).
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            # Serialize to JSON
            serialized = json.dumps(value)

            await conn.execute(
                """
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, serialized),
            )

            logger.debug("Saved preference", key=key, value=value)

        except Exception as e:
            logger.error("Failed to set preference", key=key, error=str(e))

    async def delete(self, key: str) -> bool:
        """Delete a preference.

        Args:
            key: Preference key to delete.

        Returns:
            True if key was found and deleted, False otherwise.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            cursor = await conn.execute("DELETE FROM user_preferences WHERE key = ?", (key,))

            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug("Deleted preference", key=key)

            return deleted

        except Exception as e:
            logger.error("Failed to delete preference", key=key, error=str(e))
            return False

    async def get_all(self) -> dict[str, Any]:
        """Get all preferences as a dictionary.

        Returns:
            Dictionary of all stored preferences.
        """
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            cursor = await conn.execute("SELECT key, value FROM user_preferences")
            rows = await cursor.fetchall()

            result = {}
            for key, value_json in rows:
                try:
                    result[key] = json.loads(value_json)
                except json.JSONDecodeError:
                    result[key] = value_json

            return result

        except Exception as e:
            logger.error("Failed to get all preferences", error=str(e))
            return {}

    async def clear(self) -> None:
        """Clear all preferences (use with caution)."""
        try:
            db = get_db_manager()
            conn = await db.get_connection()

            await conn.execute("DELETE FROM user_preferences")
            logger.info("Cleared all preferences")

        except Exception as e:
            logger.error("Failed to clear preferences", error=str(e))

    # Convenience methods for common preferences

    async def get_last_active_section(self, default: str = "mr") -> str:
        """Get the last active section."""
        return await self.get("last_active_section", default)

    async def set_last_active_section(self, section: str) -> None:
        """Save the last active section."""
        await self.set("last_active_section", section)

    async def get_last_mr_subsection(self, default: str = "assigned") -> str:
        """Get the last MR subsection."""
        return await self.get("last_mr_subsection", default)

    async def set_last_mr_subsection(self, subsection: str) -> None:
        """Save the last MR subsection."""
        await self.set("last_mr_subsection", subsection)

    async def get_sort_preference(
        self, section_id: str, preserve_sort: bool = True
    ) -> dict[str, Any] | None:
        """Get sort preference for a section.

        Args:
            section_id: Section identifier (e.g., "work_items", "cr_assigned").
            preserve_sort: If False, return None regardless of stored value.

        Returns:
            Stored sort state dict or None if not found/preservation disabled.
        """
        if not preserve_sort:
            return None
        return await self.get(f"sort_{section_id}", default=None)

    async def set_sort_preference(self, section_id: str, sort_state: dict[str, Any]) -> None:
        """Save sort preference for a section.

        Args:
            section_id: Section identifier.
            sort_state: SortState serialized as dict.
        """
        await self.set(f"sort_{section_id}", sort_state)
