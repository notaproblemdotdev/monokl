"""Main Textual application for Monokl.

Provides MonoApp class - the entry point for the dashboard UI.
"""

import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from textual.app import App
from textual.app import SystemCommand
from textual.binding import Binding
from textual.screen import Screen

from monokl import get_logger
from monokl.config import CONFIG_PATHS
from monokl.config import get_config
from monokl.ui.main_screen import MainScreen
from monokl.ui.setup_screen import SetupScreen

logger = get_logger(__name__)


class MonoApp(App):
    """Main Textual application for Monokl dashboard.

    Provides a two-section dashboard showing merge requests and work items
    from GitLab and Jira respectively.

    Example:
        # Run the app
        MonoApp().run()

        # Or from command line:
        # python -m monokl dash
    """

    THEME = "atom-one-dark"
    SCREENS = {
        "main": MainScreen,
        "setup": SetupScreen,
    }

    BINDINGS = [
        Binding("s", "open_setup", "Setup", show=False),
    ]

    TITLE = "Monokl"
    SUB_TITLE = "Unified Dashboard"

    CSS = """
    Screen {
        background: $surface-darken-1;
    }

    * {
        scrollbar-size: 1 1;
    }
    """

    def __init__(self, initial_screen: str = "main") -> None:
        super().__init__()
        self._initial_screen = initial_screen

    def on_mount(self) -> None:
        config = get_config()

        if not config.is_configured():
            self.push_screen("setup")
        else:
            self.push_screen(self._initial_screen)

    def on_unmount(self) -> None:
        pass

    def action_open_setup(self) -> None:
        self.push_screen("setup")

    def action_open_config_file(self) -> None:
        """Open the config file with the system default editor."""
        config = get_config()
        config_path = config.get_config_path() or CONFIG_PATHS[0]

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.touch(exist_ok=True)
            self._open_with_system_default(config_path)
        except (OSError, subprocess.SubprocessError) as e:
            logger.exception("Failed to open config file", path=str(config_path), error=str(e))
            self.notify(f"Failed to open config file: {e}", severity="error")

    def _open_with_system_default(self, path: Path) -> None:
        """Open a path with the platform default file handler."""
        if sys.platform == "darwin":
            opener = shutil.which("open")
            if not opener:
                raise FileNotFoundError("Could not find 'open' command")
            subprocess.run([opener, str(path)], check=True)  # noqa: S603
            return

        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
            return

        opener = shutil.which("xdg-open")
        if not opener:
            raise FileNotFoundError("Could not find 'xdg-open' command")
        subprocess.run([opener, str(path)], check=True)  # noqa: S603

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Add app-specific commands to the command palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Setup",
            "Open the setup screen for configuring integrations",
            self.action_open_setup,
        )
        yield SystemCommand(
            "Open Config File",
            "Open the Monokl config file in the system default editor",
            self.action_open_config_file,
        )
