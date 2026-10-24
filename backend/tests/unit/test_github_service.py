"""Unit tests for GitHubService with mocked HTTP responses."""
import base64
import pytest
import httpx
from app.services.github_service import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubFileContent,
    GitHubIssue,
    GitHubRateLimitError,
    GitHubRepoMetadata,
    GitHubResourceNotFoundError,
    GitHubService,
)


@pytest.mark.asyncio
async def test_get_repository_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World"
        return httpx.Response(
            200,
            json={
                "id": 1296269,
                "name": "Hello-World",
                "full_name": "octocat/Hello-World",
                "owner": {"login": "octocat"},
                "default_branch": "main",
                "description": "My first repository",
                "private": False,
                "html_url": "https://github.com/octocat/Hello-World",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        repo = await svc.get_repository("octocat", "Hello-World")
        assert repo.id == 1296269
        assert repo.full_name == "octocat/Hello-World"
        assert repo.default_branch == "main"


@pytest.mark.asyncio
async def test_github_auth_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        with pytest.raises(GitHubAuthError):
            await svc.get_repository("octocat", "Private-Repo")


@pytest.mark.asyncio
async def test_github_rate_limit_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1700000000",
        }
        return httpx.Response(403, headers=headers, json={"message": "API rate limit exceeded"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await svc.get_repository("octocat", "Hello-World")
        assert exc_info.value.reset_timestamp == 1700000000


@pytest.mark.asyncio
async def test_github_resource_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        with pytest.raises(GitHubResourceNotFoundError):
            await svc.get_repository("octocat", "Non-Existent")


@pytest.mark.asyncio
async def test_get_issue_and_comments():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/comments"):
            return httpx.Response(200, json=[{"body": "First comment"}, {"body": "Second comment"}])
        return httpx.Response(
            200,
            json={
                "number": 42,
                "title": "Fix authentication crash",
                "body": "Crash occurs on empty token",
                "state": "open",
                "labels": [{"name": "bug"}, {"name": "priority:high"}],
                "html_url": "https://github.com/octocat/Hello-World/issues/42",
                "user": {"login": "coder"},
                "comments": 2,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        issue = await svc.get_issue("octocat", "Hello-World", 42)
        assert issue.number == 42
        assert issue.labels == ["bug", "priority:high"]

        comments = await svc.get_issue_comments("octocat", "Hello-World", 42)
        assert len(comments) == 2
        assert comments[0] == "First comment"


@pytest.mark.asyncio
async def test_list_issues_filters_pull_requests():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "number": 1,
                    "title": "Genuine issue",
                    "state": "open",
                    "labels": [],
                    "html_url": "url1",
                },
                {
                    "number": 2,
                    "title": "A Pull Request mistakenly returned by issues API",
                    "state": "open",
                    "pull_request": {"url": "pr_url"},  # This is a PR
                    "labels": [],
                    "html_url": "url2",
                },
            ],
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        issues = await svc.list_issues("octocat", "Hello-World")
        assert len(issues) == 1
        assert issues[0].number == 1


@pytest.mark.asyncio
async def test_get_file_content_decodes_base64():
    raw_code = "def add(a, b):\n    return a + b\n"
    encoded = base64.b64encode(raw_code.encode("utf-8")).decode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "name": "math_utils.py",
                "path": "src/math_utils.py",
                "sha": "a" * 40,
                "size": len(raw_code),
                "encoding": "base64",
                "content": encoded,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        file_obj = await svc.get_file_content("octocat", "Hello-World", "src/math_utils.py")
        assert file_obj.content == raw_code
        assert file_obj.is_binary is False
        assert file_obj.size_bytes == len(raw_code)


@pytest.mark.asyncio
async def test_get_file_content_rejects_binary_and_oversized():
    # 1. Extension binary check
    async with httpx.AsyncClient() as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        binary_file = await svc.get_file_content("octocat", "Hello-World", "assets/logo.png")
        assert binary_file.is_binary is True
        assert binary_file.content == ""

    # 2. Oversized file check
    def oversized_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "name": "large.py",
                "path": "large.py",
                "size": 1_000_000,
                "encoding": "none",
                "content": "huge",
            },
        )

    transport = httpx.MockTransport(oversized_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        with pytest.raises(GitHubAPIError) as exc_info:
            await svc.get_file_content("octocat", "Hello-World", "large.py", max_bytes=500_000)
        assert "exceeds maximum allowed size" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_branch_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World/branches/main"
        return httpx.Response(
            200,
            json={
                "name": "main",
                "commit": {"sha": "c" * 40},
                "protected": True,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        branch = await svc.get_branch("octocat", "Hello-World", "main")
        assert branch.name == "main"
        assert branch.commit_sha == "c" * 40
        assert branch.protected is True


@pytest.mark.asyncio
async def test_get_commit_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World/commits/c" + "c" * 39
        return httpx.Response(
            200,
            json={
                "sha": "c" * 40,
                "commit": {
                    "message": "feat: initial commit",
                    "author": {"name": "Octocat", "date": "2026-10-14T00:00:00Z"},
                },
                "html_url": "https://github.com/octocat/Hello-World/commit/" + "c" * 40,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(base_url="https://api.github.com", http_client=client)
        commit = await svc.get_commit("octocat", "Hello-World", "c" * 40)
        assert commit.sha == "c" * 40
        assert commit.message == "feat: initial commit"
        assert commit.author == "Octocat"


@pytest.mark.asyncio
async def test_get_token_permissions_authorized():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/user"
        return httpx.Response(
            200,
            headers={
                "x-oauth-scopes": "repo, read:user, write:discussion",
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4990",
            },
            json={"login": "ayushkale06", "id": 12345},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(token="ghp_test123", base_url="https://api.github.com", http_client=client)
        perms = await svc.get_token_permissions()
        assert perms["authenticated"] is True
        assert perms["username"] == "ayushkale06"
        assert perms["can_write_issues"] is True
        assert perms["can_create_prs"] is True
        assert "repo" in perms["scopes"]
        assert perms["rate_limit_remaining"] == 4990


@pytest.mark.asyncio
async def test_post_issue_comment_and_close():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/repos/octocat/Hello-World/issues/1/comments":
            return httpx.Response(201, json={"id": 999, "html_url": "https://github.com/octocat/Hello-World/issues/1#issuecomment-999"})
        if request.method == "PATCH" and request.url.path == "/repos/octocat/Hello-World/issues/1":
            return httpx.Response(200, json={"id": 1, "state": "closed"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        svc = GitHubService(token="ghp_test123", base_url="https://api.github.com", http_client=client)
        comment = await svc.post_issue_comment("octocat", "Hello-World", 1, "Solution details")
        assert comment["id"] == 999
        assert "issuecomment-999" in comment["html_url"]

        closed = await svc.close_issue("octocat", "Hello-World", 1)
        assert closed["state"] == "closed"

