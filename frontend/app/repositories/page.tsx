"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  GitBranch,
  AlertCircle,
  PlayCircle,
  ShieldCheck,
  FolderGit2,
  Plus,
  Sparkles,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  Trash2,
  AlertTriangle,
  Github,
  Search,
  Check,
  Star,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { api } from "@/lib/api/client";
import {
  getStoredGitHubProfile,
  getStoredGitHubToken,
  getStoredGitHubUsername,
  getStoredGitHubPermissions,
} from "@/lib/auth/githubSession";
import { Issue, Repository, Run, GitHubUserProfile, GitHubTokenPermissions } from "@/types";
import { formatDate } from "@/lib/utils";

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [associatedIssues, setAssociatedIssues] = useState<Issue[]>([]);
  const [associatedRuns, setAssociatedRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Quick import state
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  // Deletion state
  const [repoPendingDelete, setRepoPendingDelete] = useState<Repository | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);

  // GitHub Account Repositories state
  const [accountRepos, setAccountRepos] = useState<any[]>([]);
  const [accountReposLoading, setAccountReposLoading] = useState(false);
  const [accountReposError, setAccountReposError] = useState<string | null>(null);
  const [activeAccountUsername, setActiveAccountUsername] = useState<string>("ayushkale06");
  const [usernameInputQuery, setUsernameInputQuery] = useState<string>("ayushkale06");
  const [accountFilter, setAccountFilter] = useState("");
  const [importingRepoName, setImportingRepoName] = useState<string | null>(null);
  const [accountPermissions, setAccountPermissions] = useState<GitHubTokenPermissions | null>(null);

  const confirmDeleteRepository = async () => {
    if (!repoPendingDelete) return;
    setIsDeleting(true);
    setError(null);
    try {
      await api.deleteRepository(repoPendingDelete.id);
      const deletedName = repoPendingDelete.full_name;
      setDeleteSuccess(`Removed repository '${deletedName}' and its scoped data.`);
      const updated = repositories.filter((r) => r.id !== repoPendingDelete.id);
      setRepositories(updated);
      if (selectedRepo?.id === repoPendingDelete.id) {
        if (updated.length > 0) {
          selectRepo(updated[0]);
        } else {
          setSelectedRepo(null);
          setAssociatedIssues([]);
          setAssociatedRuns([]);
        }
      }
      setRepoPendingDelete(null);
      setTimeout(() => setDeleteSuccess(null), 4000);
    } catch (err: any) {
      setError(err?.message || "Failed to remove repository.");
    } finally {
      setIsDeleting(false);
    }
  };

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

  async function handleImportRepository(e: React.FormEvent) {
    e.preventDefault();
    const url = importUrl.trim();
    if (!url) return;

    setImporting(true);
    setError(null);
    setImportSuccess(null);

    const token = getStoredGitHubToken() || undefined;

    try {
      const res = await api.importRepository(url, true, token);
      const importedName = res?.repository?.full_name || url;
      setImportSuccess(`Imported ${importedName} with ${res?.synced_issues_count ?? 0} open issues!`);
      setImportUrl("");
      await loadRepositories();
    } catch (err: any) {
      setError(err?.message || "Failed to import repository.");
    } finally {
      setImporting(false);
    }
  }

  const loadAccountRepositories = async (usernameOverride?: string) => {
    const storedUsername = getStoredGitHubUsername();
    const storedProfile = getStoredGitHubProfile();
    const token = getStoredGitHubToken() || undefined;

    const targetUser = usernameOverride || storedUsername || storedProfile?.login || "ayushkale06";
    setActiveAccountUsername(targetUser);
    setUsernameInputQuery(targetUser);

    setAccountReposLoading(true);
    setAccountReposError(null);
    try {
      const data = await api.getUserRepositories(targetUser, token, 1, 50);
      setAccountRepos(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.warn("Failed to load account repositories:", err);
      setAccountReposError(err?.message || "Failed to load account repositories");
    } finally {
      setAccountReposLoading(false);
    }
  };

  async function handleImportAccountRepo(repoFullName: string) {
    if (!repoFullName) return;
    setImportingRepoName(repoFullName);
    setError(null);
    setImportSuccess(null);
    const token = getStoredGitHubToken() || undefined;
    try {
      const res = await api.importRepository(repoFullName, true, token);
      const importedName = res?.repository?.full_name || repoFullName;
      setImportSuccess(`Imported ${importedName} (${res?.synced_issues_count ?? 0} open issues synced)!`);
      const updatedList = await api.getRepositories();
      setRepositories(Array.isArray(updatedList) ? updatedList : []);
      const match = (updatedList || []).find(
        (r) => r?.full_name && r.full_name.toLowerCase() === repoFullName.toLowerCase()
      );
      if (match) {
        selectRepo(match);
      }
    } catch (err: any) {
      setError(err?.message || `Failed to import ${repoFullName}`);
    } finally {
      setImportingRepoName(null);
    }
  }

  useEffect(() => {
    loadRepositories();
    loadAccountRepositories();
    setAccountPermissions(getStoredGitHubPermissions());

    const handleSessionChange = () => {
      const u = getStoredGitHubUsername();
      const p = getStoredGitHubProfile();
      const perms = getStoredGitHubPermissions();
      const nextUser = u || p?.login || "ayushkale06";
      setActiveAccountUsername(nextUser);
      setUsernameInputQuery(nextUser);
      setAccountPermissions(perms);
      loadAccountRepositories(nextUser);
    };

    window.addEventListener("devsquad_github_session_change", handleSessionChange);
    return () => {
      window.removeEventListener("devsquad_github_session_change", handleSessionChange);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredAccountRepos = (accountRepos || []).filter((repo) => {
    if (!repo) return false;
    if (!accountFilter.trim()) return true;
    const q = accountFilter.toLowerCase();
    return (
      (repo.name && repo.name.toLowerCase().includes(q)) ||
      (repo.full_name && repo.full_name.toLowerCase().includes(q)) ||
      (repo.language && repo.language.toLowerCase().includes(q)) ||
      (repo.description && repo.description.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadRepositories} title="Repositories" subtitle="Registered Code Repositories &amp; Workspaces" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Import Any Repository Quick Action with Motion */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl bg-surface-elevated/50 border border-border-subtle shadow-sm space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                Connect & Ingest Any GitHub Repository
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Live Ingestion
            </span>
          </div>

          <form onSubmit={handleImportRepository} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Paste any GitHub repository link (e.g. https://github.com/owner/repo or owner/repo)"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              className="flex-1 px-3.5 py-2.5 text-xs font-mono rounded-xl bg-surface border border-border-subtle focus:outline-none focus:border-emerald-400 text-text-primary placeholder:text-text-muted"
            />
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={importing || !importUrl.trim()}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs font-mono flex items-center justify-center gap-2 disabled:opacity-50 transition-colors shadow-sm"
            >
              {importing ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <>
                  <Plus className="w-3.5 h-3.5" />
                  <span>Import &amp; Sync Issues</span>
                </>
              )}
            </motion.button>
          </form>

          {importSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{importSuccess}</span>
            </motion.div>
          )}

          {deleteSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-300 flex items-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 text-cyan-400" />
              <span>{deleteSuccess}</span>
            </motion.div>
          )}
        </motion.div>

        {/* Connected GitHub Account Repositories Explorer */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-2xl bg-surface-elevated/40 border border-border-subtle shadow-md space-y-4"
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-border-subtle/60">
            <div className="flex items-start sm:items-center gap-3">
              <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 shrink-0">
                <Github className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-sm font-mono font-bold text-text-primary uppercase tracking-wider">
                    GitHub Account Repositories
                  </h2>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30 font-semibold">
                    @{activeAccountUsername}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    {accountRepos.length} Repositories Found
                  </span>
                  <button
                    type="button"
                    onClick={() => window.dispatchEvent(new Event("devsquad_open_github_modal"))}
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full border flex items-center gap-1 transition-all ${
                      accountPermissions?.can_write_issues
                        ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25"
                        : "bg-amber-500/15 text-amber-300 border-amber-500/30 hover:bg-amber-500/25"
                    }`}
                    title="Click to configure GitHub PAT & issue solving permissions"
                  >
                    {accountPermissions?.can_write_issues ? (
                      <>
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        <span>Issue-Solving Authorized</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                        <span>Grant Solve Permissions</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="text-[11px] font-mono text-text-muted mt-0.5">
                  All repositories from your linked GitHub account. Import any repo to DevSquad with 1 click to sync issues and trigger multi-agent fixes.
                </p>
              </div>
            </div>

            {/* Quick Account Switcher & Search Bar */}
            <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
              <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-xl border border-border-subtle">
                <span className="text-[10px] font-mono text-text-muted">@</span>
                <input
                  type="text"
                  placeholder="github username"
                  value={usernameInputQuery}
                  onChange={(e) => setUsernameInputQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      loadAccountRepositories(usernameInputQuery.trim());
                    }
                  }}
                  className="w-28 text-xs font-mono bg-transparent focus:outline-none text-text-primary placeholder:text-text-muted"
                />
                <button
                  type="button"
                  onClick={() => loadAccountRepositories(usernameInputQuery.trim())}
                  disabled={accountReposLoading || !usernameInputQuery.trim()}
                  className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 transition-colors disabled:opacity-50"
                >
                  Load
                </button>
              </div>

              <div className="relative min-w-[180px]">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder="Filter repos..."
                  value={accountFilter}
                  onChange={(e) => setAccountFilter(e.target.value)}
                  className="w-full pl-8 pr-2.5 py-1.5 text-xs font-mono rounded-xl bg-surface border border-border-subtle focus:outline-none focus:border-purple-400 text-text-primary placeholder:text-text-muted"
                />
              </div>

              <button
                type="button"
                onClick={() => loadAccountRepositories(activeAccountUsername)}
                disabled={accountReposLoading}
                className="p-2 rounded-xl bg-surface border border-border-subtle hover:border-purple-500/40 text-text-muted hover:text-purple-300 transition-colors disabled:opacity-50 shrink-0"
                title="Refresh account repositories"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${accountReposLoading ? "animate-spin text-purple-400" : ""}`} />
              </button>
            </div>
          </div>

          {/* Account Repositories Grid */}
          {accountReposLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="h-32 bg-surface/60 rounded-xl border border-border-subtle animate-pulse p-4" />
              ))}
            </div>
          ) : accountReposError ? (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-300 flex items-center justify-between">
              <span>{accountReposError}</span>
              <button
                type="button"
                onClick={() => loadAccountRepositories(activeAccountUsername)}
                className="px-3 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : filteredAccountRepos.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-text-muted bg-surface/30 border border-border-subtle rounded-xl space-y-1">
              <p className="text-text-secondary font-medium">
                {accountFilter ? `No repositories matching "${accountFilter}"` : `No public repositories found for @${activeAccountUsername}`}
              </p>
              <p className="text-[11px] text-text-muted">
                Ensure the username is correct or connect your GitHub Personal Access Token via the top bar.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 max-h-[460px] overflow-y-auto pr-1">
              {(filteredAccountRepos || []).map((repo) => {
                if (!repo) return null;
                const repoFullName = repo.full_name || repo.name || "";
                const isImported = (repositories || []).some(
                  (r) => r?.full_name && repoFullName && r.full_name.toLowerCase() === repoFullName.toLowerCase()
                );
                const matchedWorkspaceRepo = (repositories || []).find(
                  (r) => r?.full_name && repoFullName && r.full_name.toLowerCase() === repoFullName.toLowerCase()
                );
                const isCurrentImporting = importingRepoName === repoFullName;

                return (
                  <motion.div
                    key={repo.id || repoFullName}
                    whileHover={{ y: -2 }}
                    className={`p-4 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
                      isImported
                        ? "bg-surface-elevated/70 border-emerald-500/30 shadow-sm ring-1 ring-emerald-500/20"
                        : "bg-surface/60 border-border-subtle hover:border-border-strong hover:bg-surface-elevated/40"
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <span className="font-semibold text-xs text-text-primary font-mono truncate" title={repoFullName}>
                          {repo.name || repoFullName}
                        </span>
                        <a
                          href={repo.html_url || (repoFullName ? `https://github.com/${repoFullName}` : "#")}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 rounded text-text-muted hover:text-purple-400 transition-colors shrink-0"
                          title="Open on GitHub"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>

                      <p className="text-[11px] text-text-muted line-clamp-2 min-h-[32px] leading-relaxed">
                        {repo.description || `Public repository under @${activeAccountUsername}`}
                      </p>
                    </div>

                    <div className="space-y-2.5 pt-2 border-t border-border-subtle/50">
                      <div className="flex items-center justify-between text-[10px] font-mono text-text-muted">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-purple-400" />
                          {repo.default_branch || "main"}
                        </span>
                        {repo.language && (
                          <span className="px-1.5 py-0.5 rounded bg-surface border border-border-subtle text-text-secondary">
                            {repo.language}
                          </span>
                        )}
                        {typeof repo.open_issues_count === "number" && (
                          <span className={`px-1.5 py-0.5 rounded ${repo.open_issues_count > 0 ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" : "text-text-muted"}`}>
                            {repo.open_issues_count} issues
                          </span>
                        )}
                      </div>

                      {isImported ? (
                        <div className="flex items-center justify-between gap-2 pt-1">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-semibold px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                            <Check className="w-3 h-3 text-emerald-400" />
                            In Workspace
                          </span>
                          {matchedWorkspaceRepo && (
                            <button
                              type="button"
                              onClick={() => selectRepo(matchedWorkspaceRepo)}
                              className="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-surface border border-border-subtle hover:border-emerald-500 text-text-secondary hover:text-emerald-400 transition-colors flex items-center gap-1"
                            >
                              <span>Inspect</span>
                              <ArrowUpRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      ) : (
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          type="button"
                          disabled={isCurrentImporting}
                          onClick={() => handleImportAccountRepo(repo.full_name)}
                          className="w-full py-1.5 px-3 rounded-lg bg-gradient-to-r from-purple-500/20 to-cyan-500/20 hover:from-purple-500/30 hover:to-cyan-500/30 border border-purple-500/30 hover:border-purple-400 text-text-primary text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                        >
                          {isCurrentImporting ? (
                            <>
                              <RefreshCw className="w-3 h-3 animate-spin text-purple-400" />
                              <span>Importing &amp; Syncing...</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3 h-3 text-purple-400" />
                              <span>Import to Workspace</span>
                            </>
                          )}
                        </motion.button>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </motion.div>

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
                No repositories registered in platform. Import any repo above!
              </div>
            ) : (
              <div className="space-y-2">
                {repositories.map((repo) => {
                  const isSelected = selectedRepo?.id === repo.id;
                  return (
                    <motion.div
                      key={repo.id}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => selectRepo(repo)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all relative ${
                        isSelected
                          ? "bg-surface-elevated border-emerald-500/50 shadow-md ring-1 ring-emerald-500/30"
                          : "bg-surface border-border-subtle hover:border-border-strong hover:bg-surface-elevated/50"
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-emerald-400" />
                      )}
                      <div className="flex items-center justify-between mb-1.5 pl-1">
                        <span className="font-semibold text-xs text-text-primary font-mono truncate">
                          {repo.full_name || "Unknown"}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-medium border ${
                            repo.full_name?.startsWith("devsquad/")
                              ? "bg-cyan-ice/10 text-cyan-ice border-cyan-ice/20"
                              : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          }`}>
                            {repo.full_name?.startsWith("devsquad/") ? "LOCAL DB" : "LIVE GITHUB"}
                          </span>
                          <StatusBadge
                            status={repo.is_active ? "ACTIVE" : "INACTIVE"}
                            size="sm"
                          />
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setRepoPendingDelete(repo);
                            }}
                            className="p-1 rounded text-text-muted hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-0.5"
                            title={`Remove ${repo.full_name || "repository"}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-text-muted font-mono pl-1">
                        <span className="flex items-center gap-1">
                          <GitBranch className="w-3 h-3 text-emerald-400" />
                          {repo.default_branch}
                        </span>
                        <span>ID: {repo.github_repository_id}</span>
                      </div>
                    </motion.div>
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
                        selectedRepo.full_name?.startsWith("devsquad/")
                          ? "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30"
                          : "bg-forge-lime/15 text-forge-lime border-forge-lime/30"
                      }`}>
                        {selectedRepo.full_name?.startsWith("devsquad/") ? "LOCAL DATABASE FIXTURE" : "LIVE GITHUB REPOSITORY"}
                      </span>
                      <StatusBadge status={selectedRepo.is_active ? "ACTIVE" : "INACTIVE"} />
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        onClick={() => setRepoPendingDelete(selectedRepo)}
                        className="px-2.5 py-1 text-[11px] font-mono rounded-lg border border-rose-500/30 text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 flex items-center gap-1.5 transition-colors shadow-sm ml-1"
                        title="Remove this repository and scoped data"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Remove</span>
                      </motion.button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs font-mono">
                    <div className="bg-surface-elevated p-2.5 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Provenance:</span>
                      <span className="text-cyan-ice font-bold">
                        {selectedRepo.full_name?.startsWith("devsquad/") ? "SQLite Persisted" : "GitHub Remote"}
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

        {/* Remove Repository Confirmation Modal with Motion */}
        <AnimatePresence>
          {repoPendingDelete && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => !isDeleting && setRepoPendingDelete(null)}
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
              />

              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                className="relative w-full max-w-md rounded-2xl bg-surface border border-rose-500/30 p-6 shadow-2xl shadow-rose-950/40 space-y-4"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold font-mono text-text-primary uppercase tracking-wider">
                      Remove Repository
                    </h3>
                    <p className="text-xs text-text-muted font-mono">
                      This action is immediate and cleans up scoped data.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-surface-elevated border border-border-subtle space-y-1.5 text-xs font-mono">
                  <div className="text-text-secondary">
                    Target: <strong className="text-white">{repoPendingDelete?.full_name}</strong>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Removing this repository will detach it from DevSquad and delete its ingested issues and historical runs.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={() => setRepoPendingDelete(null)}
                    className="px-4 py-2 text-xs font-mono rounded-xl border border-border-subtle bg-surface-elevated text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={confirmDeleteRepository}
                    className="px-4 py-2 text-xs font-mono font-bold rounded-xl border border-rose-500/40 bg-rose-500 hover:bg-rose-400 text-black flex items-center gap-2 transition-all shadow-md shadow-rose-500/20 disabled:opacity-50"
                  >
                    {isDeleting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Removing...</span>
                      </>
                    ) : (
                      <>
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Yes, Remove Repository</span>
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
