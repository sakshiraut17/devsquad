"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  RefreshCw,
  Server,
  UserCheck,
  ShieldAlert,
  Play,
  Cpu,
  LogOut,
  Github,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { getSessionUser, clearSession } from "@/lib/auth/session";
import {
  getStoredGitHubProfile,
  getStoredGitHubUsername,
} from "@/lib/auth/githubSession";
import { GitHubAccountModal } from "@/components/github/GitHubAccountModal";
import { GitHubAccountIssue, GitHubUserProfile, Run, User } from "@/types";

interface NavbarProps {
  onRefresh?: () => void;
  title?: string;
  subtitle?: string;
  onSelectIssueForSolve?: (issue: GitHubAccountIssue) => void;
}

export function Navbar({ onRefresh, title, subtitle, onSelectIssueForSolve }: NavbarProps) {
  const router = useRouter();
  const [backendStatus, setBackendStatus] = useState<"operational" | "degraded" | "connecting" | "disconnected">("connecting");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isGitHubModalOpen, setIsGitHubModalOpen] = useState(false);
  const [githubProfile, setGithubProfile] = useState<GitHubUserProfile | null>(null);
  const [githubUsername, setGithubUsername] = useState<string | null>(null);

  function syncGitHubSession() {
    setGithubProfile(getStoredGitHubProfile());
    setGithubUsername(getStoredGitHubUsername());
  }

  async function checkHealthAndStatus() {
    try {
      const health = await api.getHealth();
      if (health?.status === "operational" || health?.status === "healthy") {
        setBackendStatus("operational");
      } else if (health?.status === "degraded") {
        setBackendStatus("degraded");
      } else {
        setBackendStatus("disconnected");
      }
    } catch {
      setBackendStatus("disconnected");
    }

    try {
      const runs = await api.getRuns(undefined, undefined, 0, 5);
      const active = runs.find(
        (r) =>
          r.status === "INGESTING" ||
          r.status === "PLANNING" ||
          r.status === "CODING" ||
          r.status === "TESTING" ||
          r.status === "REVIEWING" ||
          r.status === "AWAITING_APPROVAL"
      );
      setActiveRun(active || null);
    } catch {
      setActiveRun(null);
    }
  }

  async function ensureAuth() {
    const cached = getSessionUser();
    if (cached) {
      setCurrentUser(cached);
      return;
    }
  }

  const handleLogout = () => {
    clearSession();
    setCurrentUser(null);
    router.push("/login");
  };

  useEffect(() => {
    checkHealthAndStatus();
    ensureAuth();
    syncGitHubSession();

    const handleStorageChange = () => syncGitHubSession();
    const handleOpenModal = () => setIsGitHubModalOpen(true);
    window.addEventListener("devsquad_github_session_change", handleStorageChange);
    window.addEventListener("devsquad_open_github_modal", handleOpenModal);
    return () => {
      window.removeEventListener("devsquad_github_session_change", handleStorageChange);
      window.removeEventListener("devsquad_open_github_modal", handleOpenModal);
    };
  }, []);

  const handleRefreshClick = async () => {
    setIsRefreshing(true);
    await checkHealthAndStatus();
    syncGitHubSession();
    if (onRefresh) onRefresh();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <>
      <header className="h-16 border-b border-border-subtle bg-surface/85 backdrop-blur-xl px-6 flex items-center justify-between sticky top-0 z-20">
        {/* Title & View Context */}
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-sm sm:text-base font-bold text-text-primary tracking-tight font-sans">
              {title || "Command Center"}
            </h1>
            {subtitle && (
              <p className="text-xs text-text-muted font-sans">{subtitle}</p>
            )}
          </div>
          <span className="hidden sm:inline-flex items-center gap-1.5 text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            v0.2.0
          </span>
        </div>

        {/* Control Room Top Indicators */}
        <div className="flex items-center gap-3">
          {/* Real Backend Status Indicator with Tooltip */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-elevated/80 border border-border-subtle text-xs font-sans group relative cursor-help"
            title={
              backendStatus === "operational"
                ? "FastAPI backend & Docker sandbox are fully operational."
                : backendStatus === "degraded"
                ? "FastAPI active. Docker sandbox unavailable; using AST static sandbox fallback."
                : "Backend is disconnected or starting up."
            }
          >
            <Server className="w-3.5 h-3.5 text-text-muted" />
            {backendStatus === "operational" && (
              <span className="flex items-center gap-1.5 font-medium text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                <span className="hidden md:inline">API Online</span>
              </span>
            )}
            {backendStatus === "degraded" && (
              <span className="flex items-center gap-1.5 font-medium text-amber-400">
                <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)] animate-pulse" />
                <span className="hidden md:inline">AST Fallback</span>
              </span>
            )}
            {backendStatus === "connecting" && (
              <span className="flex items-center gap-1.5 text-text-muted">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                <span className="hidden md:inline">Connecting</span>
              </span>
            )}
            {backendStatus === "disconnected" && (
              <span className="flex items-center gap-1.5 font-medium text-rose-400">
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                <span className="hidden md:inline">Offline</span>
              </span>
            )}
          </div>

          {/* GitHub Account Connect Button with Motion */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setIsGitHubModalOpen(true)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-sans transition-all ${
              githubProfile
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-sm"
                : "bg-surface-elevated/80 border-border-subtle text-text-secondary hover:text-text-primary hover:border-cyan-400/40"
            }`}
          >
            {githubProfile ? (
              <>
                <img
                  src={githubProfile.avatar_url}
                  alt={githubProfile.login}
                  className="w-4 h-4 rounded-full border border-emerald-400/80"
                />
                <span className="font-medium font-mono truncate max-w-[90px]">@{githubProfile.login}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              </>
            ) : (
              <>
                <Github className="w-3.5 h-3.5 text-cyan-400" />
                <span className="hidden sm:inline font-medium">Connect GitHub</span>
              </>
            )}
          </motion.button>

          {/* Current Active Workflow (if present) */}
          {activeRun && (
            <Link
              href={`/runs/${activeRun.id}`}
              className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-elevated/80 border border-border-subtle text-xs font-mono text-text-primary hover:border-cyan-400/50 transition-colors"
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-text-muted">Workflow:</span>
              <span className="text-cyan-400 font-bold">{activeRun.id.slice(0, 8)}…</span>
            </Link>
          )}

          {/* Authenticated Maintainer Session */}
          <div className="flex items-center gap-2">
            {currentUser ? (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-elevated/80 border border-border-subtle text-xs font-sans">
                  <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-cyan-400 to-emerald-400 flex items-center justify-center text-[10px] font-bold text-black font-mono">
                    {(currentUser.display_name || currentUser.email || "U")[0].toUpperCase()}
                  </div>
                  <div className="flex flex-col text-left">
                    <span className="text-text-primary font-semibold text-xs leading-none truncate max-w-[110px]" title={currentUser.email}>
                      {currentUser.display_name?.split(" ")[0] || "Maintainer"}
                    </span>
                    <span className="text-[10px] text-text-muted font-mono leading-none mt-0.5">
                      Lead
                    </span>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-xl bg-surface-elevated/80 border border-border-subtle text-text-muted hover:text-rose-400 hover:border-rose-400/40 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 text-black font-bold text-xs font-sans hover:from-cyan-300 hover:to-emerald-300 transition-all shadow-md shadow-cyan-500/20"
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </div>

          {/* Refresh Action */}
          <button
            onClick={handleRefreshClick}
            disabled={isRefreshing}
            className="p-2 rounded-xl bg-surface-elevated/80 border border-border-subtle text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-50"
            title="Refresh Data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </header>

      {/* GitHub Account Realtime Modal */}
      <GitHubAccountModal
        isOpen={isGitHubModalOpen}
        onClose={() => setIsGitHubModalOpen(false)}
        onSelectIssueForSolve={onSelectIssueForSolve}
      />
    </>
  );
}

