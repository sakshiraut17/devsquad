"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RefreshCw, Server, UserCheck, ShieldAlert, Play, Cpu, LogOut } from "lucide-react";
import { api } from "@/lib/api/client";
import { getSessionUser, clearSession } from "@/lib/auth/session";
import { Run, User } from "@/types";

interface NavbarProps {
  onRefresh?: () => void;
  title?: string;
  subtitle?: string;
}

export function Navbar({ onRefresh, title, subtitle }: NavbarProps) {
  const router = useRouter();
  const [backendStatus, setBackendStatus] = useState<"operational" | "degraded" | "connecting" | "disconnected">("connecting");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

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
    // Check if on protected route without session
    // If not on login, user can remain as guest or redirect
  }

  const handleLogout = () => {
    clearSession();
    setCurrentUser(null);
    router.push("/login");
  };

  useEffect(() => {
    checkHealthAndStatus();
    ensureAuth();
  }, []);

  const handleRefreshClick = async () => {
    setIsRefreshing(true);
    await checkHealthAndStatus();
    if (onRefresh) onRefresh();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  return (
    <header className="h-16 border-b border-border-subtle bg-surface px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Title & View Context */}
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-sm font-semibold text-text-primary tracking-tight font-mono">
            {title || "Command Center"}
          </h1>
          {subtitle && (
            <p className="text-[11px] text-text-muted font-mono">{subtitle}</p>
          )}
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-surface-elevated text-text-muted border border-border-subtle font-mono">
          env: development
        </span>
      </div>

      {/* Control Room Top Indicators */}
      <div className="flex items-center gap-3">
        {/* Current Active Workflow (if present) */}
        {activeRun && (
          <Link
            href={`/runs/${activeRun.id}`}
            className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-xs font-mono text-text-primary hover:border-forge-lime/50 transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-forge-lime animate-pulse" />
            <span className="text-text-muted">Workflow:</span>
            <span className="text-forge-lime font-bold">{activeRun.id.slice(0, 8)}…</span>
            <span className="text-[10px] uppercase text-text-secondary">({activeRun.status})</span>
          </Link>
        )}

        {/* Real Backend Status */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-xs font-mono">
          <Server className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-text-muted">FastAPI:</span>
          {backendStatus === "operational" && (
            <span className="text-forge-lime flex items-center gap-1.5 font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-forge-lime animate-pulse" />
              ONLINE (8000)
            </span>
          )}
          {backendStatus === "degraded" && (
            <span className="text-amber-attention flex items-center gap-1 font-semibold" title="Docker sandbox unavailable, AST fallback active">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-attention animate-pulse" />
              DEGRADED (8000)
            </span>
          )}
          {backendStatus === "connecting" && (
            <span className="text-amber-attention">CHECKING...</span>
          )}
          {backendStatus === "disconnected" && (
            <span className="text-semantic-danger flex items-center gap-1 font-semibold">
              <ShieldAlert className="w-3.5 h-3.5" />
              OFFLINE
            </span>
          )}
        </div>

        {/* Authenticated Maintainer Session */}
        <div className="flex items-center gap-2">
          {currentUser ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-xs font-mono">
                <UserCheck className="w-3.5 h-3.5 text-ultraviolet shrink-0" />
                <span className="text-text-primary font-medium truncate max-w-[100px] sm:max-w-[140px] md:max-w-[180px]" title={currentUser.email}>
                  {currentUser.display_name || currentUser.email}
                </span>
                <span className="hidden sm:inline-block text-[10px] px-1 rounded bg-surface border border-border-subtle text-forge-lime uppercase">
                  Maintainer
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded bg-surface-elevated border border-border-subtle text-text-muted hover:text-semantic-danger hover:border-semantic-danger/40 transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-forge-lime text-[#0B0D0F] font-bold text-xs font-mono hover:bg-[#c2ef4c] transition-colors shadow-[0_0_10px_rgba(215,255,100,0.2)]"
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
          className="p-2 rounded bg-surface-elevated border border-border-subtle text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-50"
          title="Refresh Data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-forge-lime" : ""}`} />
        </button>
      </div>
    </header>
  );
}
