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
    stargazers_count: int = 0
    forks_count: int = 0
    language: Optional[str] = None
    open_issues_count: int = 0


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
                stargazers_count=data.get("stargazers_count", 0),
                forks_count=data.get("forks_count", 0),
                language=data.get("language"),
                open_issues_count=data.get("open_issues_count", 0),
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

    async def get_user_profile(self, username: Optional[str] = None) -> dict[str, Any]:
        """Fetch GitHub user profile (authenticated or by username)."""
        url = f"{self.base_url}/users/{username}" if username else f"{self.base_url}/user"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, f"user_profile ({username or 'authenticated'})")
            data = resp.json()
            return {
                "login": data.get("login"),
                "id": data.get("id"),
                "avatar_url": data.get("avatar_url"),
                "html_url": data.get("html_url"),
                "name": data.get("name"),
                "bio": data.get("bio"),
                "public_repos": data.get("public_repos", 0),
                "total_private_repos": data.get("total_private_repos", 0),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
            }
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout fetching GitHub profile for {username or 'current user'}") from exc

    async def list_user_repositories(
        self,
        username: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[GitHubRepoMetadata]:
        """Fetch repositories for authenticated user or specific username."""
        if username:
            url = f"{self.base_url}/users/{username}/repos"
            params = {"sort": "updated", "page": page, "per_page": per_page}
        else:
            url = f"{self.base_url}/user/repos"
            params = {"sort": "updated", "affiliation": "owner,collaborator", "page": page, "per_page": per_page}

        try:
            resp = await self.client.get(url, params=params)
            self._handle_response_error(resp, f"repos for {username or 'authenticated user'}")
            items = resp.json()
            return [
                GitHubRepoMetadata(
                    id=data["id"],
                    name=data["name"],
                    full_name=data["full_name"],
                    owner=data["owner"]["login"],
                    default_branch=data.get("default_branch", "main"),
                    description=data.get("description"),
                    is_private=data.get("private", False),
                    html_url=data["html_url"],
                    stargazers_count=data.get("stargazers_count", 0),
                    forks_count=data.get("forks_count", 0),
                    language=data.get("language"),
                    open_issues_count=data.get("open_issues_count", 0),
                )
                for data in items
            ]
        except httpx.TimeoutException as exc:
            raise GitHubAPIError(f"Timeout listing user repositories for {username or 'current user'}") from exc

    async def list_user_issues(
        self,
        username: Optional[str] = None,
        state: str = "open",
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """
        List open issues across the user's account.
        If authenticated, queries /user/issues.
        If username is provided without a token, queries recent public repos and aggregates open issues.
        """
        if not username:
            # Authenticated user issues
            url = f"{self.base_url}/user/issues"
            params = {"state": state, "filter": "all", "page": page, "per_page": per_page}
            try:
                resp = await self.client.get(url, params=params)
                self._handle_response_error(resp, "user_issues")
                items = resp.json()
                results = []
                for data in items:
                    if "pull_request" in data:
                        continue
                    repo_full_name = data.get("repository", {}).get("full_name") or ""
                    labels = [lbl["name"] if isinstance(lbl, dict) else str(lbl) for lbl in data.get("labels", [])]
                    results.append({
                        "number": data["number"],
                        "title": data["title"],
                        "body": data.get("body") or "",
                        "state": data.get("state", "open"),
                        "labels": labels,
                        "html_url": data["html_url"],
                        "author": data.get("user", {}).get("login"),
                        "repository_name": repo_full_name,
                        "comments_count": data.get("comments", 0),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                    })
                return results
            except Exception as exc:
                logger.warning(f"Failed to fetch /user/issues: {exc}")

        # If username is provided or token is not scoped for /user/issues:
        user_to_query = username
        if not user_to_query:
            try:
                prof = await self.get_user_profile()
                user_to_query = prof.get("login")
            except Exception:
                user_to_query = None

        if not user_to_query:
            return []

        # List user's active repositories and aggregate issues
        repos = await self.list_user_repositories(username=user_to_query, per_page=10)
        aggregated = []
        for repo in repos:
            if repo.open_issues_count > 0:
                try:
                    owner, name = repo.full_name.split("/", 1)
                    issues = await self.list_issues(owner, name, state=state, per_page=10)
                    for issue in issues:
                        aggregated.append({
                            "number": issue.number,
                            "title": issue.title,
                            "body": issue.body,
                            "state": issue.state,
                            "labels": issue.labels,
                            "html_url": issue.html_url,
                            "author": issue.author,
                            "repository_name": repo.full_name,
                            "comments_count": issue.comments_count,
                        })
                except Exception as exc:
                    logger.debug(f"Could not list issues for {repo.full_name}: {exc}")
        return aggregated

    async def get_token_permissions(self) -> dict[str, Any]:
        """Inspect token scopes and capabilities from GitHub API headers."""
        url = f"{self.base_url}/user"
        try:
            resp = await self.client.get(url)
            self._handle_response_error(resp, "token permissions inspection")
            scopes_header = resp.headers.get("x-oauth-scopes", "")
            scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
            user_data = resp.json()

            can_write_issues = any(
                s in scopes for s in ("repo", "public_repo", "write:discussion", "issues")
            )
            can_create_prs = any(s in scopes for s in ("repo", "public_repo"))
            can_admin_repo = "repo" in scopes or "admin:repo_hook" in scopes

            return {
                "authenticated": True,
                "username": user_data.get("login"),
                "scopes": scopes,
                "can_write_issues": can_write_issues or bool(scopes),
                "can_create_prs": can_create_prs,
                "can_admin_repo": can_admin_repo,
                "rate_limit_limit": int(resp.headers.get("x-ratelimit-limit", 5000)),
                "rate_limit_remaining": int(resp.headers.get("x-ratelimit-remaining", 5000)),
            }
        except Exception as exc:
            logger.warning(f"Failed to inspect token permissions: {exc}")
            return {
                "authenticated": False,
                "username": None,
                "scopes": [],
                "can_write_issues": False,
                "can_create_prs": False,
                "can_admin_repo": False,
                "rate_limit_limit": 60,
                "rate_limit_remaining": 0,
            }

    async def post_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Publish a solution comment to a GitHub issue using authenticated token."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        resp = await self.client.post(url, json={"body": body})
        self._handle_response_error(resp, f"comment on issue {owner}/{repo}#{issue_number}")
        return resp.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create a new issue on GitHub using authenticated token."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = await self.client.post(url, json=payload)
        self._handle_response_error(resp, f"create issue on {owner}/{repo}")
        return resp.json()

    async def close_issue(
        self, owner: str, repo: str, issue_number: int, state_reason: str = "completed"
    ) -> dict[str, Any]:
        """Close an issue on GitHub when defect is resolved."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        resp = await self.client.patch(
            url,
            json={"state": "closed", "state_reason": state_reason},
        )
        self._handle_response_error(resp, f"close issue {owner}/{repo}#{issue_number}")
        return resp.json()

    async def add_issue_labels(
        self, owner: str, repo: str, issue_number: int, labels: list[str]
    ) -> list[str]:
        """Apply labels (e.g. 'devsquad-solved') to an issue."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels"
        resp = await self.client.post(url, json={"labels": labels})
        self._handle_response_error(resp, f"add labels to {owner}/{repo}#{issue_number}")
        data = resp.json()
        if isinstance(data, list):
            return [lbl["name"] if isinstance(lbl, dict) else str(lbl) for lbl in data]
        return labels

