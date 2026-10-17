"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { GitBranch, AlertCircle, PlayCircle, ShieldCheck, FolderGit2 } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { api } from "@/lib/api/client";
import { Issue, Repository, Run } from "@/types";
import { formatDate } from "@/lib/utils";

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [associatedIssues, setAssociatedIssues] = useState<Issue[]>([]);
  const [associatedRuns, setAssociatedRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRepositories = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRepositories();
      setRepositories(data);
      if (data.length > 0 && !selectedRepo) {
        selectRepo(data[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load registered repositories");
    } finally {
      setLoading(false);
    }
  };

  const selectRepo = async (repo: Repository) => {
    setSelectedRepo(repo);
    setDetailsLoading(true);
    setAssociatedIssues([]);
    setAssociatedRuns([]);
    try {
      const [issues, runs] = await Promise.allSettled([
        api.getIssues(repo.id),
        api.getRuns(repo.id),
      ]);
      if (issues.status === "fulfilled") setAssociatedIssues(issues.value);
      if (runs.status === "fulfilled") setAssociatedRuns(runs.value);
    } catch (err) {
      console.error("Failed loading associated records", err);
    } finally {
      setDetailsLoading(false);
    }
  };

  useEffect(() => {
    loadRepositories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadRepositories} title="Repositories" subtitle="Registered Code Repositories &amp; Workspaces" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Repositories Rail */}
          <div className="lg:col-span-1 space-y-3">
            <h2 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
              Repositories ({repositories.length})
            </h2>

            {loading ? (
              <div className="space-y-2">
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
              </div>
            ) : repositories.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
                No repositories registered in platform.
              </div>
            ) : (
              <div className="space-y-2">
                {repositories.map((repo) => {
                  const isSelected = selectedRepo?.id === repo.id;
                  return (
                    <div
                      key={repo.id}
                      onClick={() => selectRepo(repo)}
                      className={`p-3.5 rounded-lg border cursor-pointer transition-all relative ${
                        isSelected
                          ? "bg-surface-elevated border-forge-lime/50 shadow-md ring-1 ring-forge-lime/30"
                          : "bg-surface border-border-subtle hover:border-border-strong hover:bg-surface-elevated/50"
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-forge-lime" />
                      )}
                      <div className="flex items-center justify-between mb-1.5 pl-1">
                        <span className="font-semibold text-xs text-text-primary font-mono truncate">
                          {repo.full_name}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-medium border ${
                            repo.full_name.startsWith("devsquad/")
                              ? "bg-cyan-ice/10 text-cyan-ice border-cyan-ice/20"
                              : "bg-forge-lime/10 text-forge-lime border-forge-lime/20"
                          }`}>
                            {repo.full_name.startsWith("devsquad/") ? "LOCAL DB" : "LIVE GITHUB"}
                          </span>
                          <StatusBadge
                            status={repo.is_active ? "ACTIVE" : "INACTIVE"}
                            size="sm"
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-text-muted font-mono pl-1">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-forge-lime" />
                          {repo.default_branch}
                        </span>
                        <span>ID: {repo.github_repository_id}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Selected Repository Workspace Details */}
          <div className="lg:col-span-2 space-y-6">
            {selectedRepo ? (
              <>
                {/* Repository Details Banner */}
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h2 className="text-base font-bold text-text-primary font-mono">
                          {selectedRepo.full_name}
                        </h2>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle text-text-muted font-mono">
                          Scoped: {associatedIssues.length} {associatedIssues.length === 1 ? "Issue" : "Issues"} • {associatedRuns.length} {associatedRuns.length === 1 ? "Run" : "Runs"}
                        </span>
                      </div>
                      <p className="text-xs text-text-secondary mt-0.5 font-mono">
                        {selectedRepo.description || "Core repository target for automated defect resolution."}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${
                        selectedRepo.full_name.startsWith("devsquad/")
                          ? "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30"
                          : "bg-forge-lime/15 text-forge-lime border-forge-lime/30"
                      }`}>
                        {selectedRepo.full_name.startsWith("devsquad/") ? "LOCAL DATABASE FIXTURE" : "LIVE GITHUB REPOSITORY"}
                      </span>
                      <StatusBadge status={selectedRepo.is_active ? "ACTIVE" : "INACTIVE"} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs font-mono">
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Provenance:</span>
                      <span className="text-cyan-ice font-bold">
                        {selectedRepo.full_name.startsWith("devsquad/") ? "SQLite Persisted" : "GitHub Remote"}
                      </span>
                    </div>
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Default Branch:</span>
                      <span className="text-text-primary font-bold">{selectedRepo.default_branch}</span>
                    </div>
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">GitHub Repository ID:</span>
                      <span className="text-text-primary">{selectedRepo.github_repository_id}</span>
                    </div>
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Registered On:</span>
                      <span className="text-text-primary">{formatDate(selectedRepo.created_at)}</span>
                    </div>
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Access Policy:</span>
                      <span className="text-forge-lime font-bold flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" /> AUTHORIZED
                      </span>
                    </div>
                  </div>
                </div>

                {/* Associated Issues */}
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-cyan-ice" />
                      Associated Issues ({associatedIssues.length})
                    </h3>
                  </div>

                  {detailsLoading ? (
                    <div className="h-14 bg-surface-elevated animate-pulse rounded" />
                  ) : associatedIssues.length === 0 ? (
                    <div className="p-4 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                      No issues registered for this repository yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {associatedIssues.map((issue) => (
                        <div
                          key={issue.id}
                          className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs font-mono flex items-start justify-between"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-forge-lime font-bold">
                                #{issue.github_issue_number}
                              </span>
                              <span className="text-text-primary font-medium">
                                {issue.title}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1.5">
                              {issue.labels?.map((label) => (
                                <span
                                  key={label}
                                  className="px-1.5 py-0.2 rounded bg-surface text-text-muted border border-border-subtle text-[10px]"
                                >
                                  {label}
                                </span>
                              ))}
                            </div>
                          </div>
                          <StatusBadge status={issue.state} size="sm" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Associated Workflow Runs */}
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      <PlayCircle className="w-3.5 h-3.5 text-forge-lime" />
                      Workflow Execution History ({associatedRuns.length})
                    </h3>
                  </div>

                  {detailsLoading ? (
                    <div className="h-14 bg-surface-elevated animate-pulse rounded" />
                  ) : associatedRuns.length === 0 ? (
                    <div className="p-4 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                      No execution runs initiated for this repository yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {associatedRuns.map((run) => (
                        <div
                          key={run.id}
                          className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs font-mono flex items-center justify-between"
                        >
                          <div>
                            <span className="text-forge-lime font-bold">
                              {run.id.slice(0, 8)}…
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
                              Inspect
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
                Select a repository to inspect its details and associated engineering records.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
