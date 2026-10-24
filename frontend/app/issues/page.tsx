"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  AlertCircle,
  Tag,
  GitBranch,
  PlayCircle,
  ExternalLink,
  Clock,
  Search,
  Filter,
  Zap,
  Sparkles,
  FileCode,
  CheckCircle2,
  Copy,
  Check,
  Terminal,
  RefreshCw,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { api } from "@/lib/api/client";
import { getStoredGitHubToken } from "@/lib/auth/githubSession";
import { Issue, Repository, Run, QuickSolverResult } from "@/types";
import { formatDate } from "@/lib/utils";
import { IssueDispatcherModal } from "@/components/runs/IssueDispatcherModal";

export default function IssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [repositories, setRepositories] = useState<Record<string, Repository>>({});
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [runsForIssue, setRunsForIssue] = useState<Run[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterState, setFilterState] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDispatcherOpen, setIsDispatcherOpen] = useState(false);

  // Quick Solve state
  const [isSolving, setIsSolving] = useState(false);
  const [quickResult, setQuickResult] = useState<QuickSolverResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishSuccessUrl, setPublishSuccessUrl] = useState<string | null>(null);

  const handlePublishSolutionToGitHub = async () => {
    if (!selectedIssue || !quickResult) return;
    setPublishing(true);
    setPublishSuccessUrl(null);
    const repo = repositories[selectedIssue.repository_id];
    const targetName = repo?.full_name || selectedIssue.repository_id;
    let token = getStoredGitHubToken() || undefined;

    if (!token) {
      const promptToken = window.prompt(
        "To post this solution to GitHub, please enter your GitHub Personal Access Token (with 'repo' scope):"
      );
      if (!promptToken || !promptToken.trim()) {
        setPublishing(false);
        return;
      }
      token = promptToken.trim();
      localStorage.setItem("devsquad_github_token", token);
      window.dispatchEvent(new Event("devsquad_github_session_change"));
    }

    try {
      const res = await api.publishSolution({
        target: targetName,
        issue_number: selectedIssue.github_issue_number,
        diagnosis: quickResult.problem_diagnosis,
        root_cause: quickResult.root_cause,
        code_patch: quickResult.code_patch,
        verification_steps: quickResult.verification_steps,
        add_solved_label: true,
        close_issue: false,
        token,
      });
      setPublishSuccessUrl(res.comment_url);
    } catch (err: any) {
      alert("Publish Error: " + (err?.message || "Failed to post solution to GitHub"));
    } finally {
      setPublishing(false);
    }
  };

  const loadIssues = async () => {
    setLoading(true);
    setError(null);
    try {
      const [issuesData, reposData] = await Promise.all([
        api.getIssues(),
        api.getRepositories(),
      ]);
      setIssues(issuesData);

      const repoMap: Record<string, Repository> = {};
      reposData.forEach((r) => {
        repoMap[r.id] = r;
      });
      setRepositories(repoMap);

      if (issuesData.length > 0 && !selectedIssue) {
        selectIssue(issuesData[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load issues from backend");
    } finally {
      setLoading(false);
    }
  };

  const selectIssue = async (issue: Issue) => {
    setSelectedIssue(issue);
    setQuickResult(null);
    try {
      const runs = await api.getRuns(issue.repository_id);
      setRunsForIssue(runs.filter((r) => r.issue_id === issue.id));
    } catch {
      setRunsForIssue([]);
    }
  };

  const handleQuickSolveForSelected = async () => {
    if (!selectedIssue) return;
    const repo = repositories[selectedIssue.repository_id];
    const targetName = repo?.full_name || selectedIssue.repository_id;

    setIsSolving(true);
    setQuickResult(null);
    const token = getStoredGitHubToken() || undefined;

    try {
      const res = await api.quickSolve(
        targetName,
        selectedIssue.body || undefined,
        selectedIssue.github_issue_number,
        token
      );
      setQuickResult(res);
    } catch (err: any) {
      alert("Quick Solve Error: " + (err?.message || "Analysis failed"));
    } finally {
      setIsSolving(false);
    }
  };

  useEffect(() => {
    loadIssues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredIssues = issues.filter((issue) => {
    const matchesSearch =
      issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(issue.github_issue_number).includes(searchQuery) ||
      (issue.body && issue.body.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesState =
      filterState === "ALL" ? true : issue.state.toLowerCase() === filterState.toLowerCase();

    return matchesSearch && matchesState;
  });

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadIssues} title="Issues" subtitle="Ingested Defect Queue &amp; Specifications" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Issue Browser Left Rail */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                Defect Queue ({filteredIssues.length})
              </h2>
              <button
                onClick={() => setIsDispatcherOpen(true)}
                className="text-[11px] font-mono text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-bold"
              >
                + Dispatch Run
              </button>
            </div>

            {/* Search & State Filter Controls */}
            <div className="space-y-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-text-muted" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search issues..."
                  className="w-full pl-9 pr-3 py-1.5 rounded bg-surface border border-border-subtle text-xs font-mono text-text-primary placeholder-text-muted focus:outline-none focus:border-forge-lime"
                />
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-3 h-3 text-text-muted" />
                <select
                  value={filterState}
                  onChange={(e) => setFilterState(e.target.value)}
                  className="w-full py-1 px-2 rounded bg-surface border border-border-subtle text-xs font-mono text-text-secondary focus:outline-none focus:border-forge-lime"
                >
                  <option value="ALL">All States</option>
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="space-y-2">
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
              </div>
            ) : filteredIssues.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
                No issues match your filter query.
              </div>
            ) : (
              <div className="space-y-2">
                {filteredIssues.map((issue) => {
                  const isSelected = selectedIssue?.id === issue.id;
                  const repo = repositories[issue.repository_id];

                  return (
                    <div
                      key={issue.id}
                      onClick={() => selectIssue(issue)}
                      className={`p-3.5 rounded-lg border cursor-pointer transition-all relative ${
                        isSelected
                          ? "bg-surface-elevated border-forge-lime/50 shadow-md ring-1 ring-forge-lime/30"
                          : "bg-surface border-border-subtle hover:border-border-strong hover:bg-surface-elevated/50"
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-forge-lime" />
                      )}
                      <div className="flex items-start justify-between gap-2 mb-1.5 pl-1">
                        <span className="font-semibold text-xs text-text-primary font-mono leading-snug">
                          #{issue.github_issue_number} {issue.title}
                        </span>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <StatusBadge status={issue.state} size="sm" />
                          <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                            repo?.full_name?.startsWith("devsquad/")
                              ? "bg-cyan-ice/10 text-cyan-ice border border-cyan-ice/20"
                              : "bg-forge-lime/10 text-forge-lime border border-forge-lime/20"
                          }`}>
                            {repo?.full_name?.startsWith("devsquad/") ? "LOCAL DB" : "LIVE GITHUB"}
                          </span>
                        </div>
                      </div>

                      <div className="text-[11px] text-text-muted font-mono flex items-center gap-2 pl-1">
                        <GitBranch className="w-3 h-3 text-forge-lime" />
                        <span className="truncate">
                          {repo ? repo.full_name : issue.repository_id.slice(0, 8)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Issue Details View */}
          <div className="lg:col-span-2 space-y-6">
            {selectedIssue ? (
              <>
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-border-subtle pb-4">
                    <div>
                      <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-1 flex-wrap">
                        <GitBranch className="w-3.5 h-3.5 text-forge-lime" />
                        <span>
                          {repositories[selectedIssue.repository_id]?.full_name ||
                            selectedIssue.repository_id}
                        </span>
                        <span>•</span>
                        <Clock className="w-3.5 h-3.5" />
                        <span>{formatDate(selectedIssue.created_at)}</span>
                        <span>•</span>
                        <span className="text-[10px] text-cyan-ice font-semibold">
                          Provenance: {repositories[selectedIssue.repository_id]?.full_name?.startsWith("devsquad/") ? "Persisted Defect Model" : "GitHub Issue API"}
                        </span>
                      </div>
                      <h2 className="text-base font-bold text-text-primary font-mono">
                        #{selectedIssue.github_issue_number} {selectedIssue.title}
                      </h2>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${
                        repositories[selectedIssue.repository_id]?.full_name?.startsWith("devsquad/")
                          ? "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30"
                          : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                      }`}>
                        {repositories[selectedIssue.repository_id]?.full_name?.startsWith("devsquad/")
                          ? "LOCAL DATABASE"
                          : "LIVE GITHUB"}
                      </span>
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={handleQuickSolveForSelected}
                        disabled={isSolving}
                        className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-mono font-bold flex items-center gap-1.5 shadow-md disabled:opacity-50 transition-all"
                      >
                        <Zap className={`w-3.5 h-3.5 ${isSolving ? "animate-spin" : ""}`} />
                        {isSolving ? "Diagnosing..." : "Instant AI Solve"}
                      </motion.button>
                      <button
                        onClick={() => setIsDispatcherOpen(true)}
                        className="px-3 py-1.5 rounded-lg bg-surface-elevated hover:bg-surface-hover border border-border-subtle text-text-primary text-xs font-mono font-bold flex items-center gap-1.5 transition-all"
                      >
                        <PlayCircle className="w-3.5 h-3.5 text-emerald-400" />
                        Launch Agent Run
                      </button>
                      <StatusBadge status={selectedIssue.state} />
                    </div>
                  </div>

                  {/* Instant AI Solution Card if available */}
                  <AnimatePresence>
                    {quickResult && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/10 space-y-3"
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                            <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">
                              Instant Diagnostic & Solution
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                              {quickResult.execution_time_seconds}s
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <motion.button
                              whileHover={{ scale: 1.03 }}
                              whileTap={{ scale: 0.97 }}
                              disabled={publishing}
                              onClick={handlePublishSolutionToGitHub}
                              className="px-2.5 py-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-mono font-bold text-[11px] flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
                              title="Publish this solution comment directly to the GitHub issue thread"
                            >
                              {publishing ? (
                                <>
                                  <RefreshCw className="w-3 h-3 animate-spin text-black" />
                                  <span>Publishing...</span>
                                </>
                              ) : (
                                <>
                                  <ExternalLink className="w-3 h-3 text-black" />
                                  <span>Publish to GitHub</span>
                                </>
                              )}
                            </motion.button>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(quickResult.code_patch);
                                setCopied(true);
                                setTimeout(() => setCopied(false), 2000);
                              }}
                              className="px-2 py-1 rounded bg-surface border border-border-subtle text-[11px] font-mono text-text-muted hover:text-emerald-400 flex items-center gap-1 transition-colors"
                            >
                              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              {copied ? "Copied Diff" : "Copy Diff"}
                            </button>
                          </div>
                        </div>

                        {publishSuccessUrl && (
                          <div className="p-2.5 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-xs font-mono text-cyan-300 flex items-center justify-between">
                            <span className="flex items-center gap-2 font-semibold">
                              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                              Solution comment published to GitHub issue!
                            </span>
                            <a
                              href={publishSuccessUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 text-[11px] flex items-center gap-1 font-semibold transition-colors"
                            >
                              <span>View on GitHub</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        )}

                        <div className="text-xs text-text-primary space-y-1.5">
                          <div>
                            <strong className="text-emerald-400 text-[11px] font-mono uppercase block">Root Cause:</strong>
                            <p className="text-xs bg-surface p-2 rounded border border-border-subtle font-mono text-emerald-300">
                              {quickResult.root_cause}
                            </p>
                          </div>
                          <div>
                            <strong className="text-text-muted text-[11px] font-mono uppercase block mt-2">Proposed Fix Diff:</strong>
                            <pre className="p-3 rounded bg-background border border-border-subtle font-mono text-[11px] text-text-primary overflow-x-auto max-h-48 whitespace-pre-wrap">
                              {quickResult.code_patch}
                            </pre>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Labels */}
                  {selectedIssue.labels && selectedIssue.labels.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedIssue.labels.map((lbl) => (
                        <span
                          key={lbl}
                          className="px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle text-text-secondary text-xs font-mono flex items-center gap-1"
                        >
                          <Tag className="w-2.5 h-2.5 text-text-muted" />
                          {lbl}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Body Content */}
                  <div className="p-4 rounded bg-[#0E1114] border border-border-subtle text-xs font-mono text-text-primary whitespace-pre-wrap leading-relaxed">
                    {selectedIssue.body}
                  </div>

                  {selectedIssue.html_url && (
                    <div>
                      <a
                        href={selectedIssue.html_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-mono text-forge-lime hover:underline inline-flex items-center gap-1"
                      >
                        Open on GitHub <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>

                {/* Workflow Runs Associated With This Issue */}
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      <PlayCircle className="w-3.5 h-3.5 text-forge-lime" />
                      Associated Agent Runs ({runsForIssue.length})
                    </h3>
                  </div>

                  {runsForIssue.length === 0 ? (
                    <div className="p-4 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                      No agent workflow executions currently associated with this issue.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {runsForIssue.map((run) => (
                        <div
                          key={run.id}
                          className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs font-mono flex items-center justify-between"
                        >
                          <div>
                            <span className="text-forge-lime font-bold">
                              Run {run.id.slice(0, 8)}…
                            </span>
                            <span className="text-text-muted ml-3">
                              stage: {run.current_node}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <StatusBadge status={run.status} size="sm" />
                            <Link
                              href={`/runs/${run.id}`}
                              className="px-2.5 py-1 rounded bg-surface hover:bg-surface-hover text-text-primary border border-border-subtle text-[11px]"
                            >
                              Inspect Run
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
                Select an issue from the queue to inspect its technical specification.
              </div>
            )}
          </div>
        </div>

        {selectedIssue && (
          <IssueDispatcherModal
            isOpen={isDispatcherOpen}
            onClose={() => setIsDispatcherOpen(false)}
            preselectedRepoId={selectedIssue.repository_id}
            preselectedIssueId={selectedIssue.id}
          />
        )}
      </main>
    </div>
  );
}
