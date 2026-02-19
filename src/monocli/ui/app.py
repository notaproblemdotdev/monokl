"""Main Textual application for Mono CLI.

Provides MonoApp class - the entry point for the dashboard UI.
"""

from textual.app import App
from textual.binding import Binding

from monocli.config import get_config
from monocli.ui.main_screen import MainScreen
from monocli.ui.setup_screen import SetupScreen


class MonoApp(App):
    """Main Textual application for Mono CLI dashboard.

    Provides a two-section dashboard showing merge requests and work items
    from GitLab and Jira respectively.

    Example:
        # Run the app
        MonoApp().run()

        # Or from command line:
        # python -m monocli
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
