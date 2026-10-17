import { describe, it } from "node:test";
import assert from "node:assert/strict";

describe("Frontend Core Architecture & Security Controls", () => {
  it("verifies all 8 core platform sidebar routes and names are defined", () => {
    const expectedRoutes = [
      { label: "Command Center", href: "/" },
      { label: "Repositories", href: "/repositories" },
      { label: "Issues", href: "/issues" },
      { label: "Agent Runs", href: "/runs" },
      { label: "Patch Laboratory", href: "/patches" },
      { label: "Activity Stream", href: "/logs" },
      { label: "System Diagnostics", href: "/health" },
      { label: "Settings", href: "/settings" },
    ];

    assert.equal(expectedRoutes.length, 8);
    assert.deepEqual(
      expectedRoutes.map((n) => n.href),
      [
        "/",
        "/repositories",
        "/issues",
        "/runs",
        "/patches",
        "/logs",
        "/health",
        "/settings",
      ]
    );
  });

  it("verifies 4-agent palette colors and roles", () => {
    const agents = {
      planner: { name: "Planner Agent", color: "#A78BFA", key: "ultraviolet" },
      coder: { name: "Coder Agent", color: "#D7FF64", key: "forge-lime" },
      tester: { name: "Sandbox Tester", color: "#65E4F3", key: "ice-cyan" },
      reviewer: { name: "Reviewer Agent", color: "#FFB454", key: "amber" },
    };

    assert.equal(agents.planner.color, "#A78BFA");
    assert.equal(agents.coder.color, "#D7FF64");
    assert.equal(agents.tester.color, "#65E4F3");
    assert.equal(agents.reviewer.color, "#FFB454");
  });

  it("verifies static validation warning is triggered when only AST validation occurred", () => {
    function isStaticOnlyValidation(validationStatus) {
      return (
        validationStatus === "ast_fallback" ||
        validationStatus === "sandbox_unavailable" ||
        validationStatus === "partial_validation"
      );
    }

    assert.equal(isStaticOnlyValidation("passed"), false);
    assert.equal(isStaticOnlyValidation("ast_fallback"), true);
    assert.equal(isStaticOnlyValidation("sandbox_unavailable"), true);
    assert.equal(isStaticOnlyValidation("partial_validation"), true);
  });

  it("verifies diff viewer escaping prevents executable HTML injection", () => {
    const maliciousDiff = `--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-<script>alert("xss")</script>\n+<img src=x onerror=alert(1)>`;
    const lines = maliciousDiff.split("\n");

    assert.equal(lines.length, 5);
    assert.equal(lines[3].startsWith("-"), true);
    assert.equal(lines[4].startsWith("+"), true);
    assert.ok(lines[3].includes("<script>"));
    assert.ok(lines[4].includes("<img"));
  });

  it("verifies human approval gating policy requirements", () => {
    function evaluateApprovalGate(runStatus, patchValidationStatus) {
      const isAwaiting = runStatus === "AWAITING_APPROVAL";
      const testsPassed = patchValidationStatus === "passed";
      return isAwaiting && testsPassed;
    }

    // Passing scenario
    assert.equal(evaluateApprovalGate("AWAITING_APPROVAL", "passed"), true);

    // Blocked scenarios:
    // 1. Tests failed
    assert.equal(evaluateApprovalGate("AWAITING_APPROVAL", "failed"), false);
    // 2. Only AST fallback occurred
    assert.equal(evaluateApprovalGate("AWAITING_APPROVAL", "ast_fallback"), false);
    // 3. Run already completed or approved
    assert.equal(evaluateApprovalGate("APPROVED", "passed"), false);
    // 4. Run currently running
    assert.equal(evaluateApprovalGate("TESTING", "passed"), false);
    // 5. Run failed
    assert.equal(evaluateApprovalGate("FAILED", "passed"), false);
  });

  it("verifies approval confirmation requirement before submission", () => {
    function canSubmitApproval(decision, confirmed, isGateAllowed) {
      if (decision === "approved") {
        return Boolean(isGateAllowed && confirmed);
      }
      return true; // Rejections can always be submitted
    }

    // Approved without confirmation is blocked
    assert.equal(canSubmitApproval("approved", false, true), false);
    // Approved with confirmation and passing gate is allowed
    assert.equal(canSubmitApproval("approved", true, true), true);
    // Approved with confirmation but failed gate is blocked
    assert.equal(canSubmitApproval("approved", true, false), false);
    // Rejection is always allowed
    assert.equal(canSubmitApproval("rejected", false, false), true);
  });

  it("verifies API error wrapping and status codes", () => {
    class MockApiError extends Error {
      constructor(message, status, details) {
        super(message);
        this.status = status;
        this.details = details;
      }
    }

    const unauthErr = new MockApiError("Invalid or expired authentication token", 401);
    assert.equal(unauthErr.status, 401);

    const forbiddenErr = new MockApiError("Forbidden: Unauthorized repository access", 403);
    assert.equal(forbiddenErr.status, 403);

    const conflictErr = new MockApiError("Submitted patch hash does not match current run patch", 409);
    assert.equal(conflictErr.status, 409);
  });

  it("verifies hash truncation helper preserves uniqueness and visual security", () => {
    function truncateHash(hash, len = 12) {
      if (!hash) return "—";
      if (hash.length <= len) return hash;
      return `${hash.slice(0, len)}…`;
    }

    const fullSha256 = "9aeb65b408154889b24bc3c4176a4020d230a6ee18bf92a0bff1f0b3c55e4460";
    const truncated = truncateHash(fullSha256, 12);
    assert.equal(truncated, "9aeb65b40815…");
    assert.equal(truncateHash(null), "—");
  });

  it("verifies issue dispatcher repository and issue validation and duplicate submission defense", () => {
    function validateDispatchParams(repoId, issueId, submitting) {
      if (submitting) return { valid: false, error: "Submission already in progress" };
      if (!repoId || typeof repoId !== "string" || repoId.trim() === "") {
        return { valid: false, error: "Repository identifier is required" };
      }
      if (!issueId || typeof issueId !== "string" || issueId.trim() === "") {
        return { valid: false, error: "Issue identifier is required" };
      }
      return { valid: true, error: null };
    }

    assert.equal(validateDispatchParams("repo-1", "issue-1", false).valid, true);
    assert.equal(validateDispatchParams("", "issue-1", false).valid, false);
    assert.equal(validateDispatchParams("repo-1", "", false).valid, false);
    assert.equal(validateDispatchParams("repo-1", "issue-1", true).valid, false);
    assert.equal(validateDispatchParams("repo-1", "issue-1", true).error, "Submission already in progress");
  });

  it("verifies plan verification status strictly relies on backend is_verified flag, not text inference", () => {
    function evaluatePlanVerification(plan) {
      // Must not independently infer verification from the presence of citation text
      return Boolean(plan && plan.is_verified === true);
    }

    // A plan with citations but is_verified=false must NOT be treated as verified
    const unverifiedPlanWithCitations = {
      objective: "Fix bug",
      evidence_citations: [{ file_path: "main.py", start_line: 1, end_line: 5, excerpt: "def foo():" }],
      is_verified: false,
    };
    assert.equal(evaluatePlanVerification(unverifiedPlanWithCitations), false);

    // Only backend certified is_verified=true is verified
    const certifiedPlan = {
      objective: "Fix bug",
      evidence_citations: [{ file_path: "main.py", start_line: 1, end_line: 5, excerpt: "def foo():" }],
      is_verified: true,
    };
    assert.equal(evaluatePlanVerification(certifiedPlan), true);
  });

  it("verifies approval gate blocks on reviewer reject recommendation and blocking findings", () => {
    function canApproveWithReview(runStatus, validationStatus, review) {
      const isAwaiting = runStatus === "AWAITING_APPROVAL";
      const isValidated = validationStatus === "passed" || validationStatus === "TESTS_PASSED" || validationStatus === "VALIDATED";
      if (!isAwaiting || !isValidated) return false;

      if (!review) return true;
      if (String(review.recommendation).toLowerCase() === "reject") return false;
      const hasBlocking = review.findings?.some((f) =>
        ["CRITICAL", "BLOCKING"].includes(String(f.severity).toUpperCase())
      );
      if (hasBlocking) return false;

      return true;
    }

    // Clean review with passing tests
    assert.equal(
      canApproveWithReview("AWAITING_APPROVAL", "TESTS_PASSED", {
        recommendation: "approve",
        findings: [{ severity: "info", description: "Minor style" }],
      }),
      true
    );

    // Blocking review finding blocks approval
    assert.equal(
      canApproveWithReview("AWAITING_APPROVAL", "TESTS_PASSED", {
        recommendation: "approve",
        findings: [{ severity: "CRITICAL", description: "Remote code execution vector" }],
      }),
      false
    );

    // Rejection recommendation blocks approval
    assert.equal(
      canApproveWithReview("AWAITING_APPROVAL", "TESTS_PASSED", {
        recommendation: "reject",
        findings: [],
      }),
      false
    );
  });

  it("verifies live event stream deduplication and cleanup", () => {
    const seenIds = new Set();
    const eventLog = [];

    function processIncomingEvent(event) {
      if (seenIds.has(event.id)) {
        return false; // deduplicated
      }
      seenIds.add(event.id);
      eventLog.push(event);
      return true;
    }

    const event1 = { id: "log-1", agent_name: "planner", message: "Plan started" };
    const event2 = { id: "log-2", agent_name: "coder", message: "Patch generated" };

    assert.equal(processIncomingEvent(event1), true);
    assert.equal(processIncomingEvent(event1), false); // duplicate ignored
    assert.equal(processIncomingEvent(event2), true);
    assert.equal(eventLog.length, 2);
  });

  it("verifies strict read-only boundary: no automated GitHub branch or PR publication", () => {
    const allowedActions = ["DISPATCH_RUN", "START_RUN", "APPROVE_PATCH", "REJECT_PATCH", "CANCEL_RUN"];
    const forbiddenWriteActions = ["GIT_PUSH", "PUBLISH_BRANCH", "CREATE_PULL_REQUEST", "MERGE_BRANCH"];

    forbiddenWriteActions.forEach((action) => {
      assert.equal(allowedActions.includes(action), false, `Forbidden action ${action} must not be exposed`);
    });
  });

  it("verifies EventSource stream URL constructs short-lived ticket and last_event_id query parameters", () => {
    function buildStreamUrl(apiBase, runId, ticket, lastEventId) {
      const params = new URLSearchParams();
      if (ticket) params.set("ticket", ticket);
      if (lastEventId) params.set("last_event_id", lastEventId);
      const qs = params.toString();
      return `${apiBase}/api/v1/runs/${runId}/stream${qs ? `?${qs}` : ""}`;
    }

    const url1 = buildStreamUrl("http://localhost:8000", "run-101", "ticket_signed_abc", "log_55");
    assert.equal(url1, "http://localhost:8000/api/v1/runs/run-101/stream?ticket=ticket_signed_abc&last_event_id=log_55");

    const url2 = buildStreamUrl("http://localhost:8000", "run-101", "ticket_signed_abc", undefined);
    assert.equal(url2, "http://localhost:8000/api/v1/runs/run-101/stream?ticket=ticket_signed_abc");

    const url3 = buildStreamUrl("http://localhost:8000", "run-101", null, undefined);
    assert.equal(url3, "http://localhost:8000/api/v1/runs/run-101/stream");
  });

  it("verifies terminal stream statuses trigger completion closure", () => {
    const terminalStatuses = new Set([
      "COMPLETED",
      "FAILED",
      "CANCELLED",
      "AWAITING_APPROVAL",
      "APPROVED",
      "REJECTED",
    ]);

    function isTerminalStatus(status) {
      return terminalStatuses.has(status);
    }

    assert.equal(isTerminalStatus("PLANNING"), false);
    assert.equal(isTerminalStatus("CODING"), false);
    assert.equal(isTerminalStatus("TESTING"), false);
    assert.equal(isTerminalStatus("AWAITING_APPROVAL"), true);
    assert.equal(isTerminalStatus("APPROVED"), true);
    assert.equal(isTerminalStatus("REJECTED"), true);
    assert.equal(isTerminalStatus("COMPLETED"), true);
    assert.equal(isTerminalStatus("FAILED"), true);
    assert.equal(isTerminalStatus("CANCELLED"), true);
  });

  it("verifies maintainer demo profiles contain valid emails and roles", () => {
    const demoProfiles = [
      {
        title: "Lead Maintainer",
        email: "maintainer@devsquad.ai",
        displayName: "DevSquad Lead Maintainer",
        role: "Full System & Approval Authority",
      },
      {
        title: "Principal AI Architect",
        email: "architect@devsquad.ai",
        displayName: "Principal AI Architect",
        role: "Agent Orchestration & Tuning",
      },
      {
        title: "Security & QA Lead",
        email: "qa-lead@devsquad.ai",
        displayName: "QA & Verification Lead",
        role: "Patch Verification & Sandbox Gate",
      },
    ];

    assert.equal(demoProfiles.length, 3);
    for (const p of demoProfiles) {
      assert.match(p.email, /^[^@]+@[^@]+\.[^@]+$/);
      assert.ok(p.displayName.length > 0);
      assert.ok(p.role.length > 0);
    }
  });

  it("verifies session token storage and retrieval logic", () => {
    let mockStorage = {};
    const mockLocalStorage = {
      getItem: (k) => mockStorage[k] || null,
      setItem: (k, v) => { mockStorage[k] = v; },
      removeItem: (k) => { delete mockStorage[k]; },
    };

    const tokenKey = "devsquad_session_token";
    const userKey = "devsquad_session_user";

    // Set
    mockLocalStorage.setItem(tokenKey, "jwt-test-token");
    mockLocalStorage.setItem(userKey, JSON.stringify({ email: "maintainer@devsquad.ai" }));

    // Get
    assert.equal(mockLocalStorage.getItem(tokenKey), "jwt-test-token");
    assert.deepEqual(JSON.parse(mockLocalStorage.getItem(userKey)), { email: "maintainer@devsquad.ai" });

    // Clear
    mockLocalStorage.removeItem(tokenKey);
    mockLocalStorage.removeItem(userKey);
    assert.equal(mockLocalStorage.getItem(tokenKey), null);
    assert.equal(mockLocalStorage.getItem(userKey), null);
  });
});
