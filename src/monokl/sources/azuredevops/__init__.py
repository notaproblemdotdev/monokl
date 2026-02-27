"""Azure DevOps source for pull requests and work items.

Provides AzureDevOpsSource for fetching pull requests and work items.
Implements CodeReviewSource and PieceOfWorkSource protocols.
"""

from __future__ import annotations

import typing as t

from monokl import get_logger
from monokl import keyring_utils
from monokl.config import get_config
from monokl.models import AzureDevOpsPullRequest
from monokl.models import CodeReview
from monokl.models import PieceOfWork
from monokl.sources.base import AdapterStatus
from monokl.sources.base import CodeReviewSource
from monokl.sources.base import PieceOfWorkSource
from monokl.sources.base import SetupAction
from monokl.sources.base import SetupCapableSource
from monokl.sources.base import SetupParam
from monokl.sources.base import SetupResult

from ._api import AzureDevOpsAPIAdapter

logger = get_logger(__name__)


class AzureDevOpsSource(CodeReviewSource, PieceOfWorkSource, SetupCapableSource):
    """Source for Azure DevOps pull requests and work items.

    Implements both CodeReviewSource (for PRs) and PieceOfWorkSource (for work items).
    Uses the Azure DevOps REST API for data fetching.

    Example:
        source = AzureDevOpsSource(
            token="pat-token",
            organizations=[
                {"organization": "myorg", "project": "MyProject"}
            ]
        )

        # Check if available
        if await source.is_available():
            # Fetch code reviews (PRs)
            prs = await source.fetch_assigned()

            # Fetch work items
            items = await source.fetch_items()
    """

    def __init__(
        self,
        token: str,
        organizations: list[dict[str, str]],
    ) -> None:
        """Initialize the Azure DevOps source.

        Args:
            token: Azure DevOps Personal Access Token (PAT)
            organizations: List of org/project dicts with 'organization' and 'project' keys
        """
        self._token = token
        self._organizations = organizations
        self._adapters: list[AzureDevOpsAPIAdapter] = [
            AzureDevOpsAPIAdapter(
                organization=org["organization"],
                project=org["project"],
                token=token,
            )
            for org in organizations
        ]

    @property
    def source_type(self) -> str:
        return "azuredevops"

    @property
    def source_icon(self) -> str:
        return "🔷"

    @property
    def adapter_type(self) -> t.Literal["api"]:
        return "api"

    async def is_available(self) -> bool:
        """Check if the source is available."""
        return bool(self._token and self._organizations)

    async def check_auth(self) -> bool:
        """Check if the token is valid."""
        if not self._adapters:
            return False
        return await self._adapters[0].check_auth()

    async def get_status(self) -> AdapterStatus:
        """Get current adapter status."""
        if not self._organizations:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No organizations configured",
            )

        if not self._token:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No API token configured",
            )

        try:
            authenticated = await self.check_auth()
            return AdapterStatus(
                installed=True,
                authenticated=authenticated,
                configured=authenticated,
                error_message=None if authenticated else "Invalid token",
                details={"organizations": len(self._organizations)},
            )
        except Exception as e:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message=str(e),
            )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if Azure DevOps API token is valid",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="configure",
                label="Configure",
                icon="⚙️",
                description="Set up Azure DevOps API token and organizations",
                requires_params=True,
                external_process=False,
                save_action=True,
                params=[
                    SetupParam(
                        id="token",
                        label="Personal Access Token",
                        type="password",
                        required=True,
                        secret=True,
                        placeholder="Enter your Azure DevOps PAT",
                        help_text="Create a PAT at dev.azure.com/_usersSettings/tokens",
                    ),
                    SetupParam(
                        id="organization",
                        label="Organization",
                        type="text",
                        required=True,
                        placeholder="myorg",
                        help_text="Azure DevOps organization name",
                    ),
                    SetupParam(
                        id="project",
                        label="Project",
                        type="text",
                        required=True,
                        placeholder="MyProject",
                        help_text="Project name within the organization",
                    ),
                ],
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Token valid" if status.authenticated else "Invalid token",
            )

        if action_id == "configure":
            token = params.get("token", "").strip()
            organization = params.get("organization", "").strip()
            project = params.get("project", "").strip()

            if not token:
                return SetupResult(success=False, error="Token is required")
            if not organization:
                return SetupResult(success=False, error="Organization is required")
            if not project:
                return SetupResult(success=False, error="Project is required")

            try:
                adapter = AzureDevOpsAPIAdapter(organization, project, token)
                is_valid = await adapter.check_auth()
                if not is_valid:
                    return SetupResult(success=False, error="Invalid token or organization")

                keyring_utils.set_token("azuredevops", token)

                config = get_config()
                config.set_adapter_config(
                    integration="azuredevops",
                    adapter_type="api",
                    config={"organizations": [{"organization": organization, "project": project}]},
                )

                return SetupResult(success=True, message="Configuration saved successfully")
            except Exception as e:
                logger.exception("Failed to save Azure DevOps configuration")
                return SetupResult(success=False, error=str(e))

        return SetupResult(success=False, error=f"Unknown action: {action_id}")

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        for action in self.setup_actions:
            if action.id == action_id:
                return action.params
        return []

    def get_external_command(self, action_id: str) -> str | None:
        return None

    async def fetch_assigned(self) -> list[CodeReview]:
        """Fetch PRs assigned to the current user.

        Returns:
            List of CodeReview items (PRs) assigned to the user.
        """
        logger.info(
            "Fetching assigned Azure DevOps PRs",
            organizations=len(self._adapters),
        )
        all_prs: list[CodeReview] = []
        for adapter in self._adapters:
            try:
                prs = await adapter.fetch_pull_requests()
                all_prs.extend([self._convert_pr(pr) for pr in prs])
            except Exception as e:
                logger.warning(
                    "Failed to fetch PRs from adapter",
                    organization=adapter.organization,
                    error=str(e),
                )
        return all_prs

    async def fetch_authored(self) -> list[CodeReview]:
        """Fetch PRs authored by the current user.

        Returns:
            List of CodeReview items (PRs) authored by the user.
        """
        logger.info(
            "Fetching authored Azure DevOps PRs",
            organizations=len(self._adapters),
        )
        all_prs: list[CodeReview] = []
        for adapter in self._adapters:
            try:
                prs = await adapter.fetch_pull_requests(creator_id="@me")
                all_prs.extend([self._convert_pr(pr) for pr in prs])
            except Exception as e:
                logger.warning(
                    "Failed to fetch authored PRs from adapter",
                    organization=adapter.organization,
                    error=str(e),
                )
        return all_prs

    async def fetch_pending_review(self) -> list[CodeReview]:
        """Fetch PRs where the current user is a reviewer.

        Returns:
            List of CodeReview items (PRs) pending user's review.
        """
        logger.info(
            "Fetching pending review Azure DevOps PRs",
            organizations=len(self._adapters),
        )
        all_prs: list[CodeReview] = []
        for adapter in self._adapters:
            try:
                prs = await adapter.fetch_pull_requests(reviewer_id="@me")
                all_prs.extend([self._convert_pr(pr) for pr in prs])
            except Exception as e:
                logger.warning(
                    "Failed to fetch pending review PRs from adapter",
                    organization=adapter.organization,
                    error=str(e),
                )
        return all_prs

    async def fetch_items(self) -> list[PieceOfWork]:
        """Fetch work items assigned to the current user.

        Returns:
            List of PieceOfWork items (work items) assigned to the user.
        """
        logger.info(
            "Fetching Azure DevOps work items",
            organizations=len(self._adapters),
        )
        all_items: list[PieceOfWork] = []
        for adapter in self._adapters:
            try:
                items = await adapter.fetch_work_items()
                all_items.extend(items)
            except Exception as e:
                logger.warning(
                    "Failed to fetch work items from adapter",
                    organization=adapter.organization,
                    error=str(e),
                )
        return all_items

    def _convert_pr(self, pr: AzureDevOpsPullRequest) -> CodeReview:
        """Convert AzureDevOpsPullRequest to CodeReview model.

        Args:
            pr: Azure DevOps pull request model

        Returns:
            CodeReview model
        """
        author = pr.createdBy.get("displayName", "Unknown")
        source_branch = pr.sourceRefName.replace("refs/heads/", "")
        url = pr.web_url or ""

        return CodeReview(
            id=str(pr.pullRequestId),
            key=pr.display_key(),
            title=pr.title,
            state="open" if pr.status == "active" else pr.status,
            author=author,
            source_branch=source_branch,
            url=url,
            created_at=pr.creationDate,
            draft=pr.isDraft,
            adapter_type=self.source_type,
            adapter_icon=self.source_icon,
        )


class AzureDevOpsAPISetupSource(SetupCapableSource):
    """Setup-only source for Azure DevOps API configuration.

    Used by the setup screen to configure Azure DevOps without needing
    a full source instance.
    """

    @property
    def adapter_type(self) -> t.Literal["api"]:
        return "api"

    @property
    def source_type(self) -> str:
        return "azuredevops"

    @property
    def source_icon(self) -> str:
        return "🔷"

    async def get_status(self) -> AdapterStatus:
        """Get current adapter status."""
        config = get_config()
        token = config.azuredevops_token
        organizations = config.azuredevops_organizations

        if not organizations:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No organizations configured",
            )

        if not token:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message="No API token configured",
            )

        try:
            adapter = AzureDevOpsAPIAdapter(
                organization=organizations[0]["organization"],
                project=organizations[0]["project"],
                token=token,
            )
            authenticated = await adapter.check_auth()
            return AdapterStatus(
                installed=True,
                authenticated=authenticated,
                configured=authenticated,
                error_message=None if authenticated else "Invalid token",
                details={"organizations": len(organizations)},
            )
        except Exception as e:
            return AdapterStatus(
                installed=True,
                authenticated=False,
                configured=False,
                error_message=str(e),
            )

    @property
    def setup_actions(self) -> list[SetupAction]:
        return [
            SetupAction(
                id="verify",
                label="Verify Auth",
                icon="✓",
                description="Check if Azure DevOps API token is valid",
                requires_params=False,
                external_process=False,
            ),
            SetupAction(
                id="configure",
                label="Configure",
                icon="⚙️",
                description="Set up Azure DevOps API token and organizations",
                requires_params=True,
                external_process=False,
                params=[
                    SetupParam(
                        id="token",
                        label="Personal Access Token",
                        type="password",
                        required=True,
                        secret=True,
                        placeholder="Enter your Azure DevOps PAT",
                        help_text="Create a PAT at dev.azure.com/_usersSettings/tokens. "
                        "Required scopes: Work Items (Read), Code (Read), "
                        "Build (Read), Release (Read)",
                    ),
                    SetupParam(
                        id="organization",
                        label="Organization",
                        type="text",
                        required=True,
                        placeholder="myorg",
                        help_text="Azure DevOps organization name",
                    ),
                    SetupParam(
                        id="project",
                        label="Project",
                        type="text",
                        required=True,
                        placeholder="MyProject",
                        help_text="Project name within the organization",
                    ),
                ],
            ),
        ]

    async def execute_setup_action(self, action_id: str, params: dict[str, str]) -> SetupResult:
        if action_id == "verify":
            status = await self.get_status()
            return SetupResult(
                success=status.authenticated,
                message="Token valid" if status.authenticated else "Invalid token",
            )

        if action_id == "configure":
            token = params.get("token", "").strip()
            organization = params.get("organization", "").strip()
            project = params.get("project", "").strip()

            if not token:
                return SetupResult(success=False, error="Token is required")
            if not organization:
                return SetupResult(success=False, error="Organization is required")
            if not project:
                return SetupResult(success=False, error="Project is required")

            try:
                adapter = AzureDevOpsAPIAdapter(organization, project, token)
                is_valid = await adapter.check_auth()
                if not is_valid:
                    return SetupResult(success=False, error="Invalid token or organization")

                keyring_utils.set_token("azuredevops", token)

                config = get_config()
                config.set_adapter_config(
                    integration="azuredevops",
                    adapter_type="api",
                    config={"organizations": [{"organization": organization, "project": project}]},
                )

                return SetupResult(success=True, message="Configuration saved successfully")
            except Exception as e:
                logger.exception("Failed to save Azure DevOps configuration")
                return SetupResult(success=False, error=str(e))

        return SetupResult(success=False, error=f"Unknown action: {action_id}")

    def get_action_params(self, action_id: str) -> list[SetupParam]:
        for action in self.setup_actions:
            if action.id == action_id:
                return action.params
        return []

    def get_external_command(self, action_id: str) -> str | None:
        return None
