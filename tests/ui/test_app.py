"""Tests for MonoApp-level behaviors."""

from __future__ import annotations

import pytest

from monocle.ui.main_screen import MainScreen

pytestmark = pytest.mark.asyncio


async def test_command_palette_includes_setup_command(app_with_stub_store) -> None:
    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.2)
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)

        commands = list(pilot.app.get_system_commands(screen))
        setup_command = next((command for command in commands if command.title == "Setup"), None)

        assert setup_command is not None
        assert "setup screen" in setup_command.help.lower()


async def test_system_commands_include_expected_entries(app_with_stub_store) -> None:
    async with app_with_stub_store.run_test() as pilot:
        await pilot.pause(0.2)
        screen = pilot.app.screen
        assert isinstance(screen, MainScreen)

        command_titles = {command.title for command in pilot.app.get_system_commands(screen)}

        assert "Setup" in command_titles
        assert "Quit" in command_titles
        assert "Keys" in command_titles
        assert "Screenshot" in command_titles
