"""GitHub integration service providing authenticated REST API operations."""
import base64
import logging
from typing import Any, Optional
import httpx
from pydantic import BaseModel, ConfigDict, Field
from app.core.config import Settings, settings
from app.core.exceptions import DevSquadException

logger = logging.getLogger(__name__)


class GitHubAPIError(DevSquadException):
    """Base exception for GitHub API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = status_code


class GitHubAuthError(GitHubAPIError):
    """Raised when GitHub authentication or authorization fails."""


class GitHubResourceNotFoundError(GitHubAPIError):
    """Raised when a requested repository, issue, or file is not found."""


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limits are exceeded."""
    def __init__(self, message: str, reset_timestamp: Optional[int] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message, status_code=429, details=details)
        self.reset_timestamp = reset_timestamp


class GitHubRepoMetadata(BaseModel):
    """Normalized GitHub repository metadata."""
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    full_name: str
    owner: str
    default_branch: str
    description: Optional[str] = None
    is_private: bool = False
    html_url: str


class GitHubIssue(BaseModel):
    """Normalized GitHub issue entity."""
    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    body: Optional[str] = None
    state: str
    labels: list[str] = Field(default_factory=list)
    html_url: str
    author: Optional[str] = None
    comments_count: int = 0


class GitHubTreeItem(BaseModel):
    """Normalized item from GitHub Git Trees API."""
    model_config = ConfigDict(extra="ignore")

    path: str
    mode: str
    type: str  # "blob" or "tree"
    sha: str
    size: Optional[int] = None


class GitHubFileContent(BaseModel):
    """Normalized repository file content."""
    model_config = ConfigDict(extra="ignore")

    path: str
    content: str  # decoded UTF-8 content
    sha: str
    size_bytes: int
    is_binary: bool = False


class GitHubCommitMetadata(BaseModel):
    """Normalized GitHub commit metadata."""
    model_config = ConfigDict(extra="ignore")

    sha: str
    message: str
    author: Optional[str] = None
    date: Optional[str] = None
    html_url: str


class GitHubBranchMetadata(BaseModel):
    """Normalized GitHub branch metadata."""
    model_config = ConfigDict(extra="ignore")

    name: str
    commit_sha: str
    protected: bool = False


# Common binary and non-source extensions to exclude from plain-text processing
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pyc", ".pyo", ".class", ".db", ".sqlite", ".sqlite3",
    ".woff", ".woff2", ".ttf", ".eot",
}


class GitHubService:
    """Asynchronous client for GitHub REST API operations."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        configured_token = token or settings.github_token.get_secret_value()
        self.base_url = (base_url or settings.github_api_url).rstrip("/")
        self.timeout = timeout_seconds
        self._external_client = http_client is not None

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevSquad-AI-Agent/0.1.0",
        }
        if configured_token:
            headers["Authorization"] = f"Bearer {configured_token}"

        self.client = http_client or httpx.AsyncClient(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close HTTP client if owned by this service instance."""
        if not self._external_client:
            await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _handle_response_error(self, response: httpx.Response, context_msg: str) -> None:
        """Inspect response status codes and rate limits, raising typed exceptions."""
        if response.status_code in (401, 403):
            # Check for rate-limiting
            remaining = response.headers.get("x-ratelimit-remaining")
            reset_ts = response.headers.get("x-ratelimit-reset")
            if remaining == "0" or "rate limit" in response.text.lower():
                reset_val = int(reset_ts) if reset_ts and reset_ts.isdigit() else None
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded. Reset at {reset_val}.",
                    reset_timestamp=reset_val,
                    details={"remaining": remaining, "reset": reset_ts},
                )
            raise GitHubAuthError(
                f"GitHub authentication/permission failure: {context_msg} (HTTP {response.status_code})",
                status_code=response.status_code,
                details={"response": response.text[:500]},
            )

        if response.status_code == 404:
            raise GitHubResourceNotFoundError(
                f"GitHub resource not found: {context_msg} (HTTP 404)",
                status_code=404,
                details={"response": response.text[:500]},
            )

        if response.status_code == 429:
            reset_ts = response.headers.get("retry-after") or response.headers.get("x-ratelimit-reset")
            reset_val = int(reset_ts) if reset_ts and reset_ts.isdigit() else None
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded: {context_msg}",
                reset_timestamp=reset_val,
            )

        if response.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API request failed: {context_msg} (HTTP {response.status_code})",
                status_code=response.status_code,
                details={"response": response.text[:500]},
            )

    async def get_repository(self, owner: str, repo: str) -> GitHubRepoMetadata:
        """Fetch metadata for a specific repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, f"repos/{owner}/{repo}")
            data = resp.json()
            return GitHubRepoMetadata(
                id=data["id"],
                name=data["name"],
                full_name=data["full_name"],
                owner=data["owner"]["login"],
                default_branch=data.get("default_branch", "main"),
                description=data.get("description"),
                is_private=data.get("private", False),
                html_url=data["html_url"],
            )
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout connecting to GitHub for repo {owner}/{repo}") from exc

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> GitHubIssue:
        """Retrieve a specific issue and its metadata."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, f"issues/{issue_number}")
            data = resp.json()
            labels = [lbl["name"] if isinstance(lbl, dict) else str(lbl) for lbl in data.get("labels", [])]
            return GitHubIssue(
                number=data["number"],
                title=data["title"],
                body=data.get("body") or "",
                state=data.get("state", "open"),
                labels=labels,
                html_url=data["html_url"],
                author=data.get("user", {}).get("login") if data.get("user") else None,
                comments_count=data.get("comments", 0),
            )
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching issue #{issue_number} from {owner}/{repo}") from exc

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        page: int = 1,
        per_page: int = 30,
    ) -> list[GitHubIssue]:
        """Fetch list of issues with pagination support."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {"state": state, "page": page, "per_page": per_page}
        try:
            resp = await self.client.get(url, params=params)
            self._handle_response_error(resp, f"list_issues for {owner}/{repo}")
            items = resp.json()
            results = []
            for data in items:
                # Exclude pull requests (GitHub issues API includes PRs with a 'pull_request' key)
                if "pull_request" in data:
                    continue
                labels = [lbl["name"] if isinstance(lbl, dict) else str(lbl) for lbl in data.get("labels", [])]
                results.append(
                    GitHubIssue(
                        number=data["number"],
                        title=data["title"],
                        body=data.get("body") or "",
                        state=data.get("state", "open"),
                        labels=labels,
                        html_url=data["html_url"],
                        author=data.get("user", {}).get("login") if data.get("user") else None,
                        comments_count=data.get("comments", 0),
                    )
                )
            return results
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout listing issues for {owner}/{repo}") from exc

    async def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> list[str]:
        """Retrieve relevant comment bodies for an issue."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        try:
            resp = await self.client.get(url, params={"per_page": 20})
            self._handle_response_error(resp, f"comments for issue #{issue_number}")
            items = resp.json()
            return [item.get("body", "") for item in items if item.get("body")]
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout retrieving comments for issue #{issue_number}") from exc

    async def get_repository_tree(
        self,
        owner: str,
        repo: str,
        tree_sha: Optional[str] = None,
        recursive: bool = True,
    ) -> list[GitHubTreeItem]:
        """
        Retrieve repository directory tree via GitHub Git Trees API.
        If tree_sha is not provided, defaults to the repository default_branch.
        """
        sha = tree_sha
        if not sha:
            repo_meta = await self.get_repository(owner, repo)
            sha = repo_meta.default_branch

        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{sha}"
        params = {"recursive": "1"} if recursive else {}
        try:
            resp = await self.client.get(url, params=params)
            self._handle_response_error(resp, f"tree for {owner}/{repo}@{sha}")
            data = resp.json()
            tree_raw = data.get("tree", [])
            return [
                GitHubTreeItem(
                    path=item["path"],
                    mode=item["mode"],
                    type=item["type"],
                    sha=item["sha"],
                    size=item.get("size"),
                )
                for item in tree_raw
            ]
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching tree for {owner}/{repo}") from exc

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        ref: Optional[str] = None,
        max_bytes: int = 500_000,
    ) -> GitHubFileContent:
        """
        Retrieve single file contents from repository.
        Decodes base64 content, validates size, and detects binary content.
        """
        # Quick extension check for binary formats
        ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        if ext in BINARY_EXTENSIONS:
            return GitHubFileContent(
                path=file_path,
                content="",
                sha="",
                size_bytes=0,
                is_binary=True,
            )

        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
        params = {"ref": ref} if ref else {}
        try:
            resp = await self.client.get(url, params=params)
            self._handle_response_error(resp, f"contents/{file_path}")
            data = resp.json()

            if isinstance(data, list):
                raise GitHubAPIError(f"Path '{file_path}' is a directory, not a file.")

            size = data.get("size", 0)
            if size > max_bytes:
                raise GitHubAPIError(
                    f"File '{file_path}' exceeds maximum allowed size ({size} > {max_bytes} bytes)."
                )

            encoding = data.get("encoding")
            raw_content = data.get("content", "")
            sha = data.get("sha", "")

            if encoding == "base64":
                raw_bytes = base64.b64decode(raw_content)
                # Check for null bytes indicative of binary
                if b"\x00" in raw_bytes[:1024]:
                    return GitHubFileContent(
                        path=file_path,
                        content="",
                        sha=sha,
                        size_bytes=len(raw_bytes),
                        is_binary=True,
                    )
                try:
                    decoded_text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    return GitHubFileContent(
                        path=file_path,
                        content="",
                        sha=sha,
                        size_bytes=len(raw_bytes),
                        is_binary=True,
                    )
            else:
                decoded_text = raw_content

            return GitHubFileContent(
                path=file_path,
                content=decoded_text,
                sha=sha,
                size_bytes=size,
                is_binary=False,
            )
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching file content for {file_path}") from exc

    async def get_branch(self, owner: str, repo: str, branch: str) -> GitHubBranchMetadata:
        """Fetch metadata for a specific branch."""
        url = f"{self.base_url}/repos/{owner}/{repo}/branches/{branch}"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, f"branches/{branch}")
            data = resp.json()
            return GitHubBranchMetadata(
                name=data["name"],
                commit_sha=data.get("commit", {}).get("sha", ""),
                protected=data.get("protected", False),
            )
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching branch '{branch}' for {owner}/{repo}") from exc

    async def get_commit(self, owner: str, repo: str, commit_sha: str) -> GitHubCommitMetadata:
        """Fetch metadata for a specific commit."""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, f"commits/{commit_sha}")
            data = resp.json()
            commit_data = data.get("commit", {})
            return GitHubCommitMetadata(
                sha=data["sha"],
                message=commit_data.get("message", ""),
                author=commit_data.get("author", {}).get("name"),
                date=commit_data.get("author", {}).get("date"),
                html_url=data.get("html_url", ""),
            )
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching commit '{commit_sha}' for {owner}/{repo}") from exc
