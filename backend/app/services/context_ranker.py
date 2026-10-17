"""Repository context selection and ranking service."""
import os
import re
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.config import settings
from app.core.security import compute_sha256
from app.schemas.repository_context import (
    ContextFile,
    ContextRetrievalLimitations,
    OmittedContextFile,
    RepositoryContext,
    TruncationMetadata,
)
from app.services.github_service import BINARY_EXTENSIONS, GitHubTreeItem

# Vendored, generated, or build directories to exclude
IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".coverage",
    "coverage",
    "vendor",
    "target",
}

# Secret/environment filenames to exclude
IGNORED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
}

# Lockfiles excluded unless explicitly mentioned in issue text
LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "Gemfile.lock",
    "composer.lock",
}

# Repository configuration files prioritized for architectural context
CONFIG_FILENAMES = {
    "pyproject.toml",
    "package.json",
    "setup.py",
    "setup.cfg",
    "cargo.toml",
    "tsconfig.json",
    "requirements.txt",
    "go.mod",
    "pom.xml",
    "build.gradle",
}


class RankedFile(BaseModel):
    """An individual file selected for repository context."""
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Repository relative file path")
    content: str = Field(..., description="UTF-8 decoded file content")
    content_hash: str = Field(..., description="SHA-256 hash of the content")
    relevance_score: float = Field(..., description="Computed relevance score")
    selection_explanation: str = Field(..., description="Reason this file was prioritized")
    size_bytes: int = Field(..., description="Size in bytes")
    estimated_tokens: int = Field(..., description="Character-based token estimate (~4 chars/token)")
    sha256: Optional[str] = Field(default=None, description="SHA-256 hash")
    commit_sha: Optional[str] = Field(default=None, description="Base commit SHA")
    is_truncated: bool = Field(default=False, description="Whether file was truncated")

    @model_validator(mode="after")
    def sync_hashes(self) -> "RankedFile":
        if not self.sha256:
            object.__setattr__(self, "sha256", self.content_hash)
        return self


class OmittedFile(BaseModel):
    """A file considered during ranking but omitted from context."""
    model_config = ConfigDict(extra="forbid")

    path: str
    reason: str  # "binary", "vendored", "secret_ignored", "lockfile_ignored", "oversized", "budget_exhausted"
    size_bytes: Optional[int] = None


class RankedContextPackage(BaseModel):
    """Structured package of ranked repository files within budget limits."""
    model_config = ConfigDict(extra="forbid")

    selected_files: list[RankedFile] = Field(default_factory=list)
    omitted_files: list[OmittedFile] = Field(default_factory=list)
    total_bytes: int = 0
    total_estimated_tokens: int = 0
    budget_bytes: int
    truncated: bool = False
    context_summary: str = Field(..., description="Summary explanation of selection decisions")
    repository_context: Optional[RepositoryContext] = Field(
        default=None,
        description="Strongly typed RepositoryContext model with cryptographic provenance",
    )

    def to_repository_context(
        self,
        repo_owner: str,
        repo_name: str,
        target_branch: str,
        base_commit_sha: str,
        is_fixture: bool = False,
        fixture_identifier: Optional[str] = None,
        total_tree_files: Optional[int] = None,
        total_tree_bytes: Optional[int] = None,
        retrieval_strategy: Optional[str] = None,
    ) -> RepositoryContext:
        """Convert package to strongly typed RepositoryContext with full provenance."""
        context_files: list[ContextFile] = []
        for rf in self.selected_files:
            file_sha = rf.sha256 or rf.content_hash
            context_files.append(
                ContextFile(
                    path=rf.path,
                    content=rf.content,
                    sha256=file_sha,
                    content_hash=file_sha,
                    commit_sha=base_commit_sha,
                    size_bytes=rf.size_bytes,
                    estimated_tokens=rf.estimated_tokens,
                    relevance_score=rf.relevance_score,
                    selection_explanation=rf.selection_explanation,
                    is_truncated=rf.is_truncated,
                )
            )

        omitted_context: list[OmittedContextFile] = [
            OmittedContextFile(path=o.path, reason=o.reason, size_bytes=o.size_bytes)
            for o in self.omitted_files
        ]

        total_tree_f = total_tree_files if total_tree_files is not None else (len(self.selected_files) + len(self.omitted_files))
        total_tree_b = total_tree_bytes if total_tree_bytes is not None else self.total_bytes
        is_partial = self.truncated or len(self.omitted_files) > 0 or (total_tree_f > len(self.selected_files))

        warnings: list[str] = []
        if is_partial:
            warnings.append(
                f"Repository context is partial: {len(self.selected_files)} of {total_tree_f} discovered files included. "
                "Do not assume unlisted files do not exist."
            )
        if self.truncated:
            warnings.append("Context was bounded by configured maximum token/byte budget.")

        reasons = list({o.reason for o in self.omitted_files})

        truncation_meta = TruncationMetadata(
            is_truncated=self.truncated,
            total_files_in_tree=total_tree_f,
            total_bytes_in_tree=total_tree_b,
            selected_files_count=len(self.selected_files),
            omitted_files_count=len(self.omitted_files),
            budget_bytes=self.budget_bytes,
            consumed_bytes=self.total_bytes,
            estimated_total_tokens=self.total_estimated_tokens,
            truncation_reasons=reasons,
        )

        limitations = ContextRetrievalLimitations(
            max_budget_bytes=self.budget_bytes,
            excluded_patterns=sorted(list(IGNORED_DIRECTORIES | IGNORED_FILENAMES)),
            retrieval_strategy=retrieval_strategy or ("test_fixture" if is_fixture else "github_live_tree"),
            is_partial_representation=is_partial,
            warnings=warnings,
        )

        return RepositoryContext(
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=target_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=is_fixture,
            fixture_identifier=fixture_identifier,
            selected_files=context_files,
            omitted_files=omitted_context,
            truncation=truncation_meta,
            limitations=limitations,
            summary=self.context_summary,
        )


class ContextRanker:
    """Deterministic, token-efficient repository context ranking service."""

    def __init__(self, context_budget_bytes: Optional[int] = None):
        self.context_budget = context_budget_bytes or settings.max_repo_context_bytes

    @staticmethod
    def _extract_mentioned_paths_and_symbols(issue_text: str) -> tuple[set[str], set[str]]:
        """Extract explicit file paths and code symbols mentioned in issue title, body, or error traces."""
        # Regex for file paths like path/to/file.ext or file.py
        path_pattern = re.compile(r"\b([a-zA-Z0-9_\-\.\/]+/[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)\b")
        simple_file_pattern = re.compile(r"\b([a-zA-Z0-9_\-]+\.(?:py|ts|tsx|js|jsx|json|yaml|yml|md|toml|rs|go|java|c|cpp|h))\b")

        # Code symbols in backticks `symbol`
        symbol_pattern = re.compile(r"`([a-zA-Z0-9_\-\.]{2,50})`")

        found_paths = set(path_pattern.findall(issue_text))
        found_paths.update(simple_file_pattern.findall(issue_text))
        found_symbols = set(symbol_pattern.findall(issue_text))

        # Normalize paths
        normalized_paths = {p.replace("\\", "/").strip().lower() for p in found_paths}
        normalized_symbols = {s.strip().lower() for s in found_symbols if not s.endswith((".py", ".ts", ".js", ".json"))}

        return normalized_paths, normalized_symbols

    def calculate_file_score(
        self,
        file_path: str,
        issue_text: str,
        mentioned_paths: set[str],
        mentioned_symbols: set[str],
        file_content: Optional[str] = None,
    ) -> tuple[float, str]:
        """
        Compute a deterministic relevance score for a file against the issue context.
        Returns (score, explanation).
        """
        score = 0.0
        explanations = []
        normalized_path = file_path.replace("\\", "/").lower()
        filename = normalized_path.split("/")[-1]

        # 1. Exact path match mentioned in issue
        if any(mentioned == normalized_path or normalized_path.endswith("/" + mentioned) for mentioned in mentioned_paths):
            score += 100.0
            explanations.append("Explicitly mentioned path in issue text (+100)")

        # 2. Filename match mentioned in issue
        elif any(mentioned == filename for mentioned in mentioned_paths):
            score += 60.0
            explanations.append("Explicitly mentioned filename in issue text (+60)")

        # 3. Symbol match in file path or filename
        for symbol in mentioned_symbols:
            if symbol in filename:
                score += 25.0
                explanations.append(f"Symbol '{symbol}' in filename (+25)")
                break
            elif symbol in normalized_path:
                score += 15.0
                explanations.append(f"Symbol '{symbol}' in path (+15)")
                break

        # 4. Keyword matches from issue title/body
        words = set(re.findall(r"\b[a-zA-Z]{3,20}\b", issue_text.lower()))
        matching_words = [w for w in words if w in filename and w not in ("test", "main", "app")]
        if matching_words:
            keyword_score = min(len(matching_words) * 10.0, 30.0)
            score += keyword_score
            explanations.append(f"Matched keywords in filename: {', '.join(matching_words[:3])} (+{keyword_score})")

        # 5. Test files matching problem domain
        is_test = "test" in filename or "spec" in filename or "/tests/" in normalized_path
        if is_test:
            # If the base name matches any mentioned path or symbol
            if score > 0:
                score += 20.0
                explanations.append("Associated test file (+20)")
            else:
                score += 5.0
                explanations.append("Repository test file (+5)")

        # 6. Repository configuration file
        if filename.lower() in CONFIG_FILENAMES:
            score += 15.0
            explanations.append(f"Repository configuration file '{filename}' (+15)")

        # 7. Content & import dependency inspection if available
        if file_content:
            content_lower = file_content.lower()

            # Check for import dependencies referencing mentioned modules
            import_matches = []
            for path in mentioned_paths:
                mod_name = path.replace("/", ".").rsplit(".", 1)[0]
                short_name = mod_name.split(".")[-1]
                if short_name and short_name not in ("py", "ts", "js") and (
                    f"import {short_name}" in content_lower
                    or f"from {short_name}" in content_lower
                    or f"from .{short_name}" in content_lower
                    or f"require('{short_name}" in content_lower
                ):
                    import_matches.append(short_name)
            if import_matches:
                score += 20.0
                explanations.append(f"Imports mentioned module ({', '.join(import_matches[:2])}) (+20)")

            # Check for mentioned symbol hits in content
            if score > 0:
                symbol_hits = sum(1 for sym in mentioned_symbols if sym in content_lower)
                if symbol_hits > 0:
                    content_bonus = min(symbol_hits * 5.0, 20.0)
                    score += content_bonus
                    explanations.append(f"Contains {symbol_hits} mentioned symbols in content (+{content_bonus})")

        if not explanations:
            explanations.append("General repository source file (+1)")
            score = 1.0

        return score, "; ".join(explanations)

    def filter_tree(
        self,
        tree_items: list[GitHubTreeItem],
        mentioned_paths: set[str],
    ) -> tuple[list[GitHubTreeItem], list[OmittedFile]]:
        """Filter out binary, vendored, build, and secret files from tree items."""
        candidate_items: list[GitHubTreeItem] = []
        omitted_files: list[OmittedFile] = []

        for item in tree_items:
            if item.type != "blob":
                continue

            path = item.path.replace("\\", "/")
            parts = path.split("/")
            filename = parts[-1]
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            # Check binary extension
            if ext in BINARY_EXTENSIONS:
                omitted_files.append(OmittedFile(path=path, reason="binary"))
                continue

            # Check ignored directory
            if any(part in IGNORED_DIRECTORIES for part in parts[:-1]):
                omitted_files.append(OmittedFile(path=path, reason="vendored"))
                continue

            # Check secret / credentials files
            if filename in IGNORED_FILENAMES or ext in (".key", ".pem", ".p12", ".crt", ".cert"):
                omitted_files.append(OmittedFile(path=path, reason="secret_ignored"))
                continue

            # Check lockfiles (keep only if explicitly mentioned)
            if filename in LOCKFILES:
                if not any(mentioned == filename or mentioned == path.lower() for mentioned in mentioned_paths):
                    omitted_files.append(OmittedFile(path=path, reason="lockfile_ignored"))
                    continue

            candidate_items.append(item)

        return candidate_items, omitted_files

    def rank_and_package(
        self,
        files_data: list[dict[str, Any]],  # list of dicts with 'path' and 'content'
        issue_title: str,
        issue_body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        target_branch: Optional[str] = None,
        base_commit_sha: Optional[str] = None,
        is_fixture: bool = False,
        fixture_identifier: Optional[str] = None,
        total_tree_files: Optional[int] = None,
        total_tree_bytes: Optional[int] = None,
        omitted_from_tree: Optional[list[OmittedFile]] = None,
    ) -> RankedContextPackage:
        """
        Rank candidate files and package them within the configured context budget.
        Each entry in files_data must be {'path': str, 'content': str}.
        """
        issue_text = f"{issue_title}\n{issue_body or ''}\n{' '.join(labels or [])}"
        mentioned_paths, mentioned_symbols = self._extract_mentioned_paths_and_symbols(issue_text)

        scored_candidates: list[tuple[float, str, str, str]] = []  # (score, path, explanation, content)
        omitted: list[OmittedFile] = list(omitted_from_tree or [])

        for item in files_data:
            path = item["path"].replace("\\", "/")
            content = item["content"]
            parts = path.split("/")
            filename = parts[-1]
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            # Verify exclusions
            if ext in BINARY_EXTENSIONS:
                omitted.append(OmittedFile(path=path, reason="binary"))
                continue
            if any(part in IGNORED_DIRECTORIES for part in parts[:-1]):
                omitted.append(OmittedFile(path=path, reason="vendored"))
                continue
            if filename in IGNORED_FILENAMES or ext in (".key", ".pem", ".p12", ".crt"):
                omitted.append(OmittedFile(path=path, reason="secret_ignored"))
                continue
            if filename in LOCKFILES and not any(m == filename for m in mentioned_paths):
                omitted.append(OmittedFile(path=path, reason="lockfile_ignored"))
                continue

            score, explanation = self.calculate_file_score(
                file_path=path,
                issue_text=issue_text,
                mentioned_paths=mentioned_paths,
                mentioned_symbols=mentioned_symbols,
                file_content=content,
            )
            scored_candidates.append((score, path, explanation, content))

        # Deterministic sorting: highest score first, then path alphabetically
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))

        selected_files: list[RankedFile] = []
        current_bytes = 0
        truncated = False

        for score, path, explanation, content in scored_candidates:
            file_bytes = len(content.encode("utf-8"))

            # Check if adding this file exceeds the context budget
            if current_bytes + file_bytes > self.context_budget:
                omitted.append(OmittedFile(path=path, reason="budget_exhausted", size_bytes=file_bytes))
                truncated = True
                continue

            content_hash = compute_sha256(content)
            # Estimate tokens: approx 4 characters per token (heuristic for English/code)
            estimated_tokens = max(1, len(content) // 4)

            selected_files.append(
                RankedFile(
                    path=path,
                    content=content,
                    content_hash=content_hash,
                    sha256=content_hash,
                    commit_sha=base_commit_sha,
                    relevance_score=round(score, 2),
                    selection_explanation=explanation,
                    size_bytes=file_bytes,
                    estimated_tokens=estimated_tokens,
                )
            )
            current_bytes += file_bytes

        total_tokens = sum(f.estimated_tokens for f in selected_files)
        summary = (
            f"Selected {len(selected_files)} files ({current_bytes} bytes, ~{total_tokens} est. tokens). "
            f"Omitted {len(omitted)} files. Truncated={truncated}."
        )

        pkg = RankedContextPackage(
            selected_files=selected_files,
            omitted_files=omitted,
            total_bytes=current_bytes,
            total_estimated_tokens=total_tokens,
            budget_bytes=self.context_budget,
            truncated=truncated,
            context_summary=summary,
        )

        if base_commit_sha and repo_owner and repo_name and target_branch:
            pkg.repository_context = pkg.to_repository_context(
                repo_owner=repo_owner,
                repo_name=repo_name,
                target_branch=target_branch,
                base_commit_sha=base_commit_sha,
                is_fixture=is_fixture,
                fixture_identifier=fixture_identifier,
                total_tree_files=total_tree_files,
                total_tree_bytes=total_tree_bytes,
            )

        return pkg

    def build_repository_context(
        self,
        files_data: list[dict[str, Any]],
        issue_title: str,
        issue_body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        repo_owner: str = "unknown",
        repo_name: str = "repo",
        target_branch: str = "main",
        base_commit_sha: str = "0000000000000000000000000000000000000000",
        is_fixture: bool = False,
        fixture_identifier: Optional[str] = None,
        total_tree_files: Optional[int] = None,
        total_tree_bytes: Optional[int] = None,
        omitted_from_tree: Optional[list[OmittedFile]] = None,
        retrieval_strategy: Optional[str] = None,
    ) -> RepositoryContext:
        """
        Rank candidate files and package directly into a cryptographically grounded RepositoryContext.
        """
        pkg = self.rank_and_package(
            files_data=files_data,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=labels,
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=target_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=is_fixture,
            fixture_identifier=fixture_identifier,
            total_tree_files=total_tree_files,
            total_tree_bytes=total_tree_bytes,
            omitted_from_tree=omitted_from_tree,
        )

        repo_ctx = pkg.to_repository_context(
            repo_owner=repo_owner,
            repo_name=repo_name,
            target_branch=target_branch,
            base_commit_sha=base_commit_sha,
            is_fixture=is_fixture,
            fixture_identifier=fixture_identifier,
            total_tree_files=total_tree_files,
            total_tree_bytes=total_tree_bytes,
            retrieval_strategy=retrieval_strategy,
        )
        repo_ctx.verify_integrity()
        return repo_ctx
