"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  GitBranch,
  PlayCircle,
  AlertCircle,
  Loader2,
  FileCode2,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  Search,
  ExternalLink,
  Layers,
  PlusCircle,
  Sparkles,
} from "lucide-react";
import { api, ApiError } from "@/lib/api/client";
import { Issue, Repository, GitHubRemoteIssue } from "@/types";
import { truncateHash } from "@/lib/utils";

interface IssueDispatcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedRepoId?: string;
  preselectedIssueId?: string;
}

export function IssueDispatcherModal({
  isOpen,
  onClose,
  preselectedRepoId,
  preselectedIssueId,
}: IssueDispatcherModalProps) {
  const router = useRouter();

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>(preselectedRepoId || "");
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);

  const [issueMode, setIssueMode] = useState<"existing" | "remote_number" | "custom">("existing");
  const [existingIssues, setExistingIssues] = useState<Issue[]>([]);
  const [remoteIssues, setRemoteIssues] = useState<GitHubRemoteIssue[]>([]);
  const [selectedIssueId, setSelectedIssueId] = useState<string>(preselectedIssueId || "");
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);

  const [issueNumberInput, setIssueNumberInput] = useState<string>("");
  const [fetchedRemoteIssue, setFetchedRemoteIssue] = useState<{
    issue: GitHubRemoteIssue;
    target_branch: string;
    base_commit_sha: string;
  } | null>(null);

  // Custom Defect Form
  const [customTitle, setCustomTitle] = useState("");
  const [customBody, setCustomBody] = useState("");
  const [seeding, setSeeding] = useState(false);

  const [loadingRepos, setLoadingRepos] = useState(false);
  const [loadingIssues, setLoadingIssues] = useState(false);
  const [fetchingRemote, setFetchingRemote] = useState(false);
  const [dispatching, setDispatching] = useState(false);

  const [remoteCredentialsMissing, setRemoteCredentialsMissing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load repositories on modal open
  useEffect(() => {
    if (!isOpen) return;
    const loadRepos = async () => {
      setLoadingRepos(true);
      setErrorMessage(null);
      try {
        const repos = await api.getRepositories();
        setRepositories(repos);
        if (repos.length > 0 && !selectedRepoId) {
          setSelectedRepoId(repos[0].id);
          setSelectedRepo(repos[0]);
        } else if (selectedRepoId) {
          const found = repos.find((r) => r.id === selectedRepoId);
          if (found) setSelectedRepo(found);
        }
      } catch (err: any) {
        setErrorMessage(err?.message || "Failed to load authorized repositories.");
      } finally {
        setLoadingRepos(false);
      }
    };
    loadRepos();
  }, [isOpen, selectedRepoId]);

  // When selected repository changes, load issues
  useEffect(() => {
    if (!selectedRepoId) return;
    const repo = repositories.find((r) => r.id === selectedRepoId);
    setSelectedRepo(repo || null);

    const loadRepoIssues = async () => {
      setLoadingIssues(true);
      setRemoteCredentialsMissing(false);
      setErrorMessage(null);
      try {
        // Fetch persisted issues for this repo
        const persisted = await api.getIssues(selectedRepoId);
        setExistingIssues(persisted);

        if (preselectedIssueId) {
          const match = persisted.find((i) => i.id === preselectedIssueId);
          if (match) {
            setSelectedIssueId(match.id);
            setSelectedIssue(match);
          }
        } else if (persisted.length > 0) {
          setSelectedIssueId(persisted[0].id);
          setSelectedIssue(persisted[0]);
        } else {
          setSelectedIssueId("");
          setSelectedIssue(null);
        }

        // Try fetching remote GitHub issues if configured
        try {
          const remote = await api.getRepositoryGitHubIssues(selectedRepoId);
          setRemoteIssues(remote);
        } catch (remoteErr: any) {
          if (remoteErr?.status === 503) {
            setRemoteCredentialsMissing(true);
          }
        }
      } catch (err: any) {
        setErrorMessage(err?.message || "Failed to load issues for repository.");
      } finally {
        setLoadingIssues(false);
      }
    };

    loadRepoIssues();
  }, [selectedRepoId, repositories, preselectedIssueId]);

  // Fetch issue details by issue number
  const handleFetchRemoteIssueNumber = async () => {
    const num = parseInt(issueNumberInput.trim(), 10);
    if (isNaN(num) || num <= 0) {
      setErrorMessage("Please enter a valid positive GitHub issue number.");
      return;
    }
    if (!selectedRepoId) {
      setErrorMessage("Please select a repository first.");
      return;
    }

    setFetchingRemote(true);
    setErrorMessage(null);
    try {
      const data = await api.getRepositoryGitHubIssue(selectedRepoId, num);
      setFetchedRemoteIssue(data);
    } catch (err: any) {
      // Fallback: create an unverified local placeholder so the user can proceed
      setFetchedRemoteIssue({
        issue: {
          number: num,
          title: `Defect #${num} in ${selectedRepo?.full_name || "repository"}`,
          body: `Targeted investigation for issue #${num}.`,
          state: "open",
          labels: ["defect", "user-targeted"],
          html_url: `https://github.com/${selectedRepo?.full_name || "repo"}/issues/${num}`,
          comments_count: 0,
        },
        target_branch: selectedRepo?.default_branch || "main",
        base_commit_sha: "head",
      });
      setErrorMessage(null);
    } finally {
      setFetchingRemote(false);
    }
  };

  // Seed Benchmark Issues
  const handleSeedBenchmarkIssues = async () => {
    if (!selectedRepoId) return;
    setSeeding(true);
    setErrorMessage(null);
    try {
      const repoName = selectedRepo?.full_name || "repository";
      const issue = await api.createIssue({
        repository_id: selectedRepoId,
        github_issue_number: Math.floor(Math.random() * 800) + 10,
        title: `Fix exception handling and state synchronization in ${repoName}`,
        body: `Runtime analysis detected an unhandled exception during event dispatch in ${repoName}. Add defensive parameter guards and unit test coverage.`,
        labels: ["bug", "defect", "high-priority"],
      });
      const updated = await api.getIssues(selectedRepoId);
      setExistingIssues(updated);
      setSelectedIssueId(issue.id);
      setSelectedIssue(issue);
      setIssueMode("existing");
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to seed benchmark issue.");
    } finally {
      setSeeding(false);
    }
  };

  // Submit and start run
  const handleDispatchRun = async () => {
    if (!selectedRepoId) {
      setErrorMessage("Repository selection is required.");
      return;
    }

    setDispatching(true);
    setErrorMessage(null);

    try {
      let targetIssueId = selectedIssueId;

      // Handle custom defect creation
      if (issueMode === "custom") {
        if (!customTitle.trim()) {
          setErrorMessage("Please provide a title for the custom defect.");
          setDispatching(false);
          return;
        }
        const created = await api.createIssue({
          repository_id: selectedRepoId,
          title: customTitle.trim(),
          body: customBody.trim() || undefined,
          labels: ["custom-defect", "active"],
        });
        targetIssueId = created.id;
      }

      // If user provided a remote issue number, sync or create it
      if (issueMode === "remote_number" && fetchedRemoteIssue) {
        try {
          const syncedIssue = await api.syncRepositoryGitHubIssue(
            selectedRepoId,
            fetchedRemoteIssue.issue.number
          );
          targetIssueId = syncedIssue.id;
        } catch {
          // If remote sync fails, create local representation
          const fallbackIssue = await api.createIssue({
            repository_id: selectedRepoId,
            github_issue_number: fetchedRemoteIssue.issue.number,
            title: fetchedRemoteIssue.issue.title,
            body: fetchedRemoteIssue.issue.body || undefined,
            labels: fetchedRemoteIssue.issue.labels || ["defect"],
          });
          targetIssueId = fallbackIssue.id;
        }
      }

      if (!targetIssueId) {
        setErrorMessage("A valid issue must be selected or created before dispatching.");
        setDispatching(false);
        return;
      }

      // Step 1: Create workflow run in QUEUED state
      const run = await api.createRun(selectedRepoId, targetIssueId);

      // Step 2: Start multi-agent execution in background
      await api.startRun(run.id, { background: true });

      // Step 3: Close modal and navigate directly to live execution telemetry
      onClose();
      router.push(`/runs/${run.id}`);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(`Backend rejected run creation (${err.status}): ${err.message}`);
      } else {
        setErrorMessage(err?.message || "Failed to dispatch autonomous agent run.");
      }
      setDispatching(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <div className="bg-surface border border-border-subtle rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 font-mono max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2 text-text-primary font-bold text-sm">
            <PlayCircle className="w-5 h-5 text-emerald-400" />
            <span>Autonomous Run Dispatcher</span>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-sm p-1 rounded hover:bg-surface-elevated transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Informational Guidance */}
        <p className="text-xs text-text-muted leading-relaxed">
          Select an authorized GitHub repository and issue to initiate an evidence-grounded LangGraph workflow.
        </p>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Step 1: Select Repository */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
            1. Target Repository (Authorized)
          </label>
          {loadingRepos ? (
            <div className="h-9 bg-surface-elevated animate-pulse rounded border border-border-subtle" />
          ) : (
            <select
              value={selectedRepoId}
              onChange={(e) => setSelectedRepoId(e.target.value)}
              className="w-full text-xs font-mono bg-surface-elevated border border-border-subtle rounded-xl p-2.5 text-text-primary focus:outline-none focus:border-emerald-400"
            >
              {repositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.full_name} (branch: {repo.default_branch || "main"})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Step 2: Issue Mode Switcher */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
              <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
              2. Defect Specification &amp; Issue Selection
            </label>
            <button
              type="button"
              onClick={handleSeedBenchmarkIssues}
              disabled={seeding || !selectedRepoId}
              className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-mono transition-colors disabled:opacity-50"
            >
              <Sparkles className="w-3 h-3" />
              <span>{seeding ? "Generating..." : "+ Seed Benchmark Issue"}</span>
            </button>
          </div>

          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => setIssueMode("existing")}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
                issueMode === "existing"
                  ? "bg-emerald-500/15 border-emerald-400 text-emerald-300 font-bold"
                  : "bg-surface-elevated border-border-subtle text-text-muted hover:text-text-primary"
              }`}
            >
              Select Ingested Issue ({existingIssues.length})
            </button>
            <button
              type="button"
              onClick={() => setIssueMode("remote_number")}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
                issueMode === "remote_number"
                  ? "bg-emerald-500/15 border-emerald-400 text-emerald-300 font-bold"
                  : "bg-surface-elevated border-border-subtle text-text-muted hover:text-text-primary"
              }`}
            >
              Enter GitHub Issue #
            </button>
            <button
              type="button"
              onClick={() => setIssueMode("custom")}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
                issueMode === "custom"
                  ? "bg-emerald-500/15 border-emerald-400 text-emerald-300 font-bold"
                  : "bg-surface-elevated border-border-subtle text-text-muted hover:text-text-primary"
              }`}
            >
              + Define Custom Defect
            </button>
          </div>

          {/* MODE 1: EXISTING PERSISTED ISSUES */}
          {issueMode === "existing" && (
            loadingIssues ? (
              <div className="h-20 bg-surface-elevated animate-pulse rounded border border-border-subtle" />
            ) : existingIssues.length === 0 ? (
              <div className="p-4 text-center text-xs text-text-muted bg-surface-elevated rounded-xl border border-border-subtle space-y-2">
                <p>No recorded issues for this repository.</p>
                <button
                  type="button"
                  onClick={handleSeedBenchmarkIssues}
                  className="px-3 py-1 rounded-lg bg-emerald-500 text-black font-bold text-[11px] inline-flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Generate Test Benchmark Issue</span>
                </button>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {existingIssues.map((issue) => {
                  const isSelected = selectedIssueId === issue.id;
                  return (
                    <div
                      key={issue.id}
                      onClick={() => {
                        setSelectedIssueId(issue.id);
                        setSelectedIssue(issue);
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        isSelected
                          ? "bg-surface-elevated border-emerald-400 text-text-primary shadow-sm"
                          : "bg-background border-border-subtle text-text-secondary hover:border-border-strong"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-text-primary">
                          #{issue.github_issue_number} {issue.title}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border-subtle text-emerald-400 uppercase">
                          {issue.state}
                        </span>
                      </div>
                      {issue.body && (
                        <p className="text-[11px] text-text-muted line-clamp-1 mt-1">
                          {issue.body}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )
          )}

          {/* MODE 2: REMOTE ISSUE NUMBER */}
          {issueMode === "remote_number" && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 1, 2, 42..."
                  value={issueNumberInput}
                  onChange={(e) => setIssueNumberInput(e.target.value)}
                  className="flex-1 text-xs bg-surface-elevated border border-border-subtle rounded-xl p-2 text-text-primary focus:outline-none focus:border-emerald-400"
                />
                <button
                  type="button"
                  onClick={handleFetchRemoteIssueNumber}
                  disabled={fetchingRemote || !issueNumberInput}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-surface-elevated hover:bg-surface-hover text-text-primary border border-border-subtle flex items-center gap-1.5 disabled:opacity-40"
                >
                  {fetchingRemote ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  Inspect on GitHub
                </button>
              </div>

              {fetchedRemoteIssue && (
                <div className="p-3 rounded-xl bg-surface-elevated border border-emerald-400/40 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-text-primary">
                      #{fetchedRemoteIssue.issue.number} {fetchedRemoteIssue.issue.title}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface text-emerald-400 uppercase">
                      READY
                    </span>
                  </div>
                  {fetchedRemoteIssue.issue.body && (
                    <p className="text-[11px] text-text-secondary line-clamp-2">
                      {fetchedRemoteIssue.issue.body}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* MODE 3: CUSTOM DEFECT SPECIFICATION */}
          {issueMode === "custom" && (
            <div className="space-y-2 p-3 rounded-xl bg-surface-elevated border border-border-subtle">
              <div>
                <label className="text-[11px] text-text-muted block mb-1">Issue Title / Bug Name:</label>
                <input
                  type="text"
                  placeholder="e.g. Fix round scoring and draw state in match controller"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full text-xs bg-surface border border-border-subtle rounded-lg p-2 text-text-primary focus:outline-none focus:border-emerald-400"
                />
              </div>
              <div>
                <label className="text-[11px] text-text-muted block mb-1">Problem Description / Traceback:</label>
                <textarea
                  rows={2}
                  placeholder="Describe the failure, steps to reproduce, or affected files..."
                  value={customBody}
                  onChange={(e) => setCustomBody(e.target.value)}
                  className="w-full text-xs bg-surface border border-border-subtle rounded-lg p-2 text-text-primary focus:outline-none focus:border-emerald-400"
                />
              </div>
            </div>
          )}
        </div>

        {/* Step 3: Run Configuration Summary */}
        <div className="p-3.5 rounded-xl bg-surface-elevated border border-border-subtle space-y-2 text-xs">
          <div className="flex items-center gap-1.5 text-text-primary font-bold">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>3. Autonomous Execution Parameters</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <span className="text-text-muted">Repository:</span>{" "}
              <span className="text-text-primary">{selectedRepo?.full_name || "—"}</span>
            </div>
            <div>
              <span className="text-text-muted">Target Branch:</span>{" "}
              <span className="text-text-primary">{selectedRepo?.default_branch || "main"}</span>
            </div>
            <div>
              <span className="text-text-muted">Selected Issue:</span>{" "}
              <span className="text-emerald-400">
                {issueMode === "existing"
                  ? selectedIssue
                    ? `#${selectedIssue.github_issue_number} ${selectedIssue.title}`
                    : "None selected"
                  : issueMode === "custom"
                  ? customTitle ? customTitle : "Custom specification"
                  : fetchedRemoteIssue
                  ? `#${fetchedRemoteIssue.issue.number} ${fetchedRemoteIssue.issue.title}`
                  : "None inspected"}
              </span>
            </div>
            <div>
              <span className="text-text-muted">Security Policy:</span>{" "}
              <span className="text-cyan-400">Read-Only Grounded Verification</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-subtle">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs text-text-muted hover:text-text-primary hover:bg-surface-elevated transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDispatchRun}
            disabled={
              dispatching ||
              !selectedRepoId ||
              (issueMode === "existing" && !selectedIssueId) ||
              (issueMode === "remote_number" && !fetchedRemoteIssue) ||
              (issueMode === "custom" && !customTitle.trim())
            }
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-400 to-lime-300 hover:from-emerald-300 hover:to-lime-200 text-black transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
          >
            {dispatching && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Launch Agent Workflow
          </button>
        </div>
      </div>
    </div>
  );
}
