"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Tag, GitBranch, PlayCircle, ExternalLink, Clock, Search, Filter } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { api } from "@/lib/api/client";
import { Issue, Repository, Run } from "@/types";
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
    try {
      const runs = await api.getRuns(issue.repository_id);
      setRunsForIssue(runs.filter((r) => r.issue_id === issue.id));
    } catch {
      setRunsForIssue([]);
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
                          : "bg-forge-lime/15 text-forge-lime border-forge-lime/30"
                      }`}>
                        {repositories[selectedIssue.repository_id]?.full_name?.startsWith("devsquad/")
                          ? "LOCAL DATABASE"
                          : "LIVE GITHUB"}
                      </span>
                      <button
                        onClick={() => setIsDispatcherOpen(true)}
                        className="px-3 py-1.5 rounded-lg bg-forge-lime hover:bg-forge-lime/90 text-black text-xs font-mono font-bold flex items-center gap-1.5 shadow-[0_0_10px_rgba(215,255,100,0.3)] transition-all"
                      >
                        <PlayCircle className="w-3.5 h-3.5" />
                        Launch Agent Run
                      </button>
                      <StatusBadge status={selectedIssue.state} />
                    </div>
                  </div>

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
