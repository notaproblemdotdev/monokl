"""Tests for StatusSpinner widget.

Tests for the loading spinner with status text functionality.
"""

import pytest
from textual.app import App
from textual.app import ComposeResult

from monokl.ui.spinner import StatusSpinner


class SpinnerTestApp(App[None]):
    """Test app for StatusSpinner widget."""

    def __init__(self, status: str = "") -> None:
        """Initialize test app with a spinner."""
        super().__init__()
        self.spinner: StatusSpinner | None = None
        self.initial_status = status

    def compose(self) -> ComposeResult:
        """Compose the app with the spinner."""
        self.spinner = StatusSpinner(self.initial_status, id="test-spinner")
        yield self.spinner


class TestStatusSpinner:
    """Tests for StatusSpinner widget."""

    @pytest.mark.asyncio
    async def test_spinner_creation(self) -> None:
        """Test spinner is created with initial status."""
        app = SpinnerTestApp("Loading...")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            assert spinner.status == "Loading..."
            assert spinner.active is True

    @pytest.mark.asyncio
    async def test_spinner_empty_status(self) -> None:
        """Test spinner works with empty status."""
        app = SpinnerTestApp("")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            assert spinner.status == ""
            assert spinner.active is True

    @pytest.mark.asyncio
    async def test_spinner_update_status(self) -> None:
        """Test status can be updated."""
        app = SpinnerTestApp("Initial")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            assert spinner.status == "Initial"

            spinner.update_status("Updated")
            assert spinner.status == "Updated"

    @pytest.mark.asyncio
    async def test_spinner_stop(self) -> None:
        """Test spinner stops correctly."""
        app = SpinnerTestApp("Loading...")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            assert spinner.active is True

            spinner.stop()
            assert spinner.active is False

    @pytest.mark.asyncio
    async def test_spinner_start(self) -> None:
        """Test spinner starts/restarts correctly."""
        app = SpinnerTestApp("")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)

            # Start with status
            spinner.start("Fetching...")
            assert spinner.active is True
            assert spinner.status == "Fetching..."

            # Start again with different status
            spinner.start("Processing...")
            assert spinner.status == "Processing..."

    @pytest.mark.asyncio
    async def test_spinner_animation_advances(self) -> None:
        """Test spinner animation advances frames."""
        app = SpinnerTestApp("Loading")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            initial_frame = spinner._frame_index

            # Advance frame manually
            spinner._advance_frame()
            assert spinner._frame_index == (initial_frame + 1) % len(StatusSpinner.FRAMES)

    @pytest.mark.asyncio
    async def test_spinner_render_includes_status(self) -> None:
        """Test render output includes status text."""
        app = SpinnerTestApp("Test Status")
        async with app.run_test() as pilot:
            spinner = app.query_one("#test-spinner", StatusSpinner)
            rendered = str(spinner.render())

            assert "Test Status" in rendered

    @pytest.mark.asyncio
    async def test_spinner_frames_exist(self) -> None:
        """Test spinner has animation frames defined."""
        assert len(StatusSpinner.FRAMES) > 0
        assert all(isinstance(frame, str) for frame in StatusSpinner.FRAMES)
