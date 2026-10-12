import base64
import re
from typing import List, Optional, Dict, Any
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger
from app.schemas.repository import (
    RepositoryResponse,
    IssueResponse,
    FileTreeNode,
    FileContentResponse,
)


class GitHubService:
    """Service for interacting with GitHub REST API."""

    def __init__(self):
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers, attaching token if configured."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevSquad-AI-Platform",
        }
        token = settings.GITHUB_PERSONAL_ACCESS_TOKEN
        if token and token.strip() and not token.startswith("your-"):
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _sanitize_path(self, path: str) -> str:
        """Validate and sanitize file paths to prevent path traversal attacks."""
        cleaned = path.strip().lstrip("/")
        # Prevent parent directory traversal
        if ".." in cleaned.split("/"):
            logger.warning(f"Rejected path traversal attempt: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path: directory traversal is prohibited.",
            )
        # Prevent invalid path characters
        if re.search(r"[\x00-\x1f\x7f]", cleaned):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid characters detected in path.",
            )
        return cleaned

    async def get_repo_info(self, owner: str, repo: str) -> RepositoryResponse:
        """Fetch repository metadata from GitHub."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
            except httpx.RequestError as exc:
                logger.error(f"GitHub network error connecting to {url}: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to connect to GitHub API: {str(exc)}",
                )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found on GitHub.",
            )
        elif res.status_code == 403:
            msg = res.json().get("message", "Forbidden")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"GitHub API rate limit exceeded or access forbidden: {msg}",
            )
        elif res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"GitHub API returned error: {res.text}",
            )

        data = res.json()
        return RepositoryResponse(
            full_name=data.get("full_name", f"{owner}/{repo}"),
            default_branch=data.get("default_branch", "main"),
            is_active=not data.get("archived", False),
            description=data.get("description"),
            stars_count=data.get("stargazers_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
        )

    async def list_repo_issues(
        self, owner: str, repo: str, state: str = "open"
    ) -> List[IssueResponse]:
        """Fetch open issues for a repository, excluding pull requests."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": 30}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
            except httpx.RequestError as exc:
                logger.error(f"GitHub network error: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to connect to GitHub API: {str(exc)}",
                )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found.",
            )
        elif res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"GitHub API error: {res.text}",
            )

        items = res.json()
        issues: List[IssueResponse] = []
        for item in items:
            # GitHub issues API includes PRs; filter out if pull_request key exists
            if "pull_request" in item:
                continue
            issues.append(
                IssueResponse(
                    issue_number=item.get("number"),
                    title=item.get("title", ""),
                    body=item.get("body") or "",
                    state=item.get("state", "open"),
                    author=item.get("user", {}).get("login"),
                    labels=[lb.get("name") for lb in item.get("labels", []) if isinstance(lb, dict)],
                )
            )
        return issues

    async def get_issue_detail(
        self, owner: str, repo: str, issue_number: int
    ) -> IssueResponse:
        """Fetch full issue details for an issue number."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error: {str(exc)}",
                )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue #{issue_number} in '{owner}/{repo}' not found.",
            )
        elif res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"GitHub API error: {res.text}",
            )

        item = res.json()
        return IssueResponse(
            issue_number=item.get("number"),
            title=item.get("title", ""),
            body=item.get("body") or "",
            state=item.get("state", "open"),
            author=item.get("user", {}).get("login"),
            labels=[lb.get("name") for lb in item.get("labels", []) if isinstance(lb, dict)],
        )

    async def get_repo_tree(
        self, owner: str, repo: str, branch: Optional[str] = None
    ) -> List[FileTreeNode]:
        """Retrieve repository file tree recursively."""
        target_branch = branch or "main"
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{target_branch}?recursive=1"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers())
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error: {str(exc)}",
                )

        if res.status_code == 404 and not branch:
            # Fallback to master if default main is not found
            url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/master?recursive=1"
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=self._get_headers())

        if res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"Failed to fetch repository tree: {res.text}",
            )

        tree_data = res.json().get("tree", [])
        nodes: List[FileTreeNode] = []
        for item in tree_data:
            nodes.append(
                FileTreeNode(
                    path=item.get("path", ""),
                    type=item.get("type", "blob"),
                    size=item.get("size", 0),
                )
            )
        return nodes

    async def get_file_content(
        self, owner: str, repo: str, path: str, branch: Optional[str] = None
    ) -> FileContentResponse:
        """Fetch file content, safely decoding base64 payload."""
        clean_path = self._sanitize_path(path)
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{clean_path}"
        params = {}
        if branch:
            params["ref"] = branch

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, headers=self._get_headers(), params=params)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"GitHub API error: {str(exc)}",
                )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{clean_path}' not found in repository '{owner}/{repo}'.",
            )
        elif res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"Failed to retrieve file: {res.text}",
            )

        data = res.json()
        encoding = data.get("encoding")
        raw_content = data.get("content", "")

        if encoding == "base64":
            try:
                decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
            except Exception as e:
                logger.error(f"Error decoding base64 file {clean_path}: {e}")
                decoded = f"[Binary or undecodable content: {clean_path}]"
        else:
            decoded = raw_content

        # Cap file content to prevent memory exhaustion (max 500 KB)
        max_bytes = 500_000
        truncated = False
        if len(decoded.encode("utf-8")) > max_bytes:
            decoded = decoded[:max_bytes] + "\n\n... [Content truncated at 500KB] ..."
            truncated = True

        return FileContentResponse(
            path=clean_path,
            content=decoded,
            size=data.get("size", len(decoded)),
            truncated=truncated,
        )


github_service = GitHubService()
