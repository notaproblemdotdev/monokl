"""Azure DevOps REST API adapter.

Uses Azure DevOps REST API 7.0 for fetching pull requests and work items.
"""

from __future__ import annotations

import base64
import typing as t
from contextlib import suppress

from monokl import get_logger
from monokl.models import AzureDevOpsPieceOfWork
from monokl.models import AzureDevOpsPullRequest

if t.TYPE_CHECKING:
    import aiohttp

logger = get_logger(__name__)

API_VERSION = "7.0"


class AzureDevOpsAPIAdapter:
    """Adapter for Azure DevOps REST API.

    Fetches pull requests and work items using Azure DevOps REST API.

    Example:
        adapter = AzureDevOpsAPIAdapter(
            organization="myorg",
            project="MyProject",
            token="pat-token"
        )

        # Check authentication
        if await adapter.check_auth():
            # Fetch PRs
            prs = await adapter.fetch_pull_requests()

            # Fetch work items
            items = await adapter.fetch_work_items()
    """

    def __init__(self, organization: str, project: str, token: str) -> None:
        """Initialize the Azure DevOps API adapter.

        Args:
            organization: Azure DevOps organization name
            project: Project name
            token: Personal Access Token (PAT)
        """
        self.organization = organization
        self.project = project
        self.token = token
        self._base_url = f"https://dev.azure.com/{organization}"
        self._session: aiohttp.ClientSession | None = None

    def _get_auth_header_value(self) -> str:
        """Get Basic auth header value for PAT.

        Azure DevOps PAT uses Basic auth with empty username and PAT as password.
        """
        auth_str = f":{self.token}"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()
        return f"Basic {auth_bytes}"

    def _headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": self._get_auth_header_value(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            import aiohttp

            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def check_auth(self) -> bool:
        """Verify PAT token by fetching profile.

        Returns:
            True if token is valid, False otherwise
        """
        import aiohttp

        url = f"https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version={API_VERSION}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers()) as resp:
                    if resp.status == 200:
                        logger.debug("Azure DevOps authentication successful")
                        return True
                    logger.debug(
                        "Azure DevOps authentication failed",
                        status=resp.status,
                    )
                    return False
        except Exception as e:
            logger.warning("Azure DevOps auth check failed", error=str(e))
            return False

    async def fetch_pull_requests(
        self,
        creator_id: str | None = None,
        reviewer_id: str | None = None,
        status: str = "active",
        include_abandoned: bool = False,
    ) -> list[AzureDevOpsPullRequest]:
        """Fetch pull requests from all repositories in the project.

        Args:
            creator_id: Filter by creator ID (GUID or "@me")
            reviewer_id: Filter by reviewer ID (GUID or "@me")
            status: PR status filter ("active", "abandoned", "completed", "all")
            include_abandoned: Include abandoned PRs in results

        Returns:
            List of AzureDevOpsPullRequest models
        """
        import aiohttp

        url = f"{self._base_url}/{self.project}/_apis/git/pullrequests"
        params: dict[str, str] = {"api-version": API_VERSION}

        if status != "all":
            params["searchCriteria[status]"] = status
        if creator_id:
            params["searchCriteria[creatorId]"] = creator_id
        if reviewer_id:
            params["searchCriteria[reviewerId]"] = reviewer_id

        logger.info(
            "Fetching Azure DevOps pull requests",
            organization=self.organization,
            project=self.project,
            status=status,
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers(), params=params) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(
                            "Failed to fetch pull requests",
                            status=resp.status,
                            error=text[:200],
                        )
                        return []

                    data = await resp.json()

            prs = []
            for item in data.get("value", []):
                with suppress(Exception):
                    pr = AzureDevOpsPullRequest(
                        pullRequestId=item["pullRequestId"],
                        title=item["title"],
                        status=item["status"],
                        createdBy=item["createdBy"],
                        repository=item["repository"],
                        sourceRefName=item["sourceRefName"],
                        targetRefName=item["targetRefName"],
                        creationDate=item.get("creationDate"),
                        isDraft=item.get("isDraft", False),
                    )
                    pr.web_url = self._build_pr_url(item)
                    prs.append(pr)

            logger.info("Fetched Azure DevOps pull requests", count=len(prs))
            return prs

        except Exception as e:
            logger.error("Failed to fetch pull requests", error=str(e))
            return []

    async def fetch_work_items(
        self,
        wiql: str | None = None,
    ) -> list[AzureDevOpsPieceOfWork]:
        """Fetch work items via WIQL query.

        Args:
            wiql: WIQL query string. If None, uses default query for
                  items assigned to current user that are not closed/done.

        Returns:
            List of AzureDevOpsPieceOfWork models
        """
        import aiohttp

        if wiql is None:
            wiql = (
                "SELECT [System.Id] FROM WorkItems "
                "WHERE [System.AssignedTo] = @me "
                "AND [System.State] <> 'Closed' "
                "AND [System.State] <> 'Done' "
                "AND [System.State] <> 'Removed' "
                "ORDER BY [System.ChangedDate] DESC"
            )

        logger.info(
            "Fetching Azure DevOps work items",
            organization=self.organization,
            project=self.project,
        )

        try:
            # Step 1: Execute WIQL to get IDs
            wiql_url = f"{self._base_url}/{self.project}/_apis/wit/wiql?api-version={API_VERSION}"
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    wiql_url,
                    headers=self._headers(),
                    json={"query": wiql},
                ) as resp,
            ):
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(
                        "Failed to execute WIQL query",
                        status=resp.status,
                        error=text[:200],
                    )
                    return []

                wiql_result = await resp.json()

            ids = [str(item["id"]) for item in wiql_result.get("workItems", [])]
            if not ids:
                logger.info("No work items found matching query")
                return []

            # Step 2: Batch fetch work items (max 200 at a time)
            items: list[AzureDevOpsPieceOfWork] = []
            batch_size = 200

            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i : i + batch_size]
                items_url = (
                    f"{self._base_url}/{self.project}"
                    f"/_apis/wit/workitemsbatch?api-version={API_VERSION}"
                )

                async with (
                    aiohttp.ClientSession() as session,
                    session.post(
                        items_url,
                        headers=self._headers(),
                        json={
                            "ids": batch_ids,
                            "$expand": "Links",
                        },
                    ) as resp,
                ):
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(
                            "Failed to fetch work items batch",
                            status=resp.status,
                            error=text[:200],
                        )
                        continue

                    items_data = await resp.json()

                for item in items_data.get("value", []):
                    with suppress(Exception):
                        work_item = AzureDevOpsPieceOfWork(
                            id=item["id"],
                            fields=item.get("fields", {}),
                            url=item.get("url", ""),
                        )
                        items.append(work_item)

            logger.info("Fetched Azure DevOps work items", count=len(items))
            return items

        except Exception as e:
            logger.error("Failed to fetch work items", error=str(e))
            return []

    def _build_pr_url(self, pr_data: dict) -> str:
        """Build browser URL for pull request.

        Args:
            pr_data: PR data from API including repository info

        Returns:
            Browser-accessible URL for the PR
        """
        repo_name = pr_data.get("repository", {}).get("name", "")
        pr_id = pr_data.get("pullRequestId", "")
        return f"{self._base_url}/{self.project}/_git/{repo_name}/pullrequest/{pr_id}"
