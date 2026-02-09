"""Topbar widget for the Mono CLI dashboard.

Provides TopBar class that displays the app title with version information.
"""

from textual.containers import Container
from textual.widgets import Static


class TopBar(Static):
    """Topbar widget displaying app title and version.

    Shows "Monocli vX.Y.Z" in the top area of the application.

    Example:
        topbar = TopBar(version="1.2.3")
        yield topbar
    """

    DEFAULT_CSS = """
    TopBar {
        height: auto;
        padding: 0;
        margin: 0;
        text-align: center;
        text-style: bold;
    }
    """

    def __init__(self, version: str = "unknown", **kwargs):
        """Initialize the topbar with version.

        Args:
            version: The version string to display (e.g., "1.2.3")
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.version = version

    def render(self) -> str:
        """Render the topbar content."""
        return f"Monocli v{self.version}"
