"""Entry point for Monocle.

Run the dashboard with: python -m monocle dash
Run setup with: python -m monocle setup
"""

import os
import subprocess
import sys
import typing as t
import webbrowser
from typing import Any

import typer
from typer.core import TyperCommand

from monocle import __version__
from monocle import configure_logging
from monocle import get_logger
from monocle.config import ConfigError
from monocle.config import validate_keyring_available
from monocle.db.connection import DatabaseManager
from monocle.db.work_store import WorkStore
from monocle.features import get_feature_flag
from monocle.features import is_feature_enabled
from monocle.logging_config import get_log_file_path
from monocle.ui.app import MonoApp


class MonocleApp(typer.Typer):
    """Typer app that respects feature flags on commands."""

    def command(
        self,
        name: str | None = None,
        *,
        cls: type[TyperCommand] | None = None,
        context_settings: dict[Any, Any] | None = None,
        help: str | None = None,
        epilog: str | None = None,
        short_help: str | None = None,
        options_metavar: str | None = None,
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        rich_help_panel: str | None = None,
    ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
        """Decorator to register a command, respecting feature flags."""

        def decorator(func: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
            flag = get_feature_flag(func)
            if flag and not is_feature_enabled(flag):
                return func

            return super(MonocleApp, self).command(
                name=name,
                cls=cls,
                context_settings=context_settings,
                help=help,
                epilog=epilog,
                short_help=short_help,
                options_metavar=options_metavar,
                add_help_option=add_help_option,
                no_args_is_help=no_args_is_help,
                hidden=hidden,
                deprecated=deprecated,
                rich_help_panel=rich_help_panel,
            )(func)

        return decorator


app = MonocleApp(
    help="Mono CLI Dashboard - Unified view of PRs and work items",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__version__}")
        raise typer.Exit()


def _apply_env_vars(offline: bool, db_path: str | None) -> None:
    if offline:
        os.environ["MONOCLE_OFFLINE_MODE"] = "true"
    if db_path:
        os.environ["MONOCLE_DB_PATH"] = db_path


async def _clear_cache(db_path: str | None = None) -> None:
    db = DatabaseManager(db_path)
    async with db:
        from monocle.sources.registry import SourceRegistry

        store = WorkStore(SourceRegistry())
        await store.invalidate()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit", callback=version_callback
    ),
) -> None:
    pass


@app.command()
def dash(
    web: t.Annotated[
        bool,
        typer.Option("--web", help="Serve the dashboard over the web (textual-serve)"),
    ] = False,
    port: t.Annotated[
        int,
        typer.Option("--port", "-p", help="Port for web server (requires --web)"),
    ] = 6969,
    host: t.Annotated[
        str,
        typer.Option("--host", help="Host interface for web server (requires --web)"),
    ] = "localhost",
    no_open: t.Annotated[
        bool,
        typer.Option("--no-open", help="Don't open browser automatically (requires --web)"),
    ] = False,
    debug: t.Annotated[bool, typer.Option("--debug", help="Enable debug logging")] = False,
    offline: t.Annotated[bool, typer.Option("--offline", help="Use cached data only")] = False,
    db_path: t.Annotated[
        str | None,
        typer.Option("--db-path", help="Path to SQLite database file"),
    ] = None,
    clear_cache: t.Annotated[
        bool,
        typer.Option("--clear-cache", help="Clear all cached data and exit"),
    ] = False,
) -> None:
    """Launch the dashboard (TUI), or serve it in a browser with `--web`."""
    import asyncio

    configure_logging(debug=debug)
    logger = get_logger()
    logger.info(
        "Starting Mono CLI Dashboard",
        version=__version__,
        debug_mode=debug,
        web_mode=web,
    )

    if clear_cache:
        try:
            asyncio.run(_clear_cache(db_path))
            typer.echo("Cache cleared successfully.")
            raise typer.Exit()
        except Exception as e:
            typer.echo(f"Error clearing cache: {e}", err=True)
            raise typer.Exit(1)

    _apply_env_vars(offline, db_path)

    try:
        validate_keyring_available()
    except ConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if web:
        from textual_serve.server import Server

        cmd_parts = [sys.executable, "-m", "monocle", "dash"]
        if debug:
            cmd_parts.append("--debug")
        if offline:
            cmd_parts.append("--offline")
        if db_path:
            cmd_parts.extend(["--db-path", db_path])

        server = Server(" ".join(cmd_parts), host=host, port=port)

        url = f"http://{host}:{port}"
        typer.echo(f"Starting web server at {url}")

        if not no_open:
            typer.echo("Opening browser...")
            webbrowser.open(url)

        server.serve()
        return

    if port != 6969 or host != "localhost" or no_open:
        typer.echo("Error: --host/--port/--no-open require --web", err=True)
        raise typer.Exit(2)

    MonoApp().run()


@app.command()
def setup(
    debug: t.Annotated[bool, typer.Option("--debug", help="Enable debug logging")] = False,
) -> None:
    configure_logging(debug=debug)
    logger = get_logger()
    logger.info("Starting Mono CLI Setup", version=__version__, debug_mode=debug)

    try:
        validate_keyring_available()
    except ConfigError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    mono_app = MonoApp(initial_screen="setup")
    mono_app.run()


@app.command()
def logs(
    debug: t.Annotated[bool, typer.Option("--debug", help="Enable debug logging")] = False,
) -> None:
    """Open current log file with configured viewer."""
    configure_logging(debug=debug)
    logger = get_logger()
    logger.info("Opening logs", version=__version__, debug_mode=debug)

    log_path = get_log_file_path()

    if not log_path.exists():
        typer.echo(f"No log file found at {log_path}")
        raise typer.Exit(1)

    from monocle.config import get_config

    cmd_template = get_config().show_logs_command
    cmd = cmd_template.replace("{file}", str(log_path))

    logger.info("Executing log viewer", command=cmd, log_path=str(log_path))
    subprocess.run(cmd, shell=True)


def run_dev() -> None:
    """Run monocle with Textual hot reload (for development)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        ["uv", "run", "textual", "run", "--dev", "monocle.ui.dev:app"],
        check=False,
        env=env,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    app()
