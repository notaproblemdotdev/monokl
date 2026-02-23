"""Main Textual application for Monocle.

Provides MonoApp class - the entry point for the dashboard UI.
"""

from collections.abc import Iterable

from textual.app import App
from textual.app import SystemCommand
from textual.binding import Binding
from textual.screen import Screen

from monocle.config import get_config
from monocle.ui.main_screen import MainScreen
from monocle.ui.setup_screen import SetupScreen


class MonoApp(App):
    """Main Textual application for Monocle dashboard.

    Provides a two-section dashboard showing merge requests and work items
    from GitLab and Jira respectively.

    Example:
        # Run the app
        MonoApp().run()

        # Or from command line:
        # python -m monocle
    """

    THEME = "atom-one-dark"
    SCREENS = {
        "main": MainScreen,
        "setup": SetupScreen,
    }

    BINDINGS = [
        Binding("s", "open_setup", "Setup", show=False),
    ]

    TITLE = "Mono CLI"
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

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Add app-specific commands to the command palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Setup",
            "Open the setup screen for configuring integrations",
            self.action_open_setup,
        )
