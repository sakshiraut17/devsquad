"use client";

import React, { useState, useEffect, Suspense, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ShieldCheck,
  Server,
  Terminal,
  ArrowRight,
  AlertCircle,
  Loader2,
  Lock,
  User,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  ShieldAlert,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { setSession, getSessionUser } from "@/lib/auth/session";
import { DevSquadLogo } from "@/components/layout/DevSquadLogo";

interface DemoProfile {
  title: string;
  email: string;
  displayName: string;
  role: string;
}

const DEMO_PROFILES: DemoProfile[] = [
  {
    title: "Lead Maintainer",
    email: "maintainer@devsquad.ai",
    displayName: "DevSquad Lead Maintainer",
    role: "Full System & Approval Authority",
  },
  {
    title: "Principal AI Architect",
    email: "architect@devsquad.ai",
    displayName: "Principal AI Architect",
    role: "Agent Orchestration & Tuning",
  },
  {
    title: "Security & QA Lead",
    email: "qa-lead@devsquad.ai",
    displayName: "QA & Verification Lead",
    role: "Patch Verification & Sandbox Gate",
  },
];

type HealthStatus = "checking" | "operational" | "degraded" | "offline";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get("from") || "/";

  const [email, setEmail] = useState("maintainer@devsquad.ai");
  const [displayName, setDisplayName] = useState("DevSquad Lead Maintainer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("checking");
  const [isRetryingHealth, setIsRetryingHealth] = useState(false);

  // Check health on mount and provide retry
  const verifyBackendHealth = useCallback(async () => {
    setIsRetryingHealth(true);
    setHealthStatus("checking");
    try {
      const res = await api.getHealth();
      if (res?.status === "operational" || res?.status === "healthy") {
        setHealthStatus("operational");
      } else if (res?.status === "degraded") {
        setHealthStatus("degraded");
      } else {
        setHealthStatus("offline");
      }
    } catch {
      setHealthStatus("offline");
    } finally {
      setIsRetryingHealth(false);
    }
  }, []);

  useEffect(() => {
    // If already signed in, redirect to returnUrl
    const existing = getSessionUser();
    if (existing) {
      router.push(returnUrl);
      return;
    }

    verifyBackendHealth();
  }, [router, returnUrl, verifyBackendHealth]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email || !displayName) {
      setError("Please specify both maintainer email and display name.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const session = await api.createSession(email.trim(), displayName.trim());
      setSession(session.access_token, session.user);
      router.push(returnUrl);
    } catch (err: any) {
      setError(
        err?.message ||
          "Authentication failed. Ensure FastAPI backend is running on http://127.0.0.1:8000."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProfile = (profile: DemoProfile) => {
    setEmail(profile.email);
    setDisplayName(profile.displayName);
    setError(null);
  };

  return (
    <div className="min-h-screen w-full bg-[#0B0D0F] text-foreground flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden font-mono">
      {/* Background Ambience */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-forge-lime/5 rounded-full blur-[140px]" />
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-ultraviolet/5 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-3">
            <DevSquadLogo size="lg" showWordmark={true} />
          </div>
          <p className="text-xs text-text-muted">
            Autonomous Multi-Agent Software Engineering Platform
          </p>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-surface border border-border-subtle text-[11px] text-text-secondary">
            <Server className="w-3.5 h-3.5 text-text-muted" />
            <span>FastAPI Engine:</span>
            {healthStatus === "operational" && (
              <span className="text-forge-lime flex items-center gap-1 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-forge-lime animate-pulse" />
                ONLINE (8000)
              </span>
            )}
            {healthStatus === "degraded" && (
              <span className="text-amber-attention flex items-center gap-1 font-semibold" title="Docker unavailable, AST fallback active">
                <AlertTriangle className="w-3 h-3 text-amber-attention" />
                DEGRADED (AST Fallback)
              </span>
            )}
            {healthStatus === "offline" && (
              <span className="text-semantic-danger font-semibold flex items-center gap-1">
                <ShieldAlert className="w-3 h-3" />
                OFFLINE
              </span>
            )}
            {healthStatus === "checking" && (
              <span className="text-amber-attention flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                CHECKING...
              </span>
            )}
            <button
              type="button"
              onClick={verifyBackendHealth}
              disabled={isRetryingHealth}
              className="ml-1 p-0.5 rounded text-text-muted hover:text-text-primary hover:bg-surface-elevated transition-colors disabled:opacity-50"
              title="Re-check backend health"
            >
              <RefreshCw className={`w-3 h-3 ${isRetryingHealth ? "animate-spin text-forge-lime" : ""}`} />
            </button>
          </div>
        </div>

        {/* Main Authentication Card */}
        <div className="p-6 rounded-lg bg-surface border border-border-subtle shadow-2xl space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-primary uppercase tracking-wider">
              <Lock className="w-4 h-4 text-forge-lime" />
              <span>Maintainer Console Access</span>
            </div>
            <span className="text-[10px] text-forge-lime px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle">
              v1.0-LIVE
            </span>
          </div>

          {error && (
            <div className="p-3 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-xs text-semantic-danger flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                <User className="w-3 h-3 text-text-muted" />
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 rounded bg-surface-elevated border border-border-subtle text-xs text-text-primary focus:outline-none focus:border-forge-lime transition-colors"
                placeholder="maintainer@devsquad.ai"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                <Terminal className="w-3 h-3 text-text-muted" />
                Display Name / Role
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="w-full px-3 py-2 rounded bg-surface-elevated border border-border-subtle text-xs text-text-primary focus:outline-none focus:border-forge-lime transition-colors"
                placeholder="DevSquad Maintainer"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded bg-forge-lime hover:bg-[#c2ef4c] text-[#0B0D0F] font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(215,255,100,0.2)] disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>AUTHENTICATING AGENT RUNTIME...</span>
                </>
              ) : (
                <>
                  <span>AUTHENTICATE & ENTER CONTROL ROOM</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Select Demo Profiles */}
          <div className="pt-3 border-t border-border-subtle space-y-2">
            <div className="text-[10px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-amber-attention" />
              <span>Teacher / Demo Quick Switch:</span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {DEMO_PROFILES.map((profile) => (
                <button
                  key={profile.email}
                  type="button"
                  onClick={() => handleSelectProfile(profile)}
                  className={`p-2.5 rounded text-left transition-all border text-xs flex items-center justify-between ${
                    email === profile.email
                      ? "bg-surface-elevated border-forge-lime text-text-primary"
                      : "bg-[#101419] border-border-subtle text-text-secondary hover:border-text-muted"
                  }`}
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-semibold text-text-primary text-[11px] truncate flex items-center gap-1.5">
                      {profile.title}
                      {email === profile.email && (
                        <CheckCircle2 className="w-3 h-3 text-forge-lime" />
                      )}
                    </div>
                    <div className="text-[10px] text-text-muted truncate">
                      {profile.email} • {profile.role}
                    </div>
                  </div>
                  <span className="text-[10px] text-text-muted font-mono uppercase shrink-0">
                    Select
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Security and Guarantee Badge */}
        <div className="p-3 rounded bg-surface border border-border-subtle text-[11px] text-text-muted flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-forge-lime" />
            <span>Strict Verification • Grounded AST Sandbox</span>
          </div>
          <span className="text-[10px] text-text-secondary">Bearer JWT Auth</span>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen w-full bg-[#0B0D0F] flex items-center justify-center font-mono text-xs text-text-muted">
          <Loader2 className="w-5 h-5 animate-spin text-forge-lime mr-2" />
          Initializing DevSquad Maintainer Console...
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
