"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Github,
  KeyRound,
  User,
  CheckCircle2,
  AlertCircle,
  X,
  ExternalLink,
  Zap,
  FolderGit2,
  RefreshCw,
  Sparkles,
  BookOpen,
} from "lucide-react";
import { api } from "@/lib/api/client";
import {
  getStoredGitHubProfile,
  getStoredGitHubToken,
  getStoredGitHubUsername,
  getStoredGitHubPermissions,
  setStoredGitHubSession,
  clearStoredGitHubSession,
} from "@/lib/auth/githubSession";
import { GitHubAccountIssue, GitHubUserProfile, GitHubTokenPermissions } from "@/types";

interface GitHubAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectIssueForSolve?: (issue: GitHubAccountIssue) => void;
}

export function GitHubAccountModal({
  isOpen,
  onClose,
  onSelectIssueForSolve,
}: GitHubAccountModalProps) {
  const [tokenInput, setTokenInput] = useState("");
  const [usernameInput, setUsernameInput] = useState("");
  const [profile, setProfile] = useState<GitHubUserProfile | null>(null);
  const [permissions, setPermissions] = useState<GitHubTokenPermissions | null>(null);
  const [issues, setIssues] = useState<GitHubAccountIssue[]>([]);
  const [issuesSearch, setIssuesSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [issuesLoading, setIssuesLoading] = useState(false);
  const [importingRepo, setImportingRepo] = useState<string | null>(null);
  const [solvingIssueKey, setSolvingIssueKey] = useState<string | null>(null);
  const [publishedCommentUrl, setPublishedCommentUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const storedToken = getStoredGitHubToken();
      const storedUsername = getStoredGitHubUsername();
      const storedProfile = getStoredGitHubProfile();
      const storedPerms = getStoredGitHubPermissions();

      if (storedToken) setTokenInput(storedToken);
      if (storedUsername) setUsernameInput(storedUsername);
      if (storedPerms) setPermissions(storedPerms);
      if (storedProfile) {
        setProfile(storedProfile);
        loadIssues(storedUsername || undefined, storedToken || undefined);
      }

      if (storedToken) {
        api.getTokenPermissions(storedToken).then((perms) => {
          setPermissions(perms);
        }).catch(() => {});
      }
    }
  }, [isOpen]);

  async function handleConnect(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!tokenInput.trim() && !usernameInput.trim()) {
      setError("Please provide either a GitHub Personal Access Token or a GitHub username.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await api.connectGitHub(
        tokenInput.trim() || undefined,
        usernameInput.trim() || undefined
      );

      setProfile(res.profile);
      setPermissions(res.permissions || null);
      setStoredGitHubSession(
        tokenInput.trim() || null,
        usernameInput.trim() || res.profile.login,
        res.profile,
        res.permissions || null
      );
      
      const permText = res.permissions?.can_write_issues
        ? "✅ Full Issue Solving & Commenting Authorized!"
        : "Connected with Read-Only Access. (Add a PAT with 'repo' scope to publish solutions directly on GitHub).";
      setSuccessMsg(`Connected as @${res.profile.login}! ${permText}`);
      await loadIssues(usernameInput.trim() || res.profile.login, tokenInput.trim() || undefined);
    } catch (err: any) {
      setError(err?.message || "Failed to authenticate with GitHub.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSolveAndPublishToGitHub(issue: GitHubAccountIssue) {
    const key = `${issue.repository_name}#${issue.number}`;
    setSolvingIssueKey(key);
    setError(null);
    setSuccessMsg(null);
    setPublishedCommentUrl(null);

    let token = tokenInput.trim() || getStoredGitHubToken() || undefined;
    if (!token) {
      const promptToken = window.prompt(
        "To solve and post solutions to GitHub, please enter your GitHub Personal Access Token (with 'repo' scope):"
      );
      if (!promptToken || !promptToken.trim()) {
        setError("A GitHub Personal Access Token with 'repo' scope is required to publish solutions.");
        setSolvingIssueKey(null);
        return;
      }
      token = promptToken.trim();
      setTokenInput(token);
      localStorage.setItem("devsquad_github_token", token);
      window.dispatchEvent(new Event("devsquad_github_session_change"));
    }

    try {
      // 1. Instant AI Diagnosis & Patch Generation
      const solution = await api.quickSolve(
        issue.repository_name,
        issue.body || undefined,
        issue.number,
        token
      );

      // 2. Publish Solution to the GitHub Issue thread
      const pubRes = await api.publishSolution({
        target: issue.repository_name,
        issue_number: issue.number,
        diagnosis: solution.problem_diagnosis,
        root_cause: solution.root_cause,
        code_patch: solution.code_patch,
        verification_steps: solution.verification_steps,
        add_solved_label: true,
        close_issue: false,
        token,
      });

      setPublishedCommentUrl(pubRes.comment_url);
      setSuccessMsg(`🎉 Solution successfully diagnosed and posted to GitHub issue #${issue.number}!`);
    } catch (err: any) {
      setError(err?.message || `Failed to solve and publish to issue #${issue.number}`);
    } finally {
      setSolvingIssueKey(null);
    }
  }

  async function loadIssues(username?: string, token?: string) {
    setIssuesLoading(true);
    try {
      const list = await api.getUserIssues(username, token, "open", 1, 20);
      setIssues(list);
    } catch (err) {
      console.warn("Failed to load user issues:", err);
    } finally {
      setIssuesLoading(false);
    }
  }

  async function handleImport(repoName: string) {
    setImportingRepo(repoName);
    setError(null);
    try {
      const res = await api.importRepository(repoName, true, tokenInput.trim() || undefined);
      const name = res?.repository?.full_name || repoName;
      setSuccessMsg(`Repository ${name} imported with ${res?.synced_issues_count ?? 0} open issues!`);
    } catch (err: any) {
      setError(err?.message || "Import failed");
    } finally {
      setImportingRepo(null);
    }
  }

  function handleDisconnect() {
    clearStoredGitHubSession();
    setProfile(null);
    setPermissions(null);
    setIssues([]);
    setTokenInput("");
    setUsernameInput("");
    setPublishedCommentUrl(null);
    setSuccessMsg("Disconnected GitHub account.");
  }

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="bg-surface border border-border-subtle rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle bg-surface-elevated">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Github className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-text-primary flex items-center gap-2">
                  GitHub Account Integration
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Realtime Sync
                  </span>
                </h2>
                <p className="text-xs text-text-muted">
                  Connect your account to discover personal issues and solve them in real-time.
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary p-1 rounded-md hover:bg-surface transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Alerts */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2.5 text-xs text-red-400"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </motion.div>
            )}

            {successMsg && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-2.5 text-xs text-emerald-400"
              >
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{successMsg}</span>
              </motion.div>
            )}

            {/* Profile Card if Connected */}
            {profile ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-xl bg-surface-elevated border border-emerald-500/30 relative overflow-hidden space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <img
                      src={profile.avatar_url}
                      alt={profile.login}
                      className="w-14 h-14 rounded-full border-2 border-emerald-400 shadow-md"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-text-primary">
                          {profile.name || profile.login}
                        </h3>
                        <span className="text-xs text-text-muted font-mono">@{profile.login}</span>
                      </div>
                      {profile.bio && (
                        <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{profile.bio}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-[11px] text-text-muted font-mono">
                        <span>
                          <strong className="text-text-primary">{profile.public_repos}</strong> public repos
                        </span>
                        <span>•</span>
                        <span>
                          <strong className="text-text-primary">{profile.followers}</strong> followers
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => loadIssues(usernameInput || profile.login, tokenInput || undefined)}
                      disabled={issuesLoading}
                      className="px-3 py-1.5 text-xs rounded-md bg-surface border border-border-subtle hover:border-emerald-500/40 text-text-primary flex items-center gap-1.5 transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${issuesLoading ? "animate-spin" : ""}`} />
                      Refresh Issues
                    </button>
                    <button
                      onClick={handleDisconnect}
                      className="px-3 py-1.5 text-xs rounded-md text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-colors"
                    >
                      Disconnect
                    </button>
                  </div>
                </div>

                {/* Token Permissions Status Strip */}
                <div className="pt-2.5 border-t border-border-subtle/60 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono">
                  <div className="flex items-center gap-2">
                    <span className="text-text-muted">Issue Solving Permission:</span>
                    {permissions?.can_write_issues ? (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-semibold">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        Write &amp; Solve Authorized
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 text-amber-400" />
                        Read-Only Mode (Add token with repo scope to solve)
                      </span>
                    )}
                  </div>
                  {permissions?.rate_limit_remaining !== undefined && (
                    <span className="text-text-muted text-[10px]">
                      Rate Limit: {permissions.rate_limit_remaining} / {permissions.rate_limit_limit} req/hr
                    </span>
                  )}
                </div>
              </motion.div>
            ) : (
              /* Connect Form */
              <form onSubmit={handleConnect} className="space-y-4">
                <div className="p-4 rounded-xl bg-surface-elevated border border-border-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-semibold text-text-primary">
                      <KeyRound className="w-4 h-4 text-emerald-400" />
                      <span>Connect GitHub Account &amp; Grant Issue-Solving Permission</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                      repo scope
                    </span>
                  </div>
                  <p className="text-[11px] text-text-muted leading-relaxed">
                    Provide a GitHub Personal Access Token (PAT) with <code className="text-emerald-400 font-bold">repo</code> scope so DevSquad has authorization to diagnose, write code patches, and post verified solutions directly to your issues on GitHub.
                  </p>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <label className="font-mono text-text-secondary">
                        GitHub Personal Access Token:
                      </label>
                      <a
                        href="https://github.com/settings/tokens/new?scopes=repo,read:user,write:discussion&description=DevSquad%20AI%20Issue%20Solver"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono transition-colors text-[10px]"
                      >
                        <span>Generate token on GitHub with repo permissions</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <input
                      type="password"
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      value={tokenInput}
                      onChange={(e) => setTokenInput(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-surface border border-border-subtle focus:outline-none focus:border-emerald-500 text-text-primary font-mono placeholder:text-text-muted"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[11px] font-mono text-text-muted">
                      Or Connect Read-Only via GitHub Username:
                    </label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <User className="w-3.5 h-3.5 text-text-muted absolute left-3 top-2.5" />
                        <input
                          type="text"
                          placeholder="e.g. ayushkale06"
                          value={usernameInput}
                          onChange={(e) => setUsernameInput(e.target.value)}
                          className="w-full pl-8 pr-3 py-2 text-xs rounded-lg bg-surface border border-border-subtle focus:outline-none focus:border-emerald-500 text-text-primary font-mono"
                        />
                      </div>
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={loading}
                        className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black flex items-center gap-2 disabled:opacity-50 transition-colors shadow-md"
                      >
                        {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                        Connect
                      </motion.button>
                    </div>
                  </div>
                </div>
              </form>
            )}

            {publishedCommentUrl && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-xl flex items-center justify-between text-xs text-cyan-300"
              >
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                  Solution comment successfully published to GitHub!
                </span>
                <a
                  href={publishedCommentUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-mono text-[11px] flex items-center gap-1 transition-colors"
                >
                  <span>View Comment on GitHub</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </motion.div>
            )}

            {/* Account Issues List */}
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <h4 className="text-xs font-semibold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                  Your Recognized Account Issues ({issues.length})
                </h4>
                {issuesLoading && (
                  <span className="text-[11px] text-text-muted flex items-center gap-1 font-mono">
                    <RefreshCw className="w-3 h-3 animate-spin text-emerald-400" /> Fetching live issues...
                  </span>
                )}
              </div>

              {issues.length > 0 && (
                <div className="mb-3">
                  <input
                    type="text"
                    placeholder="Filter recognized issues by title or repository..."
                    value={issuesSearch}
                    onChange={(e) => setIssuesSearch(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-xl bg-surface border border-border-subtle focus:outline-none focus:border-emerald-400 text-text-primary font-mono placeholder:text-text-muted/60"
                  />
                </div>
              )}

              {issues.length === 0 && !issuesLoading ? (
                <div className="p-8 text-center rounded-xl bg-surface-elevated/50 border border-dashed border-border-subtle text-text-muted text-xs">
                  {profile
                    ? "No open issues found on your recent active repositories. Create an issue on GitHub or inspect any external repo!"
                    : "Connect your GitHub account above to load your active issues in real-time."}
                </div>
              ) : (
                <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                  {issues
                    .filter(
                      (i) =>
                        !issuesSearch.trim() ||
                        i.title.toLowerCase().includes(issuesSearch.toLowerCase()) ||
                        i.repository_name.toLowerCase().includes(issuesSearch.toLowerCase())
                    )
                    .map((issue) => (
                    <motion.div
                      key={`${issue.repository_name}-${issue.number}`}
                      whileHover={{ scale: 1.01, borderColor: "rgba(52, 211, 153, 0.4)" }}
                      className="p-3 rounded-xl bg-surface-elevated border border-border-subtle hover:bg-surface transition-all flex items-start justify-between gap-3 shadow-sm"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            {issue.repository_name} #{issue.number}
                          </span>
                          {issue.labels.slice(0, 2).map((lbl) => (
                            <span
                              key={lbl}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-surface border border-border-subtle text-text-muted"
                            >
                              {lbl}
                            </span>
                          ))}
                        </div>
                        <h5 className="text-xs font-medium text-text-primary truncate">
                          {issue.title}
                        </h5>
                        {issue.body && (
                          <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">
                            {issue.body}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <motion.button
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          disabled={solvingIssueKey === `${issue.repository_name}#${issue.number}`}
                          onClick={() => handleSolveAndPublishToGitHub(issue)}
                          className="px-2.5 py-1 text-[11px] font-mono font-bold rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-400 hover:from-emerald-400 hover:to-cyan-300 text-black flex items-center gap-1 shadow-sm transition-all disabled:opacity-50"
                          title="Generate diagnosis & code patch and publish the solution directly as a GitHub issue comment"
                        >
                          {solvingIssueKey === `${issue.repository_name}#${issue.number}` ? (
                            <>
                              <RefreshCw className="w-3 h-3 animate-spin text-black" />
                              <span>Solving &amp; Posting...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3 h-3 text-black" />
                              <span>Solve &amp; Post to GitHub</span>
                            </>
                          )}
                        </motion.button>

                        {onSelectIssueForSolve && (
                          <motion.button
                            whileHover={{ scale: 1.04 }}
                            whileTap={{ scale: 0.96 }}
                            onClick={() => {
                              onSelectIssueForSolve(issue);
                              onClose();
                            }}
                            className="px-2.5 py-1 text-[11px] font-medium rounded-lg bg-surface border border-border-subtle hover:border-emerald-400 text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors"
                          >
                            <Zap className="w-3 h-3 text-emerald-400" />
                            Inspect
                          </motion.button>
                        )}
                        <button
                          onClick={() => handleImport(issue.repository_name)}
                          disabled={importingRepo === issue.repository_name}
                          title="Import repository to DevSquad"
                          className="p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-surface border border-border-subtle transition-colors"
                        >
                          {importingRepo === issue.repository_name ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                          ) : (
                            <FolderGit2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <a
                          href={issue.html_url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-surface border border-border-subtle transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-border-subtle bg-surface-elevated flex items-center justify-between text-xs text-text-muted">
            <span>DevSquad Realtime Sync</span>
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg bg-surface border border-border-subtle hover:border-text-muted text-text-primary font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
