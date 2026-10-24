/**
 * Centralized DevSquad API client.
 * Connects directly to backend endpoints with typed responses and error handling.
 */

import {
  ApprovalRecord,
  AgentEvent,
  HealthResponse,
  Issue,
  OverviewStats,
  Patch,
  Repository,
  Run,
  RunStatus,
  SecurityScanResult,
  User,
  WorkflowStateSnapshot,
  GitHubUserProfile,
  GitHubAccountIssue,
  QuickSolverResult,
  GitHubInspectResult,
  GitHubTokenPermissions,
  PublishSolutionResult,
} from "@/types";
import { getSessionToken, setSession } from "../auth/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = 8000
): Promise<T> {
  const token = getSessionToken();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE}${endpoint}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorBody: any;
      try {
        errorBody = await res.json();
      } catch {
        errorBody = { message: res.statusText };
      }
      const message =
        errorBody?.detail || errorBody?.message || `Request failed with status ${res.status}`;
      throw new ApiError(message, res.status, errorBody);
    }

    if (res.status === 204 || res.headers.get("content-length") === "0") {
      return {} as T;
    }

    const text = await res.text();
    if (!text || text.trim() === "") {
      return {} as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch {
      return text as unknown as T;
    }
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new ApiError(`Request to ${endpoint} timed out after ${timeoutMs}ms`, 408);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(err?.message || "Network connection failure", 503);
  }
}

export const api = {
  // Session / Auth
  async createSession(
    email = "maintainer@devsquad.ai",
    displayName = "DevSquad Principal Maintainer"
  ): Promise<{ access_token: string; token_type: string; user: User }> {
    const data = await fetchWithAuth<{ access_token: string; token_type: string; user: User }>(
      "/api/v1/auth/session",
      {
        method: "POST",
        body: JSON.stringify({ email, display_name: displayName }),
      }
    );
    setSession(data.access_token, data.user);
    return data;
  },

  async getMe(): Promise<User> {
    return fetchWithAuth<User>("/api/v1/auth/me");
  },

  // Health
  async getHealth(): Promise<HealthResponse> {
    return fetchWithAuth<HealthResponse>("/api/v1/health");
  },

  // Overview
  async getOverviewStats(): Promise<OverviewStats> {
    return fetchWithAuth<OverviewStats>("/api/v1/overview/stats");
  },

  // Repositories
  async getRepositories(skip = 0, limit = 50): Promise<Repository[]> {
    return fetchWithAuth<Repository[]>(`/api/v1/repositories?skip=${skip}&limit=${limit}`);
  },

  async getRepository(id: string): Promise<Repository> {
    return fetchWithAuth<Repository>(`/api/v1/repositories/${id}`);
  },

  async deleteRepository(id: string): Promise<void> {
    await fetchWithAuth<void>(`/api/v1/repositories/${id}`, {
      method: "DELETE",
    });
  },

  async getRepositoryGitHubIssues(
    repositoryId: string,
    state = "open",
    page = 1,
    perPage = 30
  ): Promise<any[]> {
    const params = new URLSearchParams({
      state,
      page: String(page),
      per_page: String(perPage),
    });
    return fetchWithAuth<any[]>(`/api/v1/repositories/${repositoryId}/github-issues?${params.toString()}`);
  },

  async getRepositoryGitHubIssue(
    repositoryId: string,
    issueNumber: number
  ): Promise<{ issue: any; target_branch: string; base_commit_sha: string }> {
    return fetchWithAuth<{ issue: any; target_branch: string; base_commit_sha: string }>(
      `/api/v1/repositories/${repositoryId}/github-issues/${issueNumber}`
    );
  },

  async syncRepositoryGitHubIssue(
    repositoryId: string,
    issueNumber: number
  ): Promise<Issue> {
    return fetchWithAuth<Issue>(
      `/api/v1/repositories/${repositoryId}/sync-issue/${issueNumber}`,
      { method: "POST" }
    );
  },

  // Issues
  async getIssues(repositoryId?: string, state?: string, skip = 0, limit = 50): Promise<Issue[]> {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (repositoryId) params.set("repository_id", repositoryId);
    if (state) params.set("state", state);
    return fetchWithAuth<Issue[]>(`/api/v1/issues?${params.toString()}`);
  },

  async getIssue(id: string): Promise<Issue> {
    return fetchWithAuth<Issue>(`/api/v1/issues/${id}`);
  },

  async createIssue(payload: {
    repository_id: string;
    github_issue_number?: number;
    title: string;
    body?: string;
    state?: string;
    labels?: string[];
    html_url?: string;
  }): Promise<Issue> {
    return fetchWithAuth<Issue>("/api/v1/issues", {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        github_issue_number: payload.github_issue_number || Math.floor(Math.random() * 9000) + 100,
        state: payload.state || "open",
        labels: payload.labels || ["defect", "user-reported"],
      }),
    });
  },

  // Runs
  async createRun(repositoryId: string, issueId: string): Promise<Run> {
    return fetchWithAuth<Run>("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({
        repository_id: repositoryId,
        issue_id: issueId,
      }),
    });
  },

  async getRuns(repositoryId?: string, status?: RunStatus, skip = 0, limit = 50): Promise<Run[]> {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (repositoryId) params.set("repository_id", repositoryId);
    if (status) params.set("status", status);
    return fetchWithAuth<Run[]>(`/api/v1/runs?${params.toString()}`);
  },

  async getRun(id: string): Promise<Run> {
    return fetchWithAuth<Run>(`/api/v1/runs/${id}`);
  },

  async getRunState(id: string): Promise<WorkflowStateSnapshot> {
    return fetchWithAuth<WorkflowStateSnapshot>(`/api/v1/runs/${id}/state`);
  },

  async getRunEvents(id: string): Promise<AgentEvent[]> {
    return fetchWithAuth<AgentEvent[]>(`/api/v1/runs/${id}/events`);
  },

  async getRunPatches(id: string): Promise<Patch[]> {
    return fetchWithAuth<Patch[]>(`/api/v1/runs/${id}/patches`);
  },

  async getRunApprovals(id: string): Promise<ApprovalRecord[]> {
    return fetchWithAuth<ApprovalRecord[]>(`/api/v1/runs/${id}/approvals`);
  },

  async getRunSecurity(id: string): Promise<SecurityScanResult> {
    return fetchWithAuth<SecurityScanResult>(`/api/v1/runs/${id}/security`);
  },

  async startRun(
    id: string,
    options?: { background?: boolean; metadata?: Record<string, unknown> }
  ): Promise<any> {
    const isBg = options?.background ?? true;
    const body: Record<string, unknown> = {
      background: isBg,
      metadata: options?.metadata || {},
    };
    return fetchWithAuth(`/api/v1/runs/${id}/start?background=${isBg}`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async cancelRun(id: string, reason = "Cancelled by user request."): Promise<any> {
    return fetchWithAuth(`/api/v1/runs/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async approveRun(
    id: string,
    payload: {
      patch_id: string;
      decision: "approved" | "rejected";
      patch_hash: string;
      base_commit_sha?: string;
      feedback?: string;
    }
  ): Promise<ApprovalRecord> {
    return fetchWithAuth<ApprovalRecord>(`/api/v1/runs/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async createStreamTicket(
    runId: string
  ): Promise<{ ticket: string; expires_in: number; run_id: string }> {
    return fetchWithAuth<{ ticket: string; expires_in: number; run_id: string }>(
      `/api/v1/runs/${runId}/stream-ticket`,
      { method: "POST" }
    );
  },

  subscribeToRunStream(
    runId: string,
    onEvent: (event: AgentEvent) => void,
    onStatusUpdate?: (statusData: { status: RunStatus; current_node: string }) => void,
    onError?: (err: any) => void,
    onDone?: (status: string) => void,
    lastEventId?: string
  ): () => void {
    let eventSource: EventSource | null = null;
    let isCleanedUp = false;
    let reconnectTimeout: any = null;
    let currentLastEventId = lastEventId;
    let isTerminal = false;

    // Asynchronously request single-purpose stream ticket and connect with auto-refresh on reconnect
    const connect = async () => {
      if (isCleanedUp || isTerminal) return;

      try {
        const ticketRes = await this.createStreamTicket(runId);
        if (isCleanedUp || isTerminal) return;

        const queryParams = new URLSearchParams();
        if (ticketRes?.ticket) {
          queryParams.set("ticket", ticketRes.ticket);
        }
        if (currentLastEventId) {
          queryParams.set("last_event_id", currentLastEventId);
        }

        const queryString = queryParams.toString();
        const url = `${API_BASE}/api/v1/runs/${runId}/stream${queryString ? `?${queryString}` : ""}`;

        if (eventSource) {
          eventSource.close();
        }
        eventSource = new EventSource(url);

        eventSource.addEventListener("agent_event", (e: MessageEvent) => {
          try {
            const parsed = JSON.parse(e.data);
            if (parsed?.id) {
              currentLastEventId = parsed.id;
            }
            onEvent(parsed);
          } catch {
            // ignore parse error
          }
        });

        eventSource.addEventListener("status_update", (e: MessageEvent) => {
          if (onStatusUpdate) {
            try {
              const parsed = JSON.parse(e.data);
              onStatusUpdate(parsed);
            } catch {
              // ignore parse error
            }
          }
        });

        eventSource.addEventListener("done", (e: MessageEvent) => {
          isTerminal = true;
          if (onDone) {
            try {
              const parsed = JSON.parse(e.data);
              onDone(parsed.status);
            } catch {
              onDone("COMPLETED");
            }
          }
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
        });

        eventSource.onerror = (err) => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          if (!isCleanedUp && !isTerminal) {
            if (onError) onError(err);
            // Refresh stream ticket and reconnect after backoff
            reconnectTimeout = setTimeout(() => {
              if (!isCleanedUp && !isTerminal) {
                connect();
              }
            }, 3000);
          }
        };
      } catch (err) {
        if (!isCleanedUp && !isTerminal) {
          if (onError) onError(err);
          reconnectTimeout = setTimeout(() => {
            if (!isCleanedUp && !isTerminal) {
              connect();
            }
          }, 3000);
        }
      }
    };

    connect();

    return () => {
      isCleanedUp = true;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (eventSource) {
        eventSource.close();
      }
    };
  },

  // GitHub Real-time & Quick Solver
  async connectGitHub(
    token?: string,
    username?: string
  ): Promise<{
    success: boolean;
    profile: GitHubUserProfile;
    is_authenticated: boolean;
    permissions?: GitHubTokenPermissions | null;
  }> {
    return fetchWithAuth<{
      success: boolean;
      profile: GitHubUserProfile;
      is_authenticated: boolean;
      permissions?: GitHubTokenPermissions | null;
    }>(
      "/api/v1/github/connect",
      {
        method: "POST",
        body: JSON.stringify({ token, username }),
      }
    );
  },

  async getTokenPermissions(token?: string): Promise<GitHubTokenPermissions> {
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    return fetchWithAuth<GitHubTokenPermissions>(
      `/api/v1/github/token-permissions${params.toString() ? `?${params.toString()}` : ""}`
    );
  },

  async getUserRepositories(
    username?: string,
    token?: string,
    page = 1,
    perPage = 30
  ): Promise<any[]> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (username) params.set("username", username);
    if (token) params.set("token", token);
    return fetchWithAuth<any[]>(`/api/v1/github/user/repos?${params.toString()}`);
  },

  async getUserIssues(
    username?: string,
    token?: string,
    state = "open",
    page = 1,
    perPage = 30
  ): Promise<GitHubAccountIssue[]> {
    const params = new URLSearchParams({ state, page: String(page), per_page: String(perPage) });
    if (username) params.set("username", username);
    if (token) params.set("token", token);
    return fetchWithAuth<GitHubAccountIssue[]>(`/api/v1/github/user/issues?${params.toString()}`);
  },

  async inspectRepository(
    url: string,
    token?: string
  ): Promise<GitHubInspectResult> {
    return fetchWithAuth<GitHubInspectResult>("/api/v1/github/inspect", {
      method: "POST",
      body: JSON.stringify({ url, token }),
    });
  },

  async quickSolve(
    target: string,
    customProblem?: string,
    issueNumber?: number,
    token?: string
  ): Promise<QuickSolverResult> {
    return fetchWithAuth<QuickSolverResult>("/api/v1/github/quick-solve", {
      method: "POST",
      body: JSON.stringify({
        target,
        custom_problem: customProblem,
        issue_number: issueNumber,
        token,
      }),
    }, 45000);
  },

  async importRepository(
    target: string,
    syncIssues = true,
    token?: string
  ): Promise<{ success: boolean; repository: any; synced_issues_count: number }> {
    return fetchWithAuth<{ success: boolean; repository: any; synced_issues_count: number }>(
      "/api/v1/github/import-repository",
      {
        method: "POST",
        body: JSON.stringify({ target, sync_issues: syncIssues, token }),
      }
    );
  },

  async publishSolution(payload: {
    target: string;
    issue_number?: number | null;
    issue_title?: string;
    diagnosis?: string;
    root_cause?: string;
    code_patch?: string;
    verification_steps?: string[];
    custom_comment?: string;
    close_issue?: boolean;
    add_solved_label?: boolean;
    token?: string;
  }): Promise<PublishSolutionResult> {
    return fetchWithAuth<PublishSolutionResult>("/api/v1/github/publish-solution", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
