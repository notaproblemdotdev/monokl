"""Tests for MonoApp-level behaviors."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from monokl.config import Config
from monokl.ui.app import MonoApp
from monokl.ui.main_screen import MainScreen

if TYPE_CHECKING:
    from pathlib import Path

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
        assert "Open Config File" in command_titles
        assert "Quit" in command_titles
        assert "Keys" in command_titles
        assert "Screenshot" in command_titles


async def test_open_config_file_uses_existing_config_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config_path = tmp_path / "existing-config.yaml"
    app_config_path.write_text("gitlab:\n  group: test\n")

    app = MonoApp()

    mock_config = Mock(spec=Config)
    mock_config.get_config_path.return_value = app_config_path
    monkeypatch.setattr("monokl.ui.app.get_config", lambda: mock_config)
    monkeypatch.setattr("monokl.ui.app.shutil.which", lambda _: "/usr/bin/open")

    open_calls: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs: object) -> None:
        open_calls.append(cmd)

    monkeypatch.setattr("monokl.ui.app.subprocess.run", mock_run)
    monkeypatch.setattr("sys.platform", "darwin")

    app.action_open_config_file()

    assert open_calls == [["/usr/bin/open", str(app_config_path)]]


async def test_open_config_file_creates_default_path_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    default_config_path = tmp_path / "config" / "monokl.yaml"

    app = MonoApp()

    mock_config = Mock(spec=Config)
    mock_config.get_config_path.return_value = None
    monkeypatch.setattr("monokl.ui.app.get_config", lambda: mock_config)
    monkeypatch.setattr("monokl.ui.app.CONFIG_PATHS", [default_config_path])
    monkeypatch.setattr("monokl.ui.app.shutil.which", lambda _: "/usr/bin/open")

    open_calls: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs: object) -> None:
        open_calls.append(cmd)

    monkeypatch.setattr("monokl.ui.app.subprocess.run", mock_run)
    monkeypatch.setattr("sys.platform", "darwin")

    app.action_open_config_file()

    assert default_config_path.exists()
    assert open_calls == [["/usr/bin/open", str(default_config_path)]]
