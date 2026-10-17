"""Unit tests for ContextRanker scoring, filtering, and budget packaging."""
from app.services.context_ranker import ContextRanker
from app.services.github_service import GitHubTreeItem


def test_mentioned_paths_and_symbols_extraction():
    ranker = ContextRanker()
    text = (
        "Bug in `validate_token` inside src/auth/token_handler.py. "
        "Also see models.py line 40 when using `AuthException`."
    )
    paths, symbols = ranker._extract_mentioned_paths_and_symbols(text)
    assert "src/auth/token_handler.py" in paths
    assert "models.py" in paths
    assert "validate_token" in symbols
    assert "authexception" in symbols


def test_calculate_file_score_priorities():
    ranker = ContextRanker()
    issue_text = "Fix failure in src/core/auth.py for symbol `VerifyUser`"
    paths, symbols = ranker._extract_mentioned_paths_and_symbols(issue_text)

    # 1. Exact match
    score1, exp1 = ranker.calculate_file_score("src/core/auth.py", issue_text, paths, symbols)
    assert score1 >= 100.0
    assert "Explicitly mentioned" in exp1

    # 2. Symbol match
    score2, exp2 = ranker.calculate_file_score("src/user/verifyuser_handler.py", issue_text, paths, symbols)
    assert score2 >= 25.0
    assert "Symbol 'verifyuser'" in exp2

    # 3. Test file for mentioned module
    score3, exp3 = ranker.calculate_file_score("tests/test_auth.py", issue_text, paths, symbols)
    assert score3 > 20.0
    assert "test" in exp3.lower()

    # 4. Unrelated file
    score4, _ = ranker.calculate_file_score("docs/contributing.md", issue_text, paths, symbols)
    assert score4 < 10.0


def test_filter_tree_excludes_secrets_binaries_vendored():
    ranker = ContextRanker()
    items = [
        GitHubTreeItem(path="src/main.py", mode="100644", type="blob", sha="1"),
        GitHubTreeItem(path="node_modules/express/index.js", mode="100644", type="blob", sha="2"),
        GitHubTreeItem(path=".env", mode="100644", type="blob", sha="3"),
        GitHubTreeItem(path="assets/banner.png", mode="100644", type="blob", sha="4"),
        GitHubTreeItem(path="package-lock.json", mode="100644", type="blob", sha="5"),
    ]
    candidates, omitted = ranker.filter_tree(items, mentioned_paths=set())
    candidate_paths = [c.path for c in candidates]
    assert "src/main.py" in candidate_paths
    assert "node_modules/express/index.js" not in candidate_paths
    assert ".env" not in candidate_paths
    assert "assets/banner.png" not in candidate_paths
    assert "package-lock.json" not in candidate_paths

    omitted_map = {o.path: o.reason for o in omitted}
    assert omitted_map["node_modules/express/index.js"] == "vendored"
    assert omitted_map[".env"] == "secret_ignored"
    assert omitted_map["assets/banner.png"] == "binary"
    assert omitted_map["package-lock.json"] == "lockfile_ignored"


def test_rank_and_package_enforces_budget_and_truncates():
    # Set small budget of 200 bytes
    ranker = ContextRanker(context_budget_bytes=200)

    files_data = [
        {"path": "src/target.py", "content": "x = 1\n" * 10},  # ~60 bytes, exact mention
        {"path": "src/other1.py", "content": "y = 2\n" * 20},  # ~120 bytes
        {"path": "src/other2.py", "content": "z = 3\n" * 20},  # ~120 bytes
    ]

    pkg = ranker.rank_and_package(
        files_data=files_data,
        issue_title="Bug in src/target.py",
        issue_body="Please resolve immediately",
    )

    # First file should be selected
    selected_paths = [f.path for f in pkg.selected_files]
    assert "src/target.py" in selected_paths
    assert pkg.total_bytes <= 200
    assert pkg.truncated is True
    assert any(o.reason == "budget_exhausted" for o in pkg.omitted_files)


def test_deterministic_ranking_order():
    ranker = ContextRanker()
    files_data = [
        {"path": "src/b_equal.py", "content": "print('b')"},
        {"path": "src/a_equal.py", "content": "print('a')"},
    ]

    # Run multiple times to verify identical ordering
    res1 = ranker.rank_and_package(files_data, "General issue")
    res2 = ranker.rank_and_package(files_data, "General issue")

    assert [f.path for f in res1.selected_files] == [f.path for f in res2.selected_files]
    # Tie-breaking by alphabetical path: a before b
    assert res1.selected_files[0].path == "src/a_equal.py"
    assert res1.selected_files[1].path == "src/b_equal.py"


def test_config_file_scoring():
    ranker = ContextRanker()
    score, exp = ranker.calculate_file_score(
        file_path="pyproject.toml",
        issue_text="General feature request",
        mentioned_paths=set(),
        mentioned_symbols=set(),
    )
    assert score >= 15.0
    assert "Repository configuration file" in exp


def test_import_dependency_scoring():
    ranker = ContextRanker()
    content = "from auth import token_validator\nimport os\n"
    score, exp = ranker.calculate_file_score(
        file_path="src/api.py",
        issue_text="Fix bug in auth/token_validator.py",
        mentioned_paths={"auth/token_validator.py"},
        mentioned_symbols=set(),
        file_content=content,
    )
    assert score >= 20.0
    assert "Imports mentioned module" in exp
