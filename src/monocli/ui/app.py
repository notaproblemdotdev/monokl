"""Main Textual application for Mono CLI.

Provides MonoApp class - the entry point for the dashboard UI.
"""

from textual.app import App

from monocli.ui.main_screen import MainScreen


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

    # Screen definitions
    SCREENS = {
        "main": MainScreen,
    }

    # App configuration
    TITLE = "Mono CLI"
    SUB_TITLE = "Unified Dashboard"

    # CSS styling
    CSS = """
    Screen {
        background: $surface-darken-1;
    }
    """

    def on_mount(self) -> None:
        """Handle mount event - push main screen."""
        self.push_screen("main")

    def action_quit(self) -> None:
        """Action handler for quitting the app."""
        self.exit()
