"""Setup screen for configuring integrations.

Provides a UI for users to:
- View all supported integrations
- Select CLI or API adapter for each integration
- Verify authentication
- Trigger sign-in flows
"""

from __future__ import annotations

import asyncio
import shutil
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.containers import Horizontal
from textual.containers import ScrollableContainer
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import Select

from monocli import get_logger
from monocli.config import get_config
from monocli.sources.base import AdapterStatus
from monocli.sources.integrations import get_all_integrations

if TYPE_CHECKING:
    from monocli.sources.base import SetupCapableSource
    from monocli.sources.integrations import IntegrationMeta

logger = get_logger(__name__)


class IntegrationCard(Container):
    """Widget for configuring a single integration."""

    DEFAULT_CSS = """
    IntegrationCard {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border: solid $primary;
        background: $surface;
    }

    IntegrationCard.configured {
        border: solid $success;
    }

    IntegrationCard.error {
        border: solid $error;
    }

    IntegrationCard > .card-header {
        text-style: bold;
        margin-bottom: 0;
    }

    IntegrationCard > .card-description {
        color: $text-muted;
    }

    IntegrationCard .status-row {
        layout: horizontal;
        height: auto;
    }

    IntegrationCard .adapter-row {
        layout: horizontal;
        height: auto;
    }

    IntegrationCard .adapter-select {
        width: 20;
        margin-right: 1;
    }

    IntegrationCard .cli-status {
        color: $text-muted;
    }

    IntegrationCard .cli-status.installed {
        color: $success;
    }

    IntegrationCard .cli-status.not-found {
        color: $warning;
    }

    IntegrationCard .actions-row {
        layout: horizontal;
        height: auto;
    }

    IntegrationCard Button {
        min-width: 8;
        height: 3;
        padding: 0 2;
    }
    """

    integration_id: reactive[str] = reactive("")
    selected_adapter: reactive[str] = reactive("")
    status: reactive[AdapterStatus | None] = reactive(None)
    _is_loading: reactive[bool] = reactive(False)

    def __init__(
        self,
        integration: IntegrationMeta,
    ) -> None:
        super().__init__()
        self._integration = integration
        self.integration_id = integration.id
        self._init_adapter_selection()

    def _init_adapter_selection(self) -> None:
        """Determine the initial adapter selection based on config and availability."""
        config = get_config()
        selected = config.get_selected_adapter(self._integration.id)
        available = self._integration.available_adapters
        cli_available = self._integration.cli_name and shutil.which(self._integration.cli_name)

        selected_lower = selected.lower() if selected else None

        if selected_lower and selected_lower in available:
            self.selected_adapter = selected_lower
        elif cli_available and "cli" in available:
            self.selected_adapter = "cli"
        elif available:
            self.selected_adapter = available[0]
        elif "cli" in available:
            self.selected_adapter = "cli"
        else:
            self.selected_adapter = ""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="card-header"):
            yield Label(f"{self._integration.icon} {self._integration.name}")
            yield Label(self._integration.description, classes="card-description")

        with Horizontal(classes="adapter-row"):
            adapters = [(a.upper(), a) for a in self._integration.available_adapters]
            initial_value = (
                self.selected_adapter
                if self.selected_adapter in self._integration.available_adapters
                else None
            )
            if not adapters:
                yield Label("No adapters available")
            else:
                yield Select(
                    adapters,
                    value=initial_value,
                    id="adapter-select",
                    classes="adapter-select",
                )
            yield Label("", id="cli-status", classes="cli-status")

        with Horizontal(classes="status-row"):
            yield Label("Status:", id="status-label")
            yield Label("Checking...", id="status-text", classes="status-indicator")

        with Horizontal(classes="actions-row"):
            yield Button("Verify", id="btn-verify", variant="primary")
            yield Button("Sign In", id="btn-signin", variant="default")
            yield Button("Configure", id="btn-configure", variant="default")

    def _get_adapter_select(self) -> Select:
        return self.query_one("#adapter-select", Select)

    def _get_cli_status(self) -> Label:
        return self.query_one("#cli-status", Label)

    def _get_status_text(self) -> Label:
        return self.query_one("#status-text", Label)

    def _get_btn_verify(self) -> Button:
        return self.query_one("#btn-verify", Button)

    def _get_btn_signin(self) -> Button:
        return self.query_one("#btn-signin", Button)

    def _get_btn_configure(self) -> Button:
        return self.query_one("#btn-configure", Button)

    async def on_mount(self) -> None:
        self._load_initial_state()
        await self._check_status()

    def _load_initial_state(self) -> None:
        if self._integration.cli_name:
            cli_status = self._get_cli_status()
            if shutil.which(self._integration.cli_name):
                cli_status.update(f"[{self._integration.cli_name} installed]")
                cli_status.add_class("installed")
                cli_status.remove_class("not-found")
            else:
                cli_status.update(f"[{self._integration.cli_name} not found]")
                cli_status.add_class("not-found")
                cli_status.remove_class("installed")

    async def _check_status(self) -> None:
        self._is_loading = True
        self._get_status_text().update("Checking...")

        try:
            adapter = self._create_adapter()
            if adapter:
                self.status = await adapter.get_status()
                self._update_status_ui()
            else:
                self._get_status_text().update("No adapter available")
        except Exception as e:
            logger.error("Failed to check status", integration=self._integration.id, error=str(e))
            self._get_status_text().update(f"Error: {e}")
            self.add_class("error")
        finally:
            self._is_loading = False

    def _create_adapter(self) -> SetupCapableSource | None:
        if self.selected_adapter == "cli" and self._integration.create_cli_adapter:
            return self._integration.create_cli_adapter()
        if self.selected_adapter == "api" and self._integration.create_api_adapter:
            return self._integration.create_api_adapter()
        return None

    def _update_status_ui(self) -> None:
        if not self.status:
            return

        status_text = self._get_status_text()

        if self.status.authenticated:
            status_text.update("Authenticated")
            status_text.add_class("authenticated")
            self.add_class("configured")
            self.remove_class("error")
        elif self.status.installed:
            status_text.update("Not authenticated")
            status_text.remove_class("authenticated")
            self.remove_class("configured")
        else:
            status_text.update("Not installed")
            status_text.remove_class("authenticated")
            self.remove_class("configured")

        if self.status.error_message:
            status_text.update(self.status.error_message)
            self.add_class("error")

        self._update_buttons()

    def _update_buttons(self) -> None:
        pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "adapter-select":
            self.selected_adapter = str(event.value)
            config = get_config()
            config.set_selected_adapter(self._integration.id, self.selected_adapter)
            self.run_worker(self._check_status(), exclusive=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-verify":
            self.run_worker(self._check_status(), exclusive=True)
        elif button_id == "btn-signin":
            self._trigger_action("login")
        elif button_id == "btn-configure":
            self._trigger_action("configure")

    def _trigger_action(self, action_id: str) -> None:
        self.app.push_screen(
            SetupActionDialog(
                integration_id=self._integration.id,
                action_id=action_id,
            )
        )


class SetupScreen(Screen):
    """Screen for configuring integrations."""

    DEFAULT_CSS = """
    SetupScreen {
        layout: vertical;
    }

    SetupScreen > Header {
        background: $primary;
    }

    SetupScreen > #content {
        height: 1fr;
        overflow: auto;
        padding: 1;
    }

    SetupScreen > #content > .section-title {
        text-style: bold;
        margin-bottom: 0;
    }

    SetupScreen > #content > .section-description {
        color: $text-muted;
        margin-bottom: 1;
    }

    SetupScreen #integrations-grid {
        layout: grid;
        grid-size: 2 0;
        grid-gutter: 1 1;
    }

    SetupScreen Footer {
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        ("escape,q", "close", "Close"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer(id="content"):
            yield Label("Setup Integrations", classes="section-title")
            yield Label(
                "Configure your integrations to start tracking PRs and work items.",
                classes="section-description",
            )
            with Vertical(id="integrations-grid"):
                for integration in get_all_integrations():
                    yield IntegrationCard(integration)
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Setup"

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        for card in self.query(IntegrationCard):
            card.run_worker(card._check_status(), exclusive=True)


class SetupActionDialog(Screen):
    """Modal dialog for executing a setup action."""

    DEFAULT_CSS = """
    SetupActionDialog {
        align: center middle;
    }

    SetupActionDialog > Container {
        width: 60;
        max-width: 80;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    SetupActionDialog .dialog-title {
        text-style: bold;
        margin-bottom: 1;
    }

    SetupActionDialog .dialog-description {
        color: $text-muted;
        margin-bottom: 1;
    }

    SetupActionDialog .form-field {
        margin-bottom: 1;
    }

    SetupActionDialog .form-label {
        margin-bottom: 0;
    }

    SetupActionDialog Input {
        width: 100%;
        margin-top: 0;
    }

    SetupActionDialog .buttons {
        layout: horizontal;
        margin-top: 1;
    }

    SetupActionDialog .buttons Button {
        margin-right: 1;
    }

    SetupActionDialog Button {
        min-width: 10;
    }

    SetupActionDialog LoadingIndicator {
        width: auto;
        height: 1;
    }

    SetupActionDialog .result-message {
        margin-top: 1;
        padding: 0 1;
    }

    SetupActionDialog .result-message.success {
        color: $success;
    }

    SetupActionDialog .result-message.error {
        color: $error;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    integration_id: reactive[str] = reactive("")
    action_id: reactive[str] = reactive("")
    _is_loading: reactive[bool] = reactive(False)
    result_message: reactive[str] = reactive("")
    result_success: reactive[bool] = reactive(False)

    def __init__(
        self,
        integration_id: str,
        action_id: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.integration_id = integration_id
        self.action_id = action_id

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("", id="dialog-title", classes="dialog-title")
            yield Label("", id="dialog-description", classes="dialog-description")
            with Vertical(id="form-container"):
                pass
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Execute", id="btn-execute", variant="primary")
            yield Label("", id="result-message", classes="result-message")

    async def on_mount(self) -> None:
        from monocli.sources.integrations import get_integration

        integration = get_integration(self.integration_id)
        if not integration:
            self._close()
            return

        config = get_config()
        selected_adapter = config.get_selected_adapter(self.integration_id) or "cli"

        if selected_adapter == "cli" and integration.create_cli_adapter:
            self._adapter = integration.create_cli_adapter()
        elif selected_adapter == "api" and integration.create_api_adapter:
            self._adapter = integration.create_api_adapter()
        else:
            self._close()
            return

        self._action = next(
            (a for a in self._adapter.setup_actions if a.id == self.action_id),
            None,
        )

        if not self._action:
            self._close()
            return

        self._setup_ui()

    def _setup_ui(self) -> None:
        if not self._action:
            return

        self.query_one("#dialog-title", Label).update(f"{self._action.icon} {self._action.label}")

        if self._action.description:
            self.query_one("#dialog-description", Label).update(self._action.description)
        else:
            self.query_one("#dialog-description", Label).display = False

        if self._action.external_process:
            self.query_one("#dialog-description", Label).update(
                "This will open a terminal session for authentication. "
                "Follow the prompts in your terminal."
            )

        form_container = self.query_one("#form-container", Vertical)
        form_container.remove_children()

        if self._action.requires_params and self._action.params:
            from textual.widgets import Input

            for param in self._action.params:
                label = Label(f"{param.label}{'*' if param.required else ''}:")
                input_widget = Input(
                    id=f"param-{param.id}",
                    placeholder=param.placeholder or "",
                    password=param.type == "password",
                )
                form_container.mount(label, input_widget)
        else:
            form_container.display = False

    def _get_param_values(self) -> dict[str, str]:
        from textual.widgets import Input

        values = {}
        if not self._action or not self._action.params:
            return values

        form_container = self.query_one("#form-container", Vertical)
        for param in self._action.params:
            input_widget = form_container.query_one(f"#param-{param.id}", Input)
            values[param.id] = input_widget.value

        return values

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self._close()
        elif event.button.id == "btn-execute":
            self.run_worker(self._execute_action(), exclusive=True)

    async def _execute_action(self) -> None:
        if not self._action or not self._adapter:
            return

        self._is_loading = True
        self._update_loading_ui(True)

        try:
            if self._action.external_process:
                result = await self._run_external_process()
            else:
                params = self._get_param_values()
                result = await self._adapter.execute_setup_action(self._action.id, params)

            self.result_message = result.message or ("Success" if result.success else "Failed")
            self.result_success = result.success

            result_label = self.query_one("#result-message", Label)
            result_label.update(self.result_message)
            result_label.add_class("success" if result.success else "error")

            if result.success:
                await asyncio.sleep(1.5)
                self._close()

        except Exception as e:
            logger.error("Action failed", error=str(e))
            result_label = self.query_one("#result-message", Label)
            result_label.update(f"Error: {e}")
            result_label.add_class("error")
        finally:
            self._is_loading = False
            self._update_loading_ui(False)

    async def _run_external_process(self):
        from monocli.sources.base import SetupResult

        if not self._action or not self._action.external_command:
            return SetupResult(success=False, error="No external command configured")

        import asyncio

        with self.app.suspend():
            process = await asyncio.create_subprocess_shell(
                self._action.external_command,
            )
            exit_code = await process.wait()

        return SetupResult(
            success=exit_code == 0,
            message="Completed" if exit_code == 0 else f"Failed with code {exit_code}",
        )

    def _update_loading_ui(self, loading: bool) -> None:
        self.query_one("#btn-execute", Button).disabled = loading
        self.query_one("#btn-cancel", Button).disabled = loading

    def _close(self) -> None:
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self._close()
