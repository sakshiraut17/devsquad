"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  GitBranch,
  AlertCircle,
  PlayCircle,
  Clock,
  ShieldCheck,
  XCircle,
  ArrowRight,
  RefreshCw,
  Terminal,
  Activity,
  Layers,
  Database,
  Container,
  User as UserIcon,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { AgentFlowVisualization } from "@/components/agents/AgentFlowVisualization";
import { api } from "@/lib/api/client";
import { getSessionUser } from "@/lib/auth/session";
import { AgentEvent, HealthResponse, OverviewStats, Run, User } from "@/types";
import { formatDate } from "@/lib/utils";

export default function CommandCenterPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [runEvents, setRunEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [sessionUser, setSessionUser] = useState<User | null>(null);
  const [authRequired, setAuthRequired] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const currentUser = getSessionUser();
    setSessionUser(currentUser);

    try {
      const [statsData, healthData, runsData] = await Promise.allSettled([
        api.getOverviewStats(),
        api.getHealth(),
        api.getRuns(undefined, undefined, 0, 10),
      ]);

      if (statsData.status === "fulfilled") {
        setStats(statsData.value);
      } else {
        const reason: any = statsData.reason;
        console.warn("Failed to load overview stats:", reason);
        setError("Overview stats could not be loaded: " + (reason?.message || "Backend unreachable"));
      }

      if (healthData.status === "fulfilled") {
        setHealth(healthData.value);
      }

      if (runsData.status === "fulfilled") {
        setAuthRequired(false);
        const fetchedRuns = runsData.value;
        setRuns(fetchedRuns);

        // Pick currently active or latest run for agent flow binding
        const target =
          fetchedRuns.find(
            (r) =>
              r.status === "INGESTING" ||
              r.status === "PLANNING" ||
              r.status === "CODING" ||
              r.status === "TESTING" ||
              r.status === "REVIEWING" ||
              r.status === "AWAITING_APPROVAL"
          ) || fetchedRuns[0] || null;

        setActiveRun(target);

        if (target) {
          try {
            const evs = await api.getRunEvents(target.id);
            setRunEvents(evs);
          } catch {
            setRunEvents([]);
          }
        }
      } else {
        const reason: any = runsData.reason;
        if (reason?.status === 401) {
          setAuthRequired(true);
        } else {
          console.warn("Failed to load runs:", reason);
        }
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load Command Center telemetry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadData} title="Command Center" subtitle="Autonomous Engineering Control Room" />

      <main className="p-6 space-y-6 max-w-7xl w-full mx-auto">
        {/* Engineering in Motion Hero Banner */}
        <div className="p-6 rounded-lg bg-surface border border-border-subtle relative overflow-hidden">
          <div className="absolute -right-16 -top-16 w-64 h-64 bg-forge-lime/5 rounded-full blur-3xl pointer-events-none" />
          <div className="max-w-2xl relative z-10 space-y-1.5">
            <div className="flex items-center gap-2 text-xs font-mono text-forge-lime">
              <span className="w-2 h-2 rounded-full bg-forge-lime animate-pulse" />
              <span>ORCHESTRATION PIPELINE ENGAGED</span>
            </div>
            <h1 className="text-2xl font-bold font-mono tracking-tight text-text-primary">
              Engineering, in motion.
            </h1>
            <p className="text-xs text-text-secondary leading-relaxed font-mono">
              Plan, patch, test, and review software changes with an autonomous engineering team.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={loadData}
              className="px-2.5 py-1 rounded bg-semantic-danger/20 hover:bg-semantic-danger/30 text-[11px] text-white"
            >
              Retry
            </button>
          </div>
        )}

        {/* Asymmetric Command Center Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Left Column: Agent Flow Visualization & Recent Runs (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Interactive Agent Flow Visualization */}
            <AgentFlowVisualization
              run={activeRun}
              events={runEvents}
            />

            {/* Recent Multi-Agent Runs Table */}
            <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                    Recent Execution Runs
                  </h3>
                  <p className="text-[11px] text-text-muted font-mono mt-0.5">
                    Live database records across active and completed LangGraph workflows.
                  </p>
                </div>
                <Link
                  href="/runs"
                  className="text-xs font-mono text-forge-lime hover:underline flex items-center gap-1"
                >
                  All Runs <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {loading ? (
                <div className="space-y-2 py-4">
                  <div className="h-10 bg-surface-elevated animate-pulse rounded" />
                  <div className="h-10 bg-surface-elevated animate-pulse rounded" />
                </div>
              ) : authRequired ? (
                <div className="py-8 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded border border-border-subtle space-y-3">
                  <p className="text-text-secondary">Maintainer authentication required to view scoped workflow executions.</p>
                  <div>
                    <Link
                      href="/login"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-forge-lime text-black font-bold hover:bg-forge-lime/90 transition-colors text-[11px]"
                    >
                      <UserIcon className="w-3.5 h-3.5" />
                      Authenticate as Lead Maintainer
                    </Link>
                  </div>
                </div>
              ) : runs.length === 0 ? (
                <div className="py-8 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded border border-border-subtle space-y-1">
                  <p className="text-text-secondary">No workflow execution records found for active session profile.</p>
                  <p className="text-[11px] text-text-muted">
                    {sessionUser
                      ? `Active maintainer: ${sessionUser.email}. Standard benchmark repositories are owned by Lead Maintainer.`
                      : "Sign in at /login to view maintainer workflow runs."}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono text-left">
                    <thead>
                      <tr className="border-b border-border-subtle text-text-muted uppercase text-[10px]">
                        <th className="pb-2.5">Run ID</th>
                        <th className="pb-2.5">Current Stage</th>
                        <th className="pb-2.5">Status</th>
                        <th className="pb-2.5">Repairs</th>
                        <th className="pb-2.5">Started</th>
                        <th className="pb-2.5 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {runs.slice(0, 6).map((r) => (
                        <tr
                          key={r.id}
                          className="hover:bg-surface-elevated/50 transition-colors"
                        >
                          <td className="py-3 font-semibold text-text-primary">
                            <Link
                              href={`/runs/${r.id}`}
                              className="text-forge-lime hover:underline"
                            >
                              {r.id.slice(0, 8)}…
                            </Link>
                          </td>
                          <td className="py-3 text-text-secondary capitalize">
                            {r.current_node.replace(/_/g, " ")}
                          </td>
                          <td className="py-3">
                            <StatusBadge status={r.status} />
                          </td>
                          <td className="py-3 text-text-muted">
                            {r.retry_count} / 3
                          </td>
                          <td className="py-3 text-text-muted">
                            {formatDate(r.created_at)}
                          </td>
                          <td className="py-3 text-right">
                            <Link
                              href={`/runs/${r.id}`}
                              className="px-2.5 py-1 rounded bg-surface-elevated hover:bg-surface-hover text-text-primary text-[11px] border border-border-subtle transition-colors"
                            >
                              Inspect
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Compact System Status & Restrained Operational Metrics (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            {/* Restrained Operational Metrics */}
            <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-3">
              <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center justify-between">
                <span>Operational Metrics</span>
                <span className="text-[10px] text-text-muted font-normal">Global Platform Aggregates</span>
              </h3>

              <div className="grid grid-cols-2 gap-2.5">
                <MetricCard
                  label="Repositories"
                  value={stats?.repositories_count ?? 0}
                  icon={GitBranch}
                  sublabel="Active targets"
                  loading={loading}
                />
                <MetricCard
                  label="Open Issues"
                  value={stats?.open_issues_count ?? 0}
                  icon={AlertCircle}
                  sublabel="Backlog queue"
                  loading={loading}
                />
                <MetricCard
                  label="Total Runs"
                  value={stats?.total_runs_count ?? 0}
                  icon={Layers}
                  sublabel="Orchestrations"
                  loading={loading}
                />
                <MetricCard
                  label="Active"
                  value={stats?.active_runs_count ?? 0}
                  icon={PlayCircle}
                  sublabel="In graph"
                  status={stats && stats.active_runs_count > 0 ? "lime" : "normal"}
                  loading={loading}
                />
                <MetricCard
                  label="Awaiting Gate"
                  value={stats?.awaiting_approval_count ?? 0}
                  icon={Clock}
                  sublabel="Human sign-off"
                  status={stats && stats.awaiting_approval_count > 0 ? "warning" : "normal"}
                  loading={loading}
                />
                <MetricCard
                  label="Fail-Closed"
                  value={stats?.failed_runs_count ?? 0}
                  icon={XCircle}
                  sublabel="Test rejections"
                  status={stats && stats.failed_runs_count > 0 ? "danger" : "normal"}
                  loading={loading}
                />
              </div>
            </div>

            {/* Subsystem Readiness Indicators */}
            <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-3">
              <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center justify-between">
                <span>Subsystem Probes</span>
                <Link href="/health" className="text-[11px] text-forge-lime hover:underline">
                  Diagnostics
                </Link>
              </h3>

              <div className="space-y-2 text-xs font-mono">
                {/* Database */}
                <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5 text-forge-lime" />
                    <span className="text-text-primary">Database (SQLite Async)</span>
                  </div>
                  <span className="text-semantic-success text-[11px]">
                    {health?.components?.database?.latency_ms
                      ? `${health.components.database.latency_ms.toFixed(1)}ms`
                      : "ACTIVE"}
                  </span>
                </div>

                {/* Docker */}
                <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Container className="w-3.5 h-3.5 text-cyan-ice" />
                    <span className="text-text-primary">Container Sandbox</span>
                  </div>
                  <span
                    className={
                      health?.components?.docker?.status === "operational"
                        ? "text-forge-lime text-[11px] font-semibold"
                        : "text-amber-attention text-[11px]"
                    }
                  >
                    {health?.components?.docker?.status === "operational"
                      ? "DOCKER ACTIVE"
                      : "AST FALLBACK"}
                  </span>
                </div>

                {/* Checkpointer */}
                <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-ultraviolet" />
                    <span className="text-text-primary">Checkpoint Table</span>
                  </div>
                  <span className="text-semantic-success text-[11px]">
                    ISOLATED THREADS
                  </span>
                </div>
              </div>
            </div>

            {/* Compact Activity Stream from Real Events */}
            <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                  Live Event Stream
                </h3>
                <Link href="/logs" className="text-[11px] text-forge-lime font-mono hover:underline">
                  View stream
                </Link>
              </div>

              {runEvents.length === 0 ? (
                <div className="p-4 text-center text-xs font-mono text-text-muted">
                  No recent agent events in stream.
                </div>
              ) : (
                <div className="space-y-2">
                  {runEvents.slice(0, 4).map((ev) => (
                    <div
                      key={ev.id}
                      className="p-2.5 rounded bg-surface-elevated border border-border-subtle text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-forge-lime font-bold uppercase">
                          {ev.agent_name}
                        </span>
                        <span className="text-text-muted">
                          {formatDate(ev.created_at)}
                        </span>
                      </div>
                      <p className="text-text-secondary text-[11px] leading-snug truncate">
                        {ev.message}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
