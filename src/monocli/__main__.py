"""Entry point for Mono CLI.

Run the dashboard with: python -m monocli
"""

import argparse
import asyncio
import os
import sys

from monocli import __version__, configure_logging, get_logger
from monocli.config import ConfigError, validate_keyring_available
from monocli.db.connection import DatabaseManager
from monocli.db.work_store import WorkStore
from monocli.ui.app import MonoApp


async def clear_cache_command(db_path: str | None = None) -> None:
    """Clear all cached data from database.

    Args:
        db_path: Optional path to database file.
    """

    db = DatabaseManager(db_path)
    async with db:
        # Create a minimal WorkStore just to invalidate cache
        # Source registry not needed for invalidation
        from monocli.sources.registry import SourceRegistry

        store = WorkStore(SourceRegistry())
        await store.invalidate()
        print("Cache cleared successfully.")


def main() -> None:
    """Run the Mono CLI dashboard application."""
    parser = argparse.ArgumentParser(
        description="Mono CLI Dashboard - Unified view of PRs and work items"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Start in offline mode (use cached data only)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached data and exit",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database file (default: ~/.config/monocli/monocli.db)",
    )
    args = parser.parse_args()

    configure_logging(debug=args.debug)
    logger = get_logger()
    logger.info("Starting Mono CLI", version=__version__, debug_mode=args.debug)

    # Handle --clear-cache
    if args.clear_cache:
        try:
            asyncio.run(clear_cache_command(args.db_path))
            return
        except Exception as e:
            print(f"Error clearing cache: {e}", file=sys.stderr)
            sys.exit(1)

    # Set environment variables from CLI args
    if args.offline:
        os.environ["MONOCLI_OFFLINE_MODE"] = "true"
    if args.db_path:
        os.environ["MONOCLI_DB_PATH"] = args.db_path

    # Validate keyring availability before starting app
    try:
        validate_keyring_available()
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    app = MonoApp()
    app.run()


if __name__ == "__main__":
    main()
