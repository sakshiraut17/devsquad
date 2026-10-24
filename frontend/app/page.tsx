"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
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
  Zap,
  Sparkles,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { AgentFlowVisualization } from "@/components/agents/AgentFlowVisualization";
import { QuickSolverSection } from "@/components/solver/QuickSolverSection";
import { api } from "@/lib/api/client";
import { getSessionUser } from "@/lib/auth/session";
import { AgentEvent, HealthResponse, OverviewStats, Run, User } from "@/types";
import { formatDate } from "@/lib/utils";

export default function CommandCenterPage() {
  const router = useRouter();
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [runEvents, setRunEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<string>("");

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

  async function handleLaunchFullWorkflow(repoFullName: string, issueNumber?: number) {
    try {
      const importRes = await api.importRepository(repoFullName, true);
      const repo = importRes.repository;

      let issueId: string | null = null;
      const issues = await api.getIssues(repo.id);

      if (issueNumber) {
        const match = issues.find((i) => i.github_issue_number === issueNumber);
        if (match) issueId = match.id;
      }

      if (!issueId && issueNumber) {
        try {
          const synced = await api.syncRepositoryGitHubIssue(repo.id, issueNumber);
          issueId = synced.id;
        } catch {
          // Fallback to local defect creation without getting blocked by GitHub rate limits
          const created = await api.createIssue({
            repository_id: repo.id,
            github_issue_number: issueNumber,
            title: `Issue #${issueNumber} for ${repoFullName}`,
            body: `Ingested issue report for ${repoFullName}`,
            state: "open",
            labels: ["bug", "autonomous-import"],
          });
          issueId = created.id;
        }
      }

      if (!issueId && issues.length > 0) {
        issueId = issues[0].id;
      }

      if (!issueId) {
        const created = await api.createIssue({
          repository_id: repo.id,
          github_issue_number: 1,
          title: `Resolve runtime defect in ${repoFullName}`,
          body: `Autonomous agent resolution workspace for ${repoFullName}`,
          state: "open",
          labels: ["bug", "autonomous-import"],
        });
        issueId = created.id;
      }

      if (issueId) {
        const newRun = await api.createRun(repo.id, issueId);
        await api.startRun(newRun.id, { background: true });
        router.push(`/runs/${newRun.id}`);
      } else {
        router.push(`/runs`);
      }
    } catch (err: any) {
      console.warn("Could not dispatch run automatically:", err);
      router.push(`/runs`);
    }
  }

  function handleSelectIssueForSolve(issue: any) {
    const url = `https://github.com/${issue.repository_name}/issues/${issue.number}`;
    setSelectedTarget(url);
    window.scrollTo({ top: 200, behavior: "smooth" });
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-transparent">
      <Navbar
        onRefresh={loadData}
        title="Command Center"
        subtitle="Autonomous Engineering Control Room"
        onSelectIssueForSolve={handleSelectIssueForSolve}
      />

      <main className="p-6 space-y-8 max-w-7xl w-full mx-auto relative z-10">
        {/* Engineering in Motion Hero Banner with Motion */}
        <motion.div
          initial={{ opacity: 0, y: -15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="p-6 lg:p-8 rounded-3xl bg-gradient-to-br from-surface/90 via-surface/80 to-surface-elevated/90 border border-cyan-500/20 backdrop-blur-2xl relative overflow-hidden shadow-2xl"
        >
          <div className="absolute -right-16 -top-16 w-80 h-80 bg-gradient-to-br from-cyan-400/15 via-emerald-400/10 to-transparent rounded-full blur-3xl pointer-events-none" />
          <div className="max-w-2xl relative z-10 space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="font-bold tracking-wider">REALTIME MULTI-AGENT PLATFORM ACTIVE</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black font-mono tracking-tight text-text-primary">
              Engineering, in{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-400 to-lime-300">
                motion.
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-sans max-w-xl">
              Inspect any repository link to diagnose defects and formulate unified patches in seconds, or discover and resolve your GitHub account issues in real time.
            </p>

            <div className="flex items-center gap-3 pt-2 text-xs font-mono">
              <motion.a
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                href="#solver-section"
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 text-black font-bold flex items-center gap-1.5 shadow-md shadow-cyan-500/20"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Try Quick Solver</span>
              </motion.a>
              <Link
                href="/repositories"
                className="px-4 py-2 rounded-xl bg-surface-elevated/80 border border-border-subtle hover:border-cyan-400/40 text-text-secondary hover:text-cyan-300 flex items-center gap-1.5 transition-colors"
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Ingest Repositories</span>
              </Link>
            </div>
          </div>
        </motion.div>

        {/* Realtime Instant Inspector & Solver Section with Motion */}
        <motion.section
          id="solver-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        >
          <QuickSolverSection
            key={selectedTarget}
            initialTarget={selectedTarget}
            onLaunchFullWorkflow={handleLaunchFullWorkflow}
          />
        </motion.section>

        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-3.5 rounded-xl bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono flex items-center justify-between shadow-sm"
          >
            <span>{error}</span>
            <button
              onClick={loadData}
              className="px-2.5 py-1 rounded-lg bg-semantic-danger/20 hover:bg-semantic-danger/30 text-[11px] text-white transition-colors"
            >
              Retry
            </button>
          </motion.div>
        )}

        {/* Asymmetric Command Center Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Left Column: Agent Flow Visualization & Recent Runs (2/3 width) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Interactive Agent Flow Visualization */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <AgentFlowVisualization
                run={activeRun}
                events={runEvents}
              />
            </motion.div>

            {/* Recent Multi-Agent Runs Table */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.25 }}
              className="p-5 rounded-xl bg-surface border border-border-subtle space-y-4 shadow-sm"
            >
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
                  className="text-xs font-mono text-emerald-400 hover:underline flex items-center gap-1 font-semibold"
                >
                  All Runs <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {loading ? (
                <div className="space-y-2 py-4">
                  <div className="h-10 bg-surface-elevated animate-pulse rounded-lg" />
                  <div className="h-10 bg-surface-elevated animate-pulse rounded-lg" />
                </div>
              ) : authRequired ? (
                <div className="py-8 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded-xl border border-border-subtle space-y-3">
                  <p className="text-text-secondary">Maintainer authentication required to view scoped workflow executions.</p>
                  <div>
                    <Link
                      href="/login"
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500 text-black font-bold hover:bg-emerald-400 transition-colors text-[11px]"
                    >
                      <UserIcon className="w-3.5 h-3.5" />
                      Authenticate as Lead Maintainer
                    </Link>
                  </div>
                </div>
              ) : runs.length === 0 ? (
                <div className="py-8 text-center text-xs font-mono text-text-muted bg-surface-elevated/40 rounded-xl border border-border-subtle space-y-1">
                  <p className="text-text-secondary">No workflow execution records found for active session profile.</p>
                  <p className="text-[11px] text-text-muted">
                    {sessionUser
                      ? `Active maintainer: ${sessionUser.email}. Connect any GitHub repository or inspect an issue to dispatch a run.`
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
                              className="text-emerald-400 hover:underline"
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
                              className="px-2.5 py-1 rounded-lg bg-surface-elevated hover:bg-surface-hover text-text-primary text-[11px] border border-border-subtle transition-colors"
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
            </motion.div>
          </div>

          {/* Right Column: Compact System Status & Restrained Operational Metrics (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            {/* Restrained Operational Metrics */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="p-4 rounded-xl bg-surface border border-border-subtle space-y-3 shadow-sm"
            >
              <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center justify-between">
                <span>Operational Metrics</span>
                <span className="text-[10px] text-text-muted font-normal">Global Platform</span>
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
            </motion.div>

            {/* Subsystem Readiness Indicators */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
              className="p-4 rounded-xl bg-surface border border-border-subtle space-y-3 shadow-sm"
            >
              <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center justify-between">
                <span>Subsystem Probes</span>
                <Link href="/health" className="text-[11px] text-emerald-400 hover:underline">
                  Diagnostics
                </Link>
              </h3>

              <div className="space-y-2 text-xs font-mono">
                {/* Database */}
                <div className="p-2.5 rounded-lg bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-text-primary">Database (SQLite Async)</span>
                  </div>
                  <span className="text-semantic-success text-[11px]">
                    {health?.components?.database?.latency_ms
                      ? `${health.components.database.latency_ms.toFixed(1)}ms`
                      : "ACTIVE"}
                  </span>
                </div>

                {/* Docker */}
                <div className="p-2.5 rounded-lg bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Container className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-text-primary">Container Sandbox</span>
                  </div>
                  <span
                    className={
                      health?.components?.docker?.status === "operational"
                        ? "text-emerald-400 text-[11px] font-semibold"
                        : "text-amber-400 text-[11px]"
                    }
                  >
                    {health?.components?.docker?.status === "operational"
                      ? "DOCKER ACTIVE"
                      : "AST FALLBACK"}
                  </span>
                </div>

                {/* Checkpointer */}
                <div className="p-2.5 rounded-lg bg-surface-elevated border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-text-primary">Checkpoint Table</span>
                  </div>
                  <span className="text-semantic-success text-[11px]">
                    ISOLATED THREADS
                  </span>
                </div>
              </div>
            </motion.div>

            {/* Compact Activity Stream from Real Events */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
              className="p-4 rounded-xl bg-surface border border-border-subtle space-y-3 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                  Live Event Stream
                </h3>
                <Link href="/logs" className="text-[11px] text-emerald-400 font-mono hover:underline">
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
                      className="p-2.5 rounded-lg bg-surface-elevated border border-border-subtle text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="text-emerald-400 font-bold uppercase">
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
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
