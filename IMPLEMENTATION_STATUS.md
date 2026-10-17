# DevSquad Implementation Status

## Current Phase
**Sub-Milestone 7: Final Integration Audit, Functional Verification & Professional UI Polish** — **COMPLETE & DEMONSTRATION-READY**
- **Backend Tests**: 179 passed, 3 skipped, 0 failed in 67.10s across all unit, integration, and security suites.
- **Frontend Tests**: 17 passed, 0 failed in 24.4ms in `frontend/tests/frontend.test.mjs`.
- **Static Analysis**: TypeScript 0 errors (`npx tsc --noEmit`), ESLint clean, production builds passing.
- **Authoritative Diagnostics**: Live database connectivity reporting Alembic migration head `1a0c41410573`, Groq LLM inference (`openai/gpt-oss-120b`), and honest Docker status with AST fallback.
- **Data Provenance**: Explicit badges differentiating `LOCAL DATABASE` SQLite fixtures from `LIVE GITHUB` remote sync.
- **Patch Laboratory**: Strict isolation of failed patches (`stock.py` concurrency failure) with human approval locked, versus passed patches (`inventory.py`) with cryptographic review.
- **UI Integrity**: Obsidian & Forge Lime responsive design system with fluid maintainer truncation and zero layout regressions.

---

## Completed Deliverables

### Phase 1: Clean Foundation and Schema Setup
1. **Repository Structure**: Clean modular architecture established with `.gitignore` and `.env.example`.
2. **Centralized Configuration (`app/core/config.py`)**: Pydantic V2 Settings with secret masking (`safe_dict()`) and `get_settings()` helper.
3. **Security & Logging (`app/core/security.py`, `app/core/logging.py`)**: Secret redaction, relative path traversal checks, canonical SHA-256 calculation, and `SecretRedactionFilter`.
4. **Database Models (`app/db/models/`)**: Reusable async engine, SQLite foreign key enforcement, and 8 entities:
   - `User`, `Repository`, `Issue`, `Run`, `AgentLog`, `Patch` (immutable revisions), `PullRequest`, `ApprovalRecord` (audit log bound to exact patch SHA-256 hash).
5. **Alembic Migrations (`backend/alembic/`)**: Initial migration generated and applied cleanly (`1a0c41410573_initial_schema_setup.py`).
6. **API Contracts (`app/schemas/`)**: Pydantic V2 domain and request/response models.
7. **FastAPI Endpoints (`app/api/`)**: Real database `SELECT 1` ping, honest Docker availability reporting, honest LLM readiness check, and CRUD endpoints for repositories, issues, and runs.

### Phase 2: GitHub Ingestion and LLM Provider Abstraction
1. **GitHub Integration Layer (`app/services/github_service.py`)**:
   - Asynchronous HTTP client using `httpx.AsyncClient` with reusable connection pooling and timeouts.
   - Operations: `get_repository`, `get_issue`, `list_issues` (excluding PRs), `get_issue_comments`, `get_repository_tree` (recursive tree retrieval), `get_file_content`, `get_branch`, and `get_commit`.
   - Automatic base64 decoding for repository files, null-byte binary check, and size limit protection.
   - Rate limit inspection and handling (`x-ratelimit-remaining`, `x-ratelimit-reset`, `retry-after`).
   - Typed error hierarchy: `GitHubAuthError`, `GitHubRateLimitError`, `GitHubResourceNotFoundError`, `GitHubAPIError`.
2. **Repository Context Ranker (`app/services/context_ranker.py`)**:
   - Token-efficient, deterministic context-selection service.
   - Signal extraction: extracts file paths and backticked code symbols from issue title, body, and comments.
   - Multi-signal scoring: exact path matches (+100), filename matches (+60), code symbols in path/filename (+15 to +25), problem domain keywords (+10 to +30), configuration files (+15), import dependency affinity (+20), and corresponding test files (+20).
   - Strict exclusions: filters binary files, vendored/generated directories, secrets, and lockfiles.
   - Budget management: enforces configurable context budget, token estimates, and deterministic sorting.
3. **LLM Provider Abstraction (`app/services/llm/`)**:
   - `LLMProvider` Abstract Base Class defining standard `generate_structured` interface.
   - `GeminiProvider` (`google-genai` SDK) with structured JSON generation and transient 429 exponential backoff retries.
   - `OpenAIProvider` (`openai` SDK) with JSON mode and transient rate limit exponential backoff retries.
   - Strict factory resolution (`get_llm_provider`).
   - `safety.py` XML boundary encapsulation (`<UNTRUSTED_ISSUE>`, `<UNTRUSTED_REPOSITORY_FILE>`).
4. **Live Integration Test Harness (`tests/integration/test_live_integrations.py`)**:
   - Guarded by `DEVSQUAD_RUN_LIVE_TESTS=1` for isolated, deterministic offline test runs.

### Phase 3: Four Independent Multi-Agent Services
1. **Planner Agent (`app/services/agents/planner.py`)**:
   - Independent asynchronous service producing validated `StructuredPlan` objects.
   - Enforces XML-isolated prompt boundaries (`<UNTRUSTED_ISSUE>`, `<UNTRUSTED_REPOSITORY_FILE>`).
   - Grounding: strictly relies on provided repository context; validates target file paths with `is_safe_relative_path`.
   - Distinguishes empirical facts from hypotheses; records any unranked or missing target files in `uncertainties`.
   - Zero side-effects: does not execute code, write files, or publish changes.
2. **Coder Agent (`app/services/agents/coder.py`)**:
   - Independent asynchronous service generating minimal unified diff patches (`PatchItem`).
   - Enforces unified diff parsing and validation via `diff_utils`.
   - Rejects path traversal (`..`) and absolute paths (`/etc/...`, `C:\...`).
   - Enforces maximum patch size limit (`settings.max_patch_size_bytes`).
   - Verifies base-content consistency before applying diffs.
   - Pre-modification file SHA-256 computation (`file_hashes`).
   - Safe disposable workspace patch verification: verifies diff applies cleanly before accepting patch.
   - Application-side SHA-256 calculation (`compute_sha256(unified_diff.strip())`). Never trusts model-supplied hashes.
   - Incorporates reviewer/tester feedback during multi-revision repair cycles.
3. **Sandbox Tester Agent (`app/services/agents/tester.py`)**:
   - **Docker Mode**: When Docker daemon is operational:
     - Disposable container execution with non-root user (`user="1000:1000"`).
     - Network disabled by default (`network_mode="none"`).
     - Resource limits: CPU limit (`nano_cpus`), memory limit (`mem_limit="1g"`), PID limit (`pids_limit=100`).
     - Hardened isolation: `privileged=False`, no host mounts, no Docker socket mount.
     - Whitelist enforcement for test execution commands (`pytest`, `python -m unittest`, `npm test`, `go test`, `cargo test`). Rejects arbitrary model shell injection.
     - Guaranteed container cleanup in `finally` block (`container.remove(force=True)`).
   - **Static AST Fallback Mode**: When Docker is unavailable (current Windows environment):
     - Safe static Python AST parsing (`ast.parse`) and patch verification in-memory.
     - Never executes untrusted repository code on the host.
     - Honest reporting: returns `status="PARTIAL_VALIDATION"` or `"SANDBOX_UNAVAILABLE"`.
     - Non-negotiable honesty rule: AST validation success is **NEVER** reported as `TESTS_PASSED`.
4. **Independent Reviewer Agent (`app/services/agents/reviewer.py`)**:
   - Independent critique service evaluating patches against original issue, plan, and validation results.
   - Multi-dimensional review: correctness, acceptance criteria, security vulnerabilities, regressions, input validation, error handling, performance, maintainability, scope creep.
   - Structured findings with severity levels: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.
   - Strict rule enforcement: if CRITICAL or HIGH findings exist, recommendation cannot be `approve` (forces `request_changes`).
   - If sandbox was unavailable, automatically includes limitation caveat in `unresolved_risks`.
   - Advisory only: reviewer recommendation never overrides mandatory human approval.
5. **Pure Python Diff Utilities (`app/services/agents/diff_utils.py`)**:
   - OS-independent, deterministic unified diff parser and hunk patch applier without external tool dependencies.
   - Validates diff safety and detects hunk context mismatches (`PatchHunkMismatchError`).
6. **Bounded Repair Support & Audit Persistence (`app/services/agents/repair.py`)**:
   - Typed data models: `RepairCycleState`, `RevisionRecord`.
   - Tracks revisions immutably up to configurable `max_revisions` (`settings.max_agent_retries`).
   - Extracts synthesized repair feedback for CoderAgent revisions.
   - Database persistence helpers: `record_patch_revision` (persisting `Patch` entity) and `log_agent_event` (persisting `AgentLog` audit trail).

### Phase 4: LangGraph Orchestrator, Workflow State Management, Checkpointing, and Recovery
1. **Typed Workflow State & Enums (`app/orchestration/state.py`)**:
   - Enums: `WorkflowStatus` (`PENDING`, `RUNNING`, `WAITING_FOR_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`, `INTERRUPTED`) and `WorkflowStage` (`INPUT_VALIDATION`, `CONTEXT_PREPARATION`, `PLANNING`, `CODING`, `TESTING`, `REVIEWING`, `REPAIRING`, `AWAITING_APPROVAL`, `FINALIZING`).
   - `DevSquadState`: LangGraph-compatible `TypedDict` carrying `run_id`, `thread_id`, `repository_id`, `issue_id`, `status`, `current_stage`, `plan`, `current_patch`, `patch_revision`, `test_result`, `review_result`, `repair_attempts`, `max_repair_attempts`, `validation_status`, `metadata`, and `repair_feedback`.
   - Factory `create_initial_state(...)` initializes clean state with configurable repair limits.
2. **Checkpointer Infrastructure (`app/orchestration/checkpointer.py`)**:
   - Reusable async checkpointer factory `get_async_checkpointer(db_path=...)`.
   - Persistent SQLite checkpointing using `AsyncSqliteSaver` bound to thread ID (`run_id`).
   - In-memory fallback (`InMemorySaver`) for lightweight unit testing.
3. **Workflow Nodes (`app/orchestration/nodes.py`)**:
   - `validate_input_node`: Validates Run, Repository, and Issue existence, verifies status, updates stage to `INPUT_VALIDATION`.
   - `context_preparation_node`: Retrieves file tree and packages ranked context via `ContextRanker`.
   - `planner_node`: Generates structured plan via `PlannerAgent`, persists summary and audit trail to database.
   - `coder_node`: Generates minimal diff patch via `CoderAgent`, persists immutable `Patch` revision with canonical SHA-256 hash.
   - `sandbox_tester_node`: Executes tests via `SandboxTesterAgent` (Docker container or AST fallback), persists result and logs.
   - `reviewer_node`: Evaluates patch via `ReviewerAgent`, validates findings, checks severity overrides, updates state.
   - `finalization_node`: Transitions run to `WAITING_FOR_APPROVAL` or `FAILED`, updates run finish timestamp, persists audit log.
   - `NodeDependencies`: Modular dependency injection container enabling mock injection during tests without monkey-patching globals.
4. **Conditional Edge Routing (`app/orchestration/routing.py`)**:
   - Strict decision routing functions: `route_after_validation`, `route_after_context`, `route_after_planner`, `route_after_coder`, `route_after_tester`, `route_after_reviewer`.
   - Bounded repair cycle logic: If tests fail or reviewer requests changes, loops back to `coder_node` as long as `repair_attempts < max_repair_attempts`. Once attempt limit is reached, routes directly to `finalization_node`.
   - Security & Quality Gate: Critical or High review findings strictly prevent progression to approval, forcing repair or failure.
5. **StateGraph Assembly (`app/orchestration/graph.py`)**:
   - `build_devsquad_graph()` builds the complete directed cyclic graph with entry and conditional exit edges.
   - `compile_devsquad_graph(checkpointer=...)` compiles graph with async checkpointing support.
6. **Orchestrator Service Facade (`app/orchestration/service.py`)**:
   - `DevSquadOrchestrator` central service providing `start_run`, `resume_run`, `cancel_run`, and `get_run_state`.
   - Handles thread ID configuration, state synchronization with SQLAlchemy database, and clean error handling.
7. **Orchestration API Endpoints (`app/api/routes/runs.py`)**:
   - `POST /api/v1/runs/{run_id}/start`: Initiates workflow execution.
   - `POST /api/v1/runs/{run_id}/resume`: Resumes an interrupted run from latest checkpoint.
   - `POST /api/v1/runs/{run_id}/cancel`: Cancels an in-flight run.
   - `GET /api/v1/runs/{run_id}/state`: Retrieves current LangGraph state snapshot and checkpoint values.
   - `GET /api/v1/runs/{run_id}/events`: Retrieves agent execution event stream for the run.

### Sub-Milestone 1: Grounded RepositoryContext & Provenance Binding
1. **Cryptographic RepositoryContext Schema (`app/schemas/repository_context.py`)**:
   - `ContextFile`: Normalized repository-relative file paths, SHA-256 content verification, explicit immutable `commit_sha`, size in bytes, estimated tokens, and per-file truncation flags.
   - `OmittedContextFile`: Captures discarded candidate files alongside deterministic exclusion rationale (`budget_exhausted`, `binary`, `vendored`, `secret_ignored`, `lockfile_ignored`).
   - `TruncationMetadata`: Tracks total tree files/bytes, selected files, omitted counts, budget ceiling, consumed bytes, and explicit truncation reasons.
   - `ContextRetrievalLimitations`: Discloses retrieval strategy (`github_live_tree` or `test_fixture`), partial representation flag, and advisories for downstream agents.
   - `RepositoryContext`: Immutable snapshot model enforcing commit SHA hex validation (production 7–40 chars) vs explicit `fixture_identifier` for test fixtures.
   - **Revision Consistency Enforcement**: Enforces that 100% of selected files match `base_commit_sha`. Rejects mixing commits within one context snapshot.
   - **Path Traversal & Safety**: Rejects traversal attempts (`..`, `.`), absolute paths (`/`, `\`), Windows drive letters (`C:`), and null bytes.
   - **Self-Verifying Integrity Guard**: `verify_integrity()` cryptographically recalculates SHA-256 for all selected files against their content and verifies revision consistency.
2. **Context Ranker Integration (`app/services/context_ranker.py`)**:
   - `RankedFile` backward compatibility: Added `sha256`, `commit_sha`, and `is_truncated`.
   - `RankedContextPackage.to_repository_context(...)`: Converts ranked context to verified `RepositoryContext`.
   - `ContextRanker.build_repository_context(...)`: Deterministically constructs and validates `RepositoryContext`.
3. **Orchestration State & Integrity Guards (`app/orchestration/state.py`, `app/orchestration/nodes.py`)**:
   - `DevSquadState`: Added `repository_context: Optional[Dict[str, Any]]`.
   - `context_preparation_node`: Populates and validates `RepositoryContext` for both live GitHub runs and isolated test fixtures.
   - `planner_node` & `coder_node`: Guard downstream agent execution with `verify_integrity()`, failing fast with `CONTEXT_INTEGRITY_COMPROMISED` if any tampering or hash mismatch is detected.
4. **Sub-Milestone 1 Unit & Regression Suite (`tests/unit/test_repository_context.py`)**:
   - 11 comprehensive tests validating production SHA, fixture identifiers, hash mismatch rejections, commit revision consistency, path traversal guards, truncation metadata warnings, backward compatibility, and workflow node guards.

### Sub-Milestone 2: Strict Invalidation & Anti-Repetition Repair Engine
1. **Deterministic Patch Canonicalization & Provenance (`app/services/agents/diff_utils.py`)**:
   - `canonicalize_unified_diff(diff_text)`: Normalizes line endings (`\r\n` -> `\n`), trims trailing whitespace from header and content lines, collapses trailing blank lines, and guarantees deterministic formatting.
   - `compute_canonical_patch_hash(diff_text)`: Computes SHA-256 over normalized diff content.
   - `compute_canonical_patch_id(base_commit_sha, diff_text)`: Cryptographically binds the canonical patch hash to the immutable base commit SHA (`f"{base_commit_sha}:{canonical_hash}"`).
2. **Atomic Evidence Invalidation Invariant (`app/orchestration/nodes.py`)**:
   - When `coder_node` produces or updates a patch revision, all prior dependent validation evidence is atomically wiped:
     - `test_result = None`
     - `review_result = None`
     - `validation_status = "PENDING_VALIDATION"`
     - `approval_status = "PENDING"`
     - `repair_feedback = None`
   - Guarantees zero stale evidence can ever survive into subsequent pipeline stages.
3. **Cryptographic Identity Binding Across Evidence Models (`app/schemas/`)**:
   - `TestResult`: Bound to `run_id`, `repository_id`, `canonical_patch_id`, `patch_hash`, `patch_revision`, `base_commit_sha`, and `validation_status`.
   - `ReviewResponse`: Bound to `run_id`, `repository_id`, `canonical_patch_id`, `patch_hash`, `patch_revision`, `base_commit_sha`, and `reviewed_at`.
4. **Anti-Repetition Repair Engine (`app/schemas/repair_registry.py`)**:
   - `FailedPatchEntry`: Captures `run_id`, `repository_id`, `base_commit_sha`, `patch_hash`, `canonical_patch_id`, `revision`, `failure_category`, `diagnostic_fingerprint`, `validation_environment`, `recorded_at`, and `details`.
   - `FailedPatchRegistry`: Records failed patches from `sandbox_tester_node` (`TEST_FAILED`) and `reviewer_node` (`REVIEW_REJECTED` / `CRITICAL_FINDINGS`).
   - Duplicate Detection: When `coder_node` generates a patch matching an entry in `FailedPatchRegistry` under equivalent circumstances (`(run_id, base_commit_sha, patch_hash, environment)`), execution immediately halts fail-closed with `DUPLICATE_FAILED_PATCH`, preventing runaway repair cycles.
5. **Bounded Execution Duration & Hard Timeouts (`app/core/config.py`, `app/orchestration/routing.py`)**:
   - Centralized `settings.max_run_duration_seconds: int = 3600` (1 hour default).
   - In `route_after_reviewer`, elapsed workflow execution duration is checked against this ceiling. If exceeded, halts fail-closed with `TIMEOUT_EXCEEDED`.
6. **Fail-Closed Evidence Verification at Finalization & Human Approval (`app/orchestration/nodes.py`, `app/api/routes/runs.py`)**:
   - `finalization_node`: Verifies that `test_patch_hash == current_patch.content_hash`, `review_patch_hash == current_patch.content_hash`, and base commit SHAs match. Rejects with `Stale validation evidence` or `Base revision mismatch` if any discrepancy exists.
   - `POST /api/v1/runs/{run_id}/approve`: Validates that the target patch is the active, latest revision (rejects superseded revisions with 409 Conflict), verifies that `validation_status` is completed/eligible, and strictly enforces cryptographic match between submitted `patch_hash` and stored `patch.content_hash`.
7. **Verification Suite (`backend/tests/unit/test_patch_invalidation_and_registry.py`)**:
   - 12 comprehensive unit and regression tests covering all 9 required edge cases:
     1. `test_canonical_patch_hash_stability`: Whitespace and CRLF invariance.
     2. `test_patch_change_atomically_invalidates_validation_evidence`: Atomic clearing of test_result, review_result, approval_status.
     3. `test_stale_validation_or_review_rejected_at_finalization`: Finalization rejection on hash mismatch.
     4. `test_approval_rejects_superseded_or_stale_patch`: 409 Conflict on superseded revision or unvalidated status.
     5. `test_anti_repetition_registry_detects_duplicate_failure`: Registry catches duplicate failing patch.
     6. `test_anti_repetition_registry_permits_different_run`: Scoped isolation across distinct runs.
     7. `test_anti_repetition_registry_permits_different_base_revision`: Permits identical patch on rebased commit.
     8. `test_reviewer_node_rejects_stale_validation_evidence`: Fail-fast with STALE_VALIDATION_EVIDENCE without calling LLM.
     9. `test_create_initial_state_and_invariants`: Clean initialization defaults.
     10. `test_failed_patch_registry_serialization_survives_checkpoint_roundtrip`: LangGraph checkpoint serialization.
     11. `test_cancellation_during_repair_halts_coder`: Cancellation honored immediately.
     12. `test_route_after_reviewer_bounds_repairs_and_detects_timeout`: Hard timeout and retry limits enforced.

### Sub-Milestone 3: Grounded Planner with Line-Span Citations & File Verification
1. **Typed Evidence-Reference Schema (`app/schemas/evidence.py`)**:
   - `EvidencePurpose` enum: `root_cause`, `implementation_target`, `dependency`, `test`, `risk`.
   - `EvidenceReference`: Cryptographically grounded citation referencing `file_path` (safe relative path), `start_line` and `end_line` (1-indexed, inclusive, validated with $1 \le \text{start} \le \text{end}$), `file_sha256` (exact content hash), `base_commit_sha` (exact revision snapshot), `repo_owner`/`repo_name`, optional `excerpt` and `symbol`.
   - `PlanVerificationIssue` & `PlanVerificationResult`: Structured diagnostics reporting machine-readable issue codes (`OUT_OF_BOUNDS_LINE_SPAN`, `FILE_NOT_IN_CONTEXT`, `FILE_HASH_MISMATCH`, `COMMIT_MISMATCH`, `REPOSITORY_MISMATCH`, `EXCERPT_MISMATCH`, `UNSAFE_FILE_PATH`, `UNGROUNDED_TARGET_FILE`).
2. **Strengthened StructuredPlan Schema (`app/schemas/plan.py`)**:
   - Added:
     - `problem_interpretation` & `root_cause_hypothesis`: Distinguishes verified facts from working hypotheses.
     - `evidence_citations`: List of verified `EvidenceReference` citations.
     - `target_files`: Explicit list of target file paths to be modified or created.
     - `regression_test_strategy`: Concrete verification strategy to prevent regressions.
     - `needs_additional_context`, `additional_context_request`, and `declined_reason`: Explicit protocols for requesting missing files/symbols or halting safely.
     - `is_verified`: Boolean flag confirming all citations have passed mathematical and contextual verification.
   - Preserves complete backward compatibility with existing tests via Pydantic V2 `@model_validator(mode="before")`.
3. **Deterministic Evidence Verification Engine (`app/services/agents/evidence_verifier.py`)**:
   - `verify_plan_evidence(...)`: Deterministically evaluates 100% of citations against the verified `RepositoryContext`:
     - Asserts repository identity and base commit SHA match active run.
     - Asserts cited file path exists in `context.selected_files`.
     - Asserts `file_sha256` strictly matches context file hash.
     - Asserts line spans are within bounds ($1 \le \text{start} \le \text{end} \le \text{total\_lines}$).
     - Asserts quoted excerpts match actual source content within the cited line span.
     - Emits truncation warnings if citations originate from truncated files.
     - Asserts all proposed target files are grounded in context or explicitly documented as newly created files.
   - `is_plan_invalidated_by_context(...)`: Detects context mutations/rebases and marks verified plans invalidated (`STALE_PLAN_EVIDENCE`).
4. **Fail-Closed Verification Across Orchestrator Nodes (`app/orchestration/nodes.py`)**:
   - `planner_node`: Runs `verify_plan_evidence`. Halts fail-closed with `PLAN_EVIDENCE_VERIFICATION_FAILED` if any citation or target file is ungrounded or fabricated.
   - `coder_node`: Pre-execution guard blocks patch generation if plan evidence is unverified or invalidated by modified context snapshot.
   - `finalization_node`: Cryptographic evidence guard re-verifies plan citations before transitioning to `WAITING_FOR_APPROVAL`.
5. **Prompt Injection & Safety Defenses (`app/services/agents/planner.py`, `app/services/llm/safety.py`)**:
   - Untrusted issue descriptions and repository code are strictly encapsulated within `<UNTRUSTED_ISSUE>` and `<UNTRUSTED_REPOSITORY_FILE>` XML boundaries.
   - System prompts forbid following instructions embedded in untrusted repository files that contradict system policy.
6. **Verification Suite (`backend/tests/unit/test_grounded_planner_and_evidence.py`)**:
   - 14 comprehensive unit and regression tests covering all target requirements:
     1. `test_valid_line_span_evidence_passes_verification`: Valid citations pass.
     2. `test_out_of_bounds_line_span_rejected`: Out of bounds line spans caught.
     3. `test_inverted_line_span_rejected_at_schema`: Inverted line ranges fail schema validation.
     4. `test_missing_file_reference_rejected`: Citing unretrieved files rejected with `FILE_NOT_IN_CONTEXT`.
     5. `test_file_hash_mismatch_rejected`: Tampered or mismatched hashes rejected with `FILE_HASH_MISMATCH`.
     6. `test_wrong_repository_or_base_commit_sha_rejected`: Foreign commits/repos rejected.
     7. `test_incorrect_supporting_excerpt_rejected`: Fabricated excerpts rejected with `EXCERPT_MISMATCH`.
     8. `test_evidence_from_truncated_content_warns`: Citations from truncated content record warnings.
     9. `test_unverified_target_files_rejected`: Ungrounded target files rejected with `UNGROUNDED_TARGET_FILE`.
     10. `test_missing_evidence_and_uncertainty_handling`: Context requests and uncertainties captured.
     11. `test_context_changes_invalidate_plan`: Rebased context or modified content invalidates verified plan.
     12. `test_prompt_injection_defense_in_untrusted_repo_content`: Injection attempts isolated and blocked.
     13. `test_planner_node_and_coder_node_evidence_guards`: LangGraph nodes halt fail-closed on ungrounded plans.
     14. `test_plan_and_evidence_checkpoint_serialization_roundtrip`: LangGraph serialization survival.

### Sub-Milestone 4: End-to-End Issue Dispatcher & Frontend Integration
1. **Live Remote GitHub Issues & Repository Sync Endpoints (`backend/app/api/routes/repositories.py`)**:
   - `GET /api/v1/repositories/{repository_id}/github-issues`: Lists remote GitHub issues dynamically using authenticated `GitHubService`, handling missing credentials (503), rate limits (429), and authorization (401/403).
   - `GET /api/v1/repositories/{repository_id}/github-issues/{issue_number}`: Inspects individual remote issue details with default branch and latest base commit SHA preview.
   - `POST /api/v1/repositories/{repository_id}/sync-issue/{issue_number}`: Synchronizes/ingests remote issue into local SQLite database, preventing duplicate issue entities and preparing for immediate dispatch.
2. **Background Execution & Enriched Workflow State Endpoints (`backend/app/api/routes/runs.py`)**:
   - `POST /api/v1/runs/{run_id}/start?background=true`: Launches asynchronous workflow execution via `asyncio.create_task` returning immediate `PLANNING` status, preserving synchronous execution for tests.
   - `GET /api/v1/runs/{run_id}/state`: Enriched workflow state response delivering grounded plan details, line-span citations (`evidence_citations`), repository context provenance (`commit_sha`, truncation flags), test results (duration, commands, logs), reviewer findings with severity ratings, and failed patch anti-repetition registry.
   - `GET /api/v1/runs/{run_id}/stream`: Real-time Server-Sent Events (SSE) stream delivering `agent_event`, `status_update`, and `done` payloads with automatic keepalive and clean disconnect handling.
3. **Hardened Multi-Check Human Approval Gate (`backend/app/api/routes/runs.py`, `backend/app/schemas/approval.py`)**:
   - `ApprovalRequest`: Extended with optional `base_commit_sha: Optional[str]` field.
   - Reviewer Blocking Gate: Rejects approval with HTTP 409 Conflict if reviewer recommendation is `reject` or any findings have `CRITICAL` or `BLOCKING` severity.
   - Base Commit SHA Invariant: Cryptographically verifies `base_commit_sha` matches active run context.
   - Explicit Maintainer Rejection: Maintains fail-closed security by permitting explicit maintainer rejection (`decision == "rejected"`) regardless of test failure, logging full audit records in `ApprovalRecord`.
4. **Interactive Issue Dispatcher UI (`frontend/components/runs/IssueDispatcherModal.tsx`)**:
   - Select authorized repositories, toggle between ingested issues and remote GitHub issues, or enter an arbitrary issue number.
   - Live preview of issue title, description, target branch, and latest base commit SHA before dispatching.
   - Validates inputs, handles backend ingestion sync, creates authenticated run, starts execution in background, and navigates immediately to the live run detail view.
5. **Telemetry, Grounded Evidence & Hardened Reviewer Cards (`frontend/components/runs/`, `frontend/components/patches/`)**:
   - `GroundedPlanCard.tsx`: Renders structured plans, verified line-span citations (`EvidenceReference`) with code excerpts, target files, and regression test strategy with backend `is_verified` integrity badge.
   - `RepositoryContextCard.tsx`: Displays repository revision commit SHA, token budget, file count, truncation warning banner, and collapsible ranked file tree with content hash previews.
   - `TestResultCard.tsx`: Visualizes execution environment (Docker Sandbox vs AST Fallback), execution duration, pass/fail counts, executed commands, and collapsible terminal logs (stdout/stderr).
   - `ReviewerCard.tsx`: Highlights reviewer recommendation, acceptance criteria status, findings categorized by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`), and unresolved risks.
   - `ApprovalModal.tsx`: Hardened approval modal displaying patch SHA-256, target commit SHA, warning on blocking reviewer findings, and dedicated explicit rejection action with feedback.
   - Live SSE Integration (`frontend/app/runs/[id]/page.tsx`, `frontend/lib/api/client.ts`): Real-time event streaming with event deduplication, reconnect support, and fallback polling.
6. **Strict Read-Only GitHub Boundary**:
   - Strictly enforced throughout backend and frontend: no branch creation, git push, pull request creation, or repository modification endpoints are called or triggered.
7. **Verification Suites**:
   - `backend/tests/integration/test_issue_dispatcher_and_telemetry.py`: 7 tests verifying authorized/unauthorized GitHub issues, 503 missing credentials, sync & background dispatch, enriched state endpoint, reviewer blocking gate, commit SHA verification, and maintainer rejection audit trail.
   - `frontend/tests/frontend.test.mjs`: 13 tests covering UI validation, plan verification flag integrity, reviewer blocking gate, SSE deduplication, and read-only boundary.
   - Production Build: Next.js clean production compilation (11/11 pages).

### Sub-Milestone 5: Production Reliability, Recovery & End-to-End Acceptance
1. **Durable Background Worker & GC Protection (`backend/app/api/routes/runs.py`)**:
   - Fixed background task garbage collection vulnerability by maintaining a strong reference set `_background_tasks: set[asyncio.Task] = set()` with automatic `task.add_done_callback(_background_tasks.discard)`.
   - Fail-closed background worker exception handling: unhandled worker exceptions immediately transition run status to `FAILED`, record `error_summary`, and write an auditable `workflow_failed` event into `AgentLog`, completely eliminating zombie `PLANNING` or `RUNNING` runs.
2. **Server Restart & Crash Recovery (`backend/app/orchestration/service.py`, `backend/app/api/routes/runs.py`)**:
   - `DevSquadOrchestrator.reconcile_orphaned_runs(db)`: Detects in-flight runs in non-terminal active states whose worker tasks no longer exist (e.g. after container restart or process crash) and transitions them cleanly to `FAILED` with explicit error summary and finished timestamps.
   - `POST /api/v1/runs/reconcile-orphaned`: Authenticated endpoint to trigger orphan run reconciliation.
3. **Atomic Concurrency & TOCTOU Race Prevention (`backend/app/orchestration/service.py`)**:
   - Unified active task check and registration inside a single `_registry_lock` block in both `start_run` and `resume_run`, eliminating the race window where concurrent requests could launch duplicate workflow executions on the same run.
4. **Resumption Integrity Revalidation (`backend/app/orchestration/service.py`)**:
   - Hardened `resume_run`: before invoking graph execution, revalidates cryptographic integrity of stored `RepositoryContext` via `verify_integrity()` and verifies patch SHA-256 hash consistency against stored diff content, rejecting tampered or stale checkpoints with `RunNotResumableError`.
5. **Reliable SSE Telemetry & Browser Authentication (`backend/app/api/routes/runs.py`, `backend/app/api/dependencies.py`, `frontend/lib/api/client.ts`)**:
   - Browser EventSource authentication: updated `get_current_user` to accept `token: Optional[str] = Query(default=None)` when Bearer headers are unsupported by browser `EventSource`.
   - Stable reconnection without duplicate replay: `stream_run_events` supports `last_event_id` via header and query parameter, identifying its exact index in ordered logs and marking all prior events as delivered.
   - Status update deduplication: eliminates 1-second redundant status update spam by only emitting `status_update` frames when status or current node actually changes, supplemented with periodic `: keepalive\n\n` comments on idle intervals.
   - Frontend client reconnection support: `subscribeToRunStream` appends `token` and `last_event_id` to query string, and `RunDetailPage` tracks `lastEventIdRef` for seamless reconnects.
6. **Hardened Approval Under Concurrency & Explicit Rejection (`backend/app/api/routes/runs.py`)**:
   - Added DB refresh before approval status check; returns HTTP 409 Conflict if the run was already approved or rejected.
   - Verified fail-closed gates: blocks on blocking reviewer findings (`CRITICAL`/`BLOCKING`/`reject`), blocks on mismatched `base_commit_sha`, and allows explicit maintainer rejection with feedback recorded in `ApprovalRecord`.
7. **Comprehensive Reliability & Acceptance Verification Suites**:
   - `backend/tests/integration/test_runs_reliability_and_recovery.py`: 10 comprehensive tests validating background exception fail-closed transitions, orphan reconciliation, atomic concurrency protection, resumption integrity revalidation, SSE query token auth, `last_event_id` duplicate prevention, and approval gating under stress (10/10 passing).
   - `backend/tests/integration/test_acceptance_demonstration.py`: End-to-end controlled acceptance testing with deterministic bug repository fixture (`inventory.py`), real pytest subprocess execution, correct vs flawed patch execution, and security primitives (3/3 passing).
   - `frontend/tests/frontend.test.mjs`: 15 unit tests including EventSource URL query parameter construction and terminal stream closure (15/15 passing).

### Sub-Milestone 6: Deployment Readiness, Security Hardening & Real-Environment Validation
1. **Single-Purpose Stream Ticket Security Hardening (`backend/app/core/security.py`, `backend/app/api/routes/runs.py`, `backend/app/api/dependencies.py`)**:
   - Replaced risky long-lived Bearer tokens in URL query strings with short-lived (60s), single-purpose signed tickets (`create_stream_ticket` & `verify_stream_ticket`).
   - Each ticket is cryptographically signed via HMAC-SHA256, strictly bound to `user_id` and `run_id`, carries purpose `run_stream`, and includes a unique nonce (`jti`).
   - Integrated replay protection: consumed ticket JTIs are tracked and verified against replay attacks (`ValueError: Stream ticket has already been used (replay detected)`).
   - Removed query parameter token acceptance from `get_current_user` to eliminate credential leakage in browser history, proxy access logs, and referrer headers.
   - Endpoint `POST /api/v1/runs/{run_id}/stream-ticket`: Generates tickets only for authenticated users authorized on the repository.
   - Endpoint `GET /api/v1/runs/{run_id}/stream`: Exclusively accepts either signed `ticket` parameter or standard `Authorization: Bearer` header; explicitly rejects raw master tokens passed in `?token=...` with HTTP 401.
2. **Frontend Secure Stream Integration (`frontend/lib/api/client.ts`, `frontend/tests/frontend.test.mjs`)**:
   - Added `createStreamTicket(runId)` API method.
   - Updated `subscribeToRunStream`: Asynchronously acquires a short-lived stream ticket before establishing the `EventSource` connection, maintaining zero token leakage in URLs.
   - Updated frontend unit tests to verify ticket and `last_event_id` URL composition.
3. **Automatic Startup Orphan Reconciliation (`backend/app/main.py`)**:
   - Wired `orchestrator.reconcile_orphaned_runs(session)` into the FastAPI application `lifespan` startup hook.
   - In-flight runs left in active states (`INGESTING`, `PLANNING`, `CODING`, `TESTING`, `REVIEWING`) after abrupt system shutdown or process restart are automatically reconciled to `FAILED` immediately upon server boot before handling new traffic.
4. **Environment Audit & Real Boundary Verification**:
   - Docker Sandbox: Container isolation policies verified (`user="1000:1000"`, `network_mode="none"`, `mem_limit="1g"`, `nano_cpus`, no host mounts). Verified safe static AST fallback mode when Docker Desktop is offline.
   - Git CLI: Determined Git CLI is non-essential for backend runtime (pure Python `diff_utils.py` and GitHub API trees are used).
   - Real Provider Boundary: Confirmed strict read-only boundary for GitHub API and verified LLM provider abstractions.
5. **Comprehensive Verification Suites**:
   - `backend/tests/unit/test_security_stream_ticket.py`: 8 comprehensive tests verifying ticket generation, run mismatch rejection, tampering rejection, expiration rejection, replay protection, auth requirements, owner authorization, and startup orphan reconciliation (8/8 passing).
   - Full Backend Test Suite: 179 passed, 3 skipped (live creds), 0 failed in 53.84s.
   - Frontend Test Suite: 15 passed, 0 failed in 39.5ms.
   - Next.js Production Build: 11/11 routes successfully compiled with 0 TypeScript/ESLint errors.

---

## Verification Evidence

- **Pytest Suite Run (100 passed, 3 skipped, 0 failures)**:
  ```text
  tests/integration/test_crud_api.py::test_repository_crud_and_conflict PASSED
  tests/integration/test_crud_api.py::test_issue_crud_and_validation PASSED
  tests/integration/test_run_crud_lifecycle PASSED
  tests/integration/test_health_api.py::test_root_endpoint PASSED
  tests/integration/test_composite_health_endpoint PASSED
  tests/integration/test_database_health_endpoint PASSED
  tests/integration/test_llm_health_endpoint PASSED
  tests/integration/test_docker_health_endpoint PASSED
  tests/integration/test_live_integrations.py::TestLiveIntegrations::test_live_github_public_repo SKIPPED
  tests/integration/test_live_integrations.py::TestLiveIntegrations::test_live_gemini_provider SKIPPED
  tests/integration/test_live_integrations.py::TestLiveIntegrations::test_live_openai_provider SKIPPED
  tests/integration/test_migrations.py::test_migration_upgrade_from_empty_database PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_full_workflow_to_waiting_for_approval PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_repair_cycle_and_eventual_success PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_max_repairs_exhausted_fails PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_cancel_run PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_resume_terminal_run_raises PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_start_run_errors PASSED
  tests/integration/test_orchestrator_service.py::test_orchestrator_cancel_and_resume_not_found PASSED
  tests/integration/test_runs_orchestration_api.py::test_runs_orchestration_api_endpoints PASSED
  tests/integration/test_transaction_rollback.py::test_transaction_rollback_on_error PASSED
  tests/security/test_secret_redaction.py::test_logging_filter_redacts_tokens PASSED
  tests/security/test_secret_redaction.py::test_exception_handler_redacts_secrets_in_responses PASSED
  tests/unit/test_checkpointer.py::test_get_async_checkpointer_memory PASSED
  tests/unit/test_checkpointer.py::test_get_async_checkpointer_sqlite_persistence PASSED
  tests/unit/test_coder_agent.py::test_coder_agent_generates_valid_patch PASSED
  tests/unit/test_coder_agent.py::test_coder_agent_rejects_path_traversal PASSED
  tests/unit/test_coder_agent.py::test_coder_agent_rejects_hunk_mismatch PASSED
  tests/unit/test_coder_agent.py::test_coder_agent_includes_repair_feedback PASSED
  tests/unit/test_config.py::test_default_settings PASSED
  tests/unit/test_config.py::test_cors_origins_parsing PASSED
  tests/unit/test_config.py::test_settings_safe_dict_masks_secrets PASSED
  tests/unit/test_config.py::test_settings_validation_limits PASSED
  tests/unit/test_context_ranker.py::test_mentioned_paths_and_symbols_extraction PASSED
  tests/unit/test_context_ranker.py::test_calculate_file_score_priorities PASSED
  tests/unit/test_context_ranker.py::test_filter_tree_excludes_secrets_binaries_vendored PASSED
  tests/unit/test_context_ranker.py::test_rank_and_package_enforces_budget_and_truncates PASSED
  tests/unit/test_context_ranker.py::test_deterministic_ranking_order PASSED
  tests/unit/test_context_ranker.py::test_config_file_scoring PASSED
  tests/unit/test_context_ranker.py::test_import_dependency_scoring PASSED
  tests/unit/test_diff_utils.py::test_parse_unified_diff_files PASSED
  tests/unit/test_diff_utils.py::test_validate_unified_diff_safety_rejects_traversal PASSED
  tests/unit/test_diff_utils.py::test_validate_unified_diff_safety_rejects_absolute_path PASSED
  tests/unit/test_diff_utils.py::test_apply_unified_diff_success PASSED
  tests/unit/test_diff_utils.py::test_apply_unified_diff_hunk_mismatch PASSED
  tests/unit/test_diff_utils.py::test_split_multi_file_unified_diff PASSED
  tests/unit/test_github_service.py::test_get_repository_success PASSED
  tests/unit/test_github_service.py::test_github_auth_error_handling PASSED
  tests/unit/test_github_service.py::test_github_rate_limit_error_handling PASSED
  tests/unit/test_github_service.py::test_github_resource_not_found PASSED
  tests/unit/test_github_service.py::test_get_issue_and_comments PASSED
  tests/unit/test_list_issues_filters_pull_requests PASSED
  tests/unit/test_github_service.py::test_get_file_content_decodes_base64 PASSED
  tests/unit/test_github_service.py::test_get_file_content_rejects_binary_and_oversized PASSED
  tests/unit/test_github_service.py::test_get_branch_success PASSED
  tests/unit/test_github_service.py::test_get_commit_success PASSED
  tests/unit/test_llm_providers.py::test_gemini_provider_generate_structured_success PASSED
  tests/unit/test_llm_providers.py::test_gemini_provider_schema_validation_failure PASSED
  tests/unit/test_llm_providers.py::test_gemini_provider_rate_limit_and_timeout PASSED
  tests/unit/test_llm_providers.py::test_gemini_provider_retry_success PASSED
  tests/unit/test_llm_providers.py::test_gemini_provider_requires_api_key PASSED
  tests/unit/test_openai_provider_generate_structured_success PASSED
  tests/unit/test_openai_provider_auth_and_rate_limit_errors PASSED
  tests/unit/test_openai_provider_retry_success PASSED
  tests/unit/test_llm_providers.py::test_get_llm_provider_selection_and_errors PASSED
  tests/unit/test_models.py::test_user_creation_and_uniqueness PASSED
  tests/unit/test_models.py::test_repository_and_issue_relationship_and_uniqueness PASSED
  tests/unit/test_models.py::test_run_patch_approval_audit_trail PASSED
  tests/unit/test_orchestration_state.py::test_create_initial_state_defaults PASSED
  tests/unit/test_orchestration_state.py::test_workflow_enums PASSED
  tests/unit/test_planner_agent.py::test_planner_agent_generates_valid_plan PASSED
  tests/unit/test_planner_agent.py::test_planner_agent_rejects_unsafe_target_path PASSED
  tests/unit/test_planner_agent.py::test_planner_flags_unranked_target_file_in_uncertainties PASSED
  tests/unit/test_prompt_safety.py::test_build_safe_context_prompt_boundaries PASSED
  tests/unit/test_prompt_safety.py::test_system_security_policy_content PASSED
  tests/unit/test_repair_cycle.py::test_repair_cycle_state_transitions PASSED
  tests/unit/test_repair_cycle.py::test_repair_cycle_get_latest_feedback PASSED
  tests/unit/test_repair_cycle.py::test_record_patch_revision_and_log_agent_event_persistence PASSED
  tests/unit/test_reviewer_agent.py::test_reviewer_agent_approves_clean_patch PASSED
  tests/unit/test_reviewer_agent.py::test_reviewer_agent_overrides_approve_on_critical_finding PASSED
  tests/unit/test_routing.py::test_route_after_validation PASSED
  tests/unit/test_routing.py::test_route_after_planner PASSED
  tests/unit/test_routing.py::test_route_after_coder PASSED
  tests/unit/test_routing.py::test_route_after_tester PASSED
  tests/unit/test_routing.py::test_route_after_reviewer_approve PASSED
  tests/unit/test_routing.py::test_route_after_reviewer_triggers_bounded_repair PASSED
  tests/unit/test_routing.py::test_route_after_reviewer_critical_finding_prevents_direct_approval PASSED
  tests/unit/test_schemas.py::test_structured_plan_valid PASSED
  tests/unit/test_schemas.py::test_structured_plan_rejects_empty_steps_or_criteria PASSED
  tests/unit/test_plan_step_forbids_extra_fields PASSED
  tests/unit/test_schemas.py::test_patch_item_valid PASSED
  tests/unit/test_schemas.py::test_review_finding_severity_validation PASSED
  tests/unit/test_schemas.py::test_approval_request_validation PASSED
  tests/unit/test_schemas.py::test_repository_create_name_validation PASSED
  tests/unit/test_security.py::test_redact_github_tokens PASSED
  tests/unit/test_security.py::test_redact_openai_and_gemini_keys PASSED
  tests/unit/test_security.py::test_redact_bearer_tokens_and_passwords PASSED
  tests/unit/test_compute_sha256_canonical PASSED
  tests/unit/test_is_safe_relative_path PASSED
  tests/unit/test_sanitize_dict_for_logging PASSED
  tests/unit/test_tester_agent.py::test_tester_agent_ast_fallback_valid_syntax PASSED
  tests/unit/test_tester_agent.py::test_tester_agent_ast_fallback_syntax_error PASSED
  tests/unit/test_tester_agent.py::test_tester_agent_docker_mode_success PASSED
  tests/unit/test_tester_agent.py::test_tester_agent_docker_mode_rejects_unpermitted_command PASSED
  tests/unit/test_tester_agent.py::test_tester_agent_docker_mode_timeout_and_cleanup PASSED

### Phase 4.5: Critical Bug Fixes, Security Hardening, and End-to-End Verification — COMPLETE

1. **Issue A: Real Repository Context Retrieval & Grounding**:
   - Live GitHub retrieval in `context_preparation_node` uses recursive git tree indexing, base-revision commit SHA extraction, and `ContextRanker` filtering.
   - Enforces strict file-size limits (`settings.max_file_size_bytes`) and binary file exclusion.
   - Unambiguously isolates test fixtures (`metadata["is_test_fixture"] = True`) from production GitHub API paths.
   - Grounding validation: CoderAgent verifies target files exist in context before generating modifications.

2. **Issue B: Docker Sandbox Workspace Construction & Safe Test Execution**:
   - Hardened `SandboxTesterAgent`: copies patched repository files into disposable container via in-memory tar archive (`put_archive`), eliminating invalid host path bind-mounts.
   - Enforces non-root container permissions (`1000:1000`) and network isolation (`network_mode="none"`).
   - Strict command allowlist: only approved test runners (`pytest`, `python -m unittest`, `npm test`, `go test`, `cargo test`) are executed; arbitrary commands are rejected.
   - Container cleanup guaranteed via `finally` block.
   - Honest test semantics: dynamic execution pass is required for `TESTS_PASSED`. AST syntax validation is explicitly reported as `PARTIAL_VALIDATION` or `SANDBOX_UNAVAILABLE`.
   - Records cryptographic provenance: `patch_hash`, `patch_revision`, and `base_commit_sha` recorded in `TestResult`.

3. **Issue C: Centralized Fail-Closed Routing Gates**:
   - `route_after_reviewer` requires both reviewer approval AND test pass (`TESTS_PASSED` or allowed fallback policy `allow_manual_approval_without_sandbox`).
   - If tests fail, workflow routes to bounded repair; if repair attempts are exhausted, transitions to `FAILED` and **never** presents the patch as verified.
   - Reviewer approval with unresolved CRITICAL or HIGH findings cannot transition to `WAITING_FOR_APPROVAL`.
   - `finalization_node` double-checks all safety gates fail-closed.

4. **Issue D: Real Cancellation & Concurrency-Safe Execution**:
   - Orchestrator registry tracks active tasks (`_active_tasks`), cancellation events (`_cancel_events`), and concurrency locks (`_registry_lock`).
   - Starting or resuming an already active run is strictly rejected (`OrchestrationError: ... already actively executing`).
   - Cooperative cancellation: nodes inspect `WorkflowStatus.CANCELLED` at entrance and gracefully finalize.
   - In-flight asyncio tasks receive `task.cancel()` with safe database status updates.
   - Idempotent `cancel_run`: repeated cancellation calls safely return without error.

5. **Issue E: Authentication & Authorization for Runs API**:
   - Added zero-dependency RFC-compatible HMAC-SHA256 bearer token security in `app/core/security.py` (`create_access_token`, `verify_access_token`).
   - Secured `/api/v1/runs` routes with `get_current_user`, `get_authorized_repository`, and `get_authorized_run` dependencies.
   - Unauthenticated requests rejected with HTTP 401.
   - Cross-user repository and run access rejected with HTTP 403 Forbidden.
   - Added anti-tamper approval endpoint: `POST /api/v1/runs/{run_id}/approve`:
     - Verifies submitted `patch_hash` strictly matches stored patch content SHA-256 (rejects forged/tampered hashes with HTTP 409 Conflict).
     - Persists immutable `ApprovalRecord` audit trail with reviewer ID, decision, patch hash, and feedback.
     - Transitions run lifecycle status to `APPROVED` or `REJECTED`.

6. **Dedicated Integration & End-to-End Test Suites**:
   - `tests/integration/test_runs_auth_and_gates.py`: 4 tests verifying 401 unauthenticated, 403 cross-user access, anti-tamper patch hash verification, and run status validation.
   - `tests/integration/test_orchestration_cancellation.py`: 3 tests verifying concurrent start prevention, idempotent cancel, and in-flight cooperative cancellation.
   - `tests/integration/test_end_to_end_workflow.py`: 2 tests verifying realistic math library bug repair to human approval and fail-closed test failure gates.

---

## Test Execution Results (Full Suite)

```text
======================= 171 passed, 3 skipped in 44.65s =======================

Frontend Test Suite:
15 passed, 0 failed in 48.66ms (Node.js test runner)

Next.js Production Build:
11/11 pages statically/dynamically generated cleanly (0 errors, 0 warnings)
```

---

## Security Safeguards

- **Prompt Injection Defense**: Untrusted issue descriptions, repository code, and commit messages are strictly treated as data encapsulated in XML boundary tags (`<UNTRUSTED_ISSUE>`, `<UNTRUSTED_REPOSITORY_FILE>`).
- **Application-Side Patch Hashing**: The CoderAgent computes `compute_sha256(unified_diff.strip())` natively on the host; model-supplied hashes are never trusted or accepted.
- **Cryptographic Anti-Tamper Approval**: Maintainer approval cryptographically verifies the submitted `patch_hash` and `base_commit_sha` against the stored run provenance before creating an immutable `ApprovalRecord`.
- **Reviewer Blocking Finding Gate**: Approval is strictly blocked if any findings have `CRITICAL` or `BLOCKING` severity or if reviewer recommendation is `reject`.
- **Atomic Concurrency Protection**: Start and resume task registrations are held under a single `_registry_lock`, preventing race conditions and duplicate concurrent runs on the same state thread.
- **Crash Recovery & Orphan Reconciler**: Background runs terminate cleanly fail-closed on unhandled exceptions; orphaned runs from process crashes or restarts are reconciled to `FAILED`.
- **Checkpoint Resumption Invariants**: Resuming checkpoints revalidates cryptographic integrity of repository context files and patch hashes before re-entering graph execution.
- **Strict Read-Only GitHub Boundary**: Automated workflows never publish branches, push commits, create pull requests, or mutate remote repositories.
- **Path Traversal Protection**: Both PlannerAgent and CoderAgent validate all paths against `is_safe_relative_path` and reject relative traversal (`..`) or absolute paths (`/etc/...`, `C:\...`).
- **Sandbox Security Policy**: Docker mode enforces in-memory tarball injection (`put_archive`), non-root execution (`1000:1000`), network disabled (`network_mode="none"`), resource limits, read-only root filesystems, no host socket mounts, and command allowlists.
- **Honest Test Execution**: When Docker is unavailable, static AST validation is explicitly reported as `PARTIAL_VALIDATION` or `SANDBOX_UNAVAILABLE`; it is never reported as passing test suites.
- **Reviewer Advisory Constraint**: Independent review recommendations are advisory for human review; human approval is mandatory before any downstream action.
- **Bounded Repair Loop Enforcement**: Orchestrator routing enforces a hard upper bound on repair cycles (`settings.max_agent_retries`), preventing infinite execution loops, runaway API token consumption, or silent degradation.
- **Authentication & RBAC**: Every execution run and repository access is authenticated via HMAC-SHA256 bearer tokens and verified for ownership.

---

## Remaining Environmental Observations & Fallbacks

1. **Git CLI**: `git.exe` is not currently in the Windows system PATH. Standard instructions are documented in setup guides (`winget install --id Git.Git -e --source winget`).
2. **Docker Daemon**: Docker Desktop daemon is currently stopped. `GET /api/v1/health` honestly reports status `degraded` with `docker: "unavailable"`. DevSquad accurately falls back to safe AST static syntax validation without faking container execution.
3. **Live Remote GitHub**: Repository and issue sync can operate on local database fixtures (`LOCAL DATABASE`) or connect to live GitHub repositories via `DEVSQUAD_GITHUB_TOKEN`.
4. **LLM Provider**: Configured with Groq API key (`openai/gpt-oss-120b`), active and responsive for structured plan and diff synthesis.

---

## Outstanding Tasks

- None. All sub-milestones, core platform routes, multi-agent workflows, diagnostics, provenance badges, and approval safeguards are fully implemented, verified, and demonstration-ready.

---

## Demonstration Status

- **System Status**: Ready for teacher demonstration.
- **Backend**: Port 8000 (FastAPI ASGI with SQLite WAL persistence).
- **Frontend**: Port 3000 (Next.js 14 App Router with Obsidian & Forge Lime theme).
- **Verification Evidence**: 179 backend pytest passed (0 failed), 17 frontend tests passed (0 failed), 0 TypeScript compilation errors.
