"""Loading spinner widget with status text for Textual applications.

Provides StatusSpinner - a simple animated spinner with customizable status messages.
"""

from __future__ import annotations

from rich.console import RenderableType
from textual.reactive import reactive
from textual.widgets import Static


class StatusSpinner(Static):
    """A simple loading spinner with status text.

    Displays an animated spinner alongside a status message.
    Uses a simple frame-based animation (⣾⣽⣻⢿⡿⣟⣯⣷).

    Example:
        spinner = StatusSpinner("Loading data...")
        spinner.status = "Fetching from API..."
        spinner.stop()
    """

    # Spinner animation frames (simple braille spinner)
    FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    status: reactive[str] = reactive("")
    active: reactive[bool] = reactive(True)

    DEFAULT_CSS = """
    StatusSpinner {
        width: auto;
        height: auto;
        content-align: left middle;
        text-style: dim;
    }

    StatusSpinner.active {
        text-style: none;
    }

    StatusSpinner.spinner {
        color: $accent;
    }
    """

    def __init__(self, status: str = "", *, id: str | None = None) -> None:  # noqa: A002
        """Initialize the status spinner.

        Args:
            status: Initial status message to display.
            id: Optional widget ID.
        """
        super().__init__(id=id)
        self.status = status
        self._frame_index = 0
        self._update_timer = None

    def on_mount(self) -> None:
        """Start the animation when mounted."""
        if self.active:
            self._start_animation()

    def on_unmount(self) -> None:
        """Stop the animation when unmounted."""
        self._stop_animation()

    def _start_animation(self) -> None:
        """Start the spinner animation."""
        if self._update_timer is None:
            self._update_timer = self.set_interval(0.1, self._advance_frame)
        self.active = True
        self.add_class("active")

    def _stop_animation(self) -> None:
        """Stop the spinner animation."""
        if self._update_timer is not None:
            self._update_timer.stop()
            self._update_timer = None
        self.active = False
        self.remove_class("active")

    def _advance_frame(self) -> None:
        """Advance to the next animation frame."""
        self._frame_index = (self._frame_index + 1) % len(self.FRAMES)
        self.refresh()

    def render(self) -> RenderableType:
        """Render the spinner with status text."""
        frame = self.FRAMES[self._frame_index] if self.active else "○"
        status_text = f" {self.status}" if self.status else ""
        return f"[accent]{frame}[/]{status_text}"

    def start(self, status: str = "") -> None:
        """Start or restart the spinner with a new status.

        Args:
            status: New status message to display.
        """
        if status:
            self.status = status
        self._start_animation()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self._stop_animation()

    def update_status(self, status: str) -> None:
        """Update the status message while spinning.

        Args:
            status: New status message to display.
        """
        self.status = status
