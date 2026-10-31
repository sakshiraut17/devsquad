"use client";

import React, { useEffect, useState } from "react";
import { Settings, ShieldCheck, User, Server, Cpu, Database, Box } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { getSessionUser } from "@/lib/auth/session";
import { api } from "@/lib/api/client";
import { User as UserType, HealthResponse } from "@/types";

export default function SettingsPage() {
  const [user, setUser] = useState<UserType | null>(null);
  const [apiBaseUrl, setApiBaseUrl] = useState("http://127.0.0.1:8000");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  const fetchHealth = () => {
    setHealthLoading(true);
    api
      .getHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false));
  };

  useEffect(() => {
    const u = getSessionUser();
    if (u) setUser(u);
    if (process.env.NEXT_PUBLIC_API_URL) {
      setApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);
    }
    fetchHealth();
  }, []);

  const dbComponent = health?.components?.database;
  const llmComponent = health?.components?.llm;
  const dockerComponent = health?.components?.docker;

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar title="Settings" subtitle="Environment Parameters & Security Configuration" />

      <main className="p-6 max-w-5xl w-full mx-auto space-y-6 font-sans">
        <div>
          <h2 className="text-base sm:text-lg font-bold text-text-primary flex items-center gap-2 tracking-tight">
            <Settings className="w-5 h-5 text-cyan-400" />
            Platform &amp; Integration Parameters
          </h2>
          <p className="text-xs sm:text-sm text-text-secondary mt-0.5">
            Live subsystem diagnostics, maintainer identity, API connection, and security policy limits.
          </p>
        </div>

        {/* Live Subsystems & Diagnostics */}
        <div className="p-6 rounded-2xl bg-surface/90 border border-border-subtle space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3.5">
            <div className="flex items-center gap-2 text-text-primary text-sm font-bold">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Live Subsystems &amp; Operational Health
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-mono px-2.5 py-1 rounded font-bold uppercase border ${
                  healthLoading
                    ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30 animate-pulse"
                    : health?.status === "healthy" || health?.status === "operational"
                    ? "bg-semantic-success/10 text-semantic-success border-semantic-success/30"
                    : health?.status === "degraded"
                    ? "bg-amber-attention/10 text-amber-attention border-amber-attention/30"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                }`}
              >
                {healthLoading
                  ? "PROBING SUBSYSTEMS..."
                  : health?.status === "operational" || health?.status === "healthy"
                  ? "SYSTEM OPERATIONAL"
                  : health?.status === "degraded"
                  ? "SYSTEM DEGRADED (AST FALLBACK)"
                  : "SYSTEM DISCONNECTED"}
              </span>
              <button
                onClick={fetchHealth}
                disabled={healthLoading}
                className="text-[10px] font-mono px-2 py-0.5 rounded border border-border-subtle hover:border-cyan-400/40 text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
                title="Re-probe Subsystems"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
            {/* LLM Inference Engine */}
            <div className="bg-surface-elevated p-3.5 rounded border border-border-subtle space-y-1.5">
              <div className="flex items-center gap-1.5 text-text-muted text-[11px] font-semibold">
                <Cpu className="w-3.5 h-3.5 text-forge-lime" />
                LLM Inference Provider
              </div>
              <div className="text-text-primary font-bold">
                {healthLoading
                  ? "PROBING..."
                  : llmComponent?.details?.provider
                  ? String(llmComponent.details.provider).toUpperCase()
                  : "NOT CONFIGURED"}
              </div>
              <div className="text-text-muted text-[10px] truncate" title={String(llmComponent?.details?.model || "")}>
                Model:{" "}
                <span className="text-cyan-ice">
                  {healthLoading ? "..." : String(llmComponent?.details?.model || "none")}
                </span>
              </div>
              <div className="text-[10px]">
                {healthLoading ? (
                  <span className="text-text-muted animate-pulse">Probing status...</span>
                ) : llmComponent?.status === "operational" ? (
                  <span className="text-semantic-success">● Ready &amp; Responsive</span>
                ) : (
                  <span className="text-amber-attention">● {llmComponent?.message || "Not configured"}</span>
                )}
              </div>
            </div>

            {/* Primary Database Engine */}
            <div className="bg-surface-elevated p-3.5 rounded border border-border-subtle space-y-1.5">
              <div className="flex items-center gap-1.5 text-text-muted text-[11px] font-semibold">
                <Database className="w-3.5 h-3.5 text-cyan-ice" />
                Persistent Datastore
              </div>
              <div className="text-text-primary font-bold">
                {healthLoading
                  ? "PROBING..."
                  : dbComponent?.details?.engine
                  ? String(dbComponent.details.engine).toUpperCase()
                  : "SQLITE (AIOSQLITE)"}
              </div>
              <div className="text-text-muted text-[10px]">
                Migration:{" "}
                <span className="text-forge-lime">
                  {healthLoading ? "..." : String(dbComponent?.details?.migration_version || "Head")}
                </span>
              </div>
              <div className="text-[10px]">
                {healthLoading ? (
                  <span className="text-text-muted animate-pulse">Probing datastore...</span>
                ) : dbComponent?.status === "operational" ? (
                  <span className="text-semantic-success">● Connected &amp; Verified</span>
                ) : (
                  <span className="text-rose-400">● Connection Error</span>
                )}
              </div>
            </div>

            {/* Sandbox Execution Engine */}
            <div className="bg-surface-elevated p-3.5 rounded border border-border-subtle space-y-1.5">
              <div className="flex items-center gap-1.5 text-text-muted text-[11px] font-semibold">
                <Box className="w-3.5 h-3.5 text-ultraviolet" />
                Test Sandbox Isolation
              </div>
              <div className="text-text-primary font-bold">
                {healthLoading
                  ? "PROBING..."
                  : dockerComponent?.status === "operational"
                  ? "DOCKER CONTAINER"
                  : "AST STATIC VALIDATION"}
              </div>
              <div className="text-text-muted text-[10px]">
                Mode:{" "}
                {healthLoading
                  ? "..."
                  : dockerComponent?.status === "operational"
                  ? "Containerized Sandbox"
                  : "Deterministic Fallback"}
              </div>
              <div
                className={`text-[10px] ${
                  dockerComponent?.status === "operational" ? "text-semantic-success" : "text-amber-attention"
                }`}
              >
                ●{" "}
                {healthLoading
                  ? "Probing sandbox..."
                  : dockerComponent?.status === "operational"
                  ? "Daemon Connected"
                  : "AST Sandbox Active"}
              </div>
            </div>
          </div>
        </div>

        {/* Maintainer Session Info */}
        <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 text-text-primary font-mono text-xs font-bold uppercase tracking-wider border-b border-border-subtle pb-3">
            <User className="w-4 h-4 text-ultraviolet" />
            Active Maintainer Session Profile
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Display Name:</span>
              <span className="text-text-primary font-semibold">{user?.display_name || "DevSquad Principal Maintainer"}</span>
            </div>
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Email Address:</span>
              <span className="text-forge-lime font-bold">{user?.email || "maintainer@devsquad.ai"}</span>
            </div>
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Session Account ID:</span>
              <span className="text-text-secondary">{user?.id || "Auto-provisioned on session start"}</span>
            </div>
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Cryptographic Token Algorithm:</span>
              <span className="text-semantic-success font-bold">HMAC-SHA256 (Signed Bearer)</span>
            </div>
          </div>
        </div>

        {/* Backend Connection */}
        <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 text-text-primary font-mono text-xs font-bold uppercase tracking-wider border-b border-border-subtle pb-3">
            <Server className="w-4 h-4 text-cyan-ice" />
            FastAPI Backend Connection
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between items-center bg-surface-elevated p-3 rounded border border-border-subtle">
              <div>
                <span className="text-text-primary font-semibold">FastAPI Target URL</span>
                <p className="text-text-muted text-[11px]">Base API address configured via NEXT_PUBLIC_API_URL</p>
              </div>
              <span className="text-forge-lime bg-background px-2.5 py-1 rounded border border-border-subtle font-bold">
                {apiBaseUrl}
              </span>
            </div>

            <div className="flex justify-between items-center bg-surface-elevated p-3 rounded border border-border-subtle">
              <div>
                <span className="text-text-primary font-semibold">CORS Origin Security</span>
                <p className="text-text-muted text-[11px]">Strict origin matching allowed in FastAPI backend configuration</p>
              </div>
              <span className="text-semantic-success font-mono text-[11px]">
                http://localhost:3000, http://127.0.0.1:3000
              </span>
            </div>

            <div className="flex justify-between items-center bg-surface-elevated p-3 rounded border border-border-subtle">
              <div>
                <span className="text-text-primary font-semibold">Environment Mode</span>
                <p className="text-text-muted text-[11px]">Operational environment runtime flag</p>
              </div>
              <span className="text-cyan-ice font-mono text-[11px] uppercase">
                {health?.environment || "development"}
              </span>
            </div>
          </div>
        </div>

        {/* Safety & Policy Limits */}
        <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 text-text-primary font-mono text-xs font-bold uppercase tracking-wider border-b border-border-subtle pb-3">
            <ShieldCheck className="w-4 h-4 text-forge-lime" />
            Hardened Safety &amp; Policy Boundaries
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Max Repair Attempts:</span>
              <span className="text-text-primary font-bold">3 attempts</span>
            </div>
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Max Patch Size:</span>
              <span className="text-text-primary font-bold">1 MB</span>
            </div>
            <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
              <span className="text-text-muted block text-[10px]">Docker Memory Limit:</span>
              <span className="text-text-primary font-bold">1 GB</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
