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
  CheckCircle2,
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
        {/* Realtime Instant Inspector & Solver Station (2-Column Hero) */}
        <motion.section
          id="solver-section"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <QuickSolverSection
            key={selectedTarget}
            initialTarget={selectedTarget}
            onLaunchFullWorkflow={handleLaunchFullWorkflow}
          />
        </motion.section>

        {/* Unified Platform Metrics using MetricCard with Skeletons */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
        >
          <MetricCard
            label="Repositories"
            value={stats?.repositories_count ?? 0}
            icon={GitBranch}
            sublabel="Active targets"
            status={stats && stats.repositories_count > 0 ? "lime" : "normal"}
            loading={loading}
          />
          <MetricCard
            label="Open Issues"
            value={stats?.open_issues_count ?? 0}
            icon={AlertCircle}
            sublabel="Backlog queue"
            status={stats && stats.open_issues_count > 0 ? "warning" : "normal"}
            loading={loading}
          />
          <MetricCard
            label="Active Runs"
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
            label="Completed"
            value={stats?.completed_runs_count ?? 0}
            icon={CheckCircle2}
            sublabel="Verified patches"
            status={stats && stats.completed_runs_count > 0 ? "success" : "normal"}
            loading={loading}
          />
        </motion.div>

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
                <div className="space-y-3 py-4">
                  <div className="h-12 bg-surface-elevated animate-pulse rounded-xl" />
                  <div className="h-12 bg-surface-elevated animate-pulse rounded-xl" />
                  <div className="h-12 bg-surface-elevated animate-pulse rounded-xl" />
                </div>
              ) : authRequired ? (
                <div className="py-8 text-center text-sm font-sans text-text-muted bg-surface-elevated/40 rounded-2xl border border-border-subtle space-y-3">
                  <p className="text-text-secondary">Maintainer authentication required to view scoped workflow executions.</p>
                  <div>
                    <Link
                      href="/login"
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 text-black font-bold hover:from-cyan-300 hover:to-emerald-300 transition-all text-xs shadow-md shadow-cyan-500/20"
                    >
                      <UserIcon className="w-4 h-4" />
                      Authenticate as Lead Maintainer
                    </Link>
                  </div>
                </div>
              ) : runs.length === 0 ? (
                <div className="py-10 text-center text-sm font-sans text-text-secondary bg-surface-elevated/40 rounded-2xl border border-border-subtle space-y-2">
                  <PlayCircle className="w-8 h-8 text-cyan-400 mx-auto opacity-80" />
                  <p className="font-semibold text-text-primary">No orchestrations executed yet</p>
                  <p className="text-xs text-text-muted max-w-sm mx-auto">
                    Try a one-click benchmark above or paste any repository URL to launch your first multi-agent workflow.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm font-sans text-left">
                    <thead>
                      <tr className="border-b border-border-subtle text-text-muted uppercase text-xs font-semibold">
                        <th className="pb-3">Target Issue</th>
                        <th className="pb-3">Status</th>
                        <th className="pb-3">Agents</th>
                        <th className="pb-3">Updated</th>
                        <th className="pb-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {runs.slice(0, 6).map((r) => {
                        const progress =
                          r.status === "COMPLETED" || r.status === "APPROVED"
                            ? "6/6"
                            : r.status === "AWAITING_APPROVAL" || r.current_node.includes("review") || r.current_node.includes("final")
                            ? "5/6"
                            : r.current_node.includes("test")
                            ? "4/6"
                            : r.current_node.includes("code") || r.current_node.includes("patch")
                            ? "3/6"
                            : r.current_node.includes("plan")
                            ? "2/6"
                            : r.status === "FAILED"
                            ? "0/6"
                            : "1/6";

                        return (
                          <tr
                            key={r.id}
                            onClick={() => {
                              setActiveRun(r);
                              api.getRunEvents(r.id).then(setRunEvents).catch(() => setRunEvents([]));
                            }}
                            className={`cursor-pointer transition-colors ${
                              activeRun?.id === r.id
                                ? "bg-surface-elevated/80 border-l-2 border-l-cyan-400"
                                : "hover:bg-surface-elevated/50"
                            }`}
                          >
                            <td className="py-3.5 font-medium text-text-primary">
                              <Link
                                href={`/runs/${r.id}`}
                                className="text-emerald-400 hover:text-emerald-300 hover:underline flex items-center gap-1.5 font-medium"
                              >
                                <span className="truncate max-w-[180px] sm:max-w-xs">
                                  {r.repository_id.includes("/")
                                    ? `Issue in ${r.repository_id}`
                                    : `Defect #${r.id.slice(0, 6)}`}
                                </span>
                              </Link>
                              <span className="text-xs text-text-muted block font-mono mt-0.5">
                                ID: {r.id.slice(0, 8)}…
                              </span>
                            </td>
                            <td className="py-3.5">
                              <StatusBadge status={r.status} />
                            </td>
                            <td className="py-3.5">
                              <span className="px-2.5 py-1 rounded-full bg-surface-elevated text-cyan-ice border border-cyan-ice/20 text-xs font-mono font-bold">
                                {progress}
                              </span>
                            </td>
                            <td className="py-3.5 text-text-muted text-xs font-mono">
                              {formatDate(r.created_at)}
                            </td>
                            <td className="py-3.5 text-right">
                              <Link
                                href={`/runs/${r.id}`}
                                className="px-3.5 py-1.5 rounded-xl bg-surface-elevated hover:bg-surface-hover text-text-primary text-xs font-medium border border-border-subtle transition-colors shadow-sm"
                              >
                                Inspect &rarr;
                              </Link>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.div>
          </div>

          {/* Right Column: System Status, Invariant Guardrails & Live Stream (1/3 width) */}
          <div className="lg:col-span-1 space-y-6">
            {/* System Guardrails & Invariants Panel */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="p-5 rounded-2xl bg-surface/90 border border-border-subtle space-y-4 shadow-sm"
            >
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                    Safety &amp; Invariants
                  </h3>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                  FAIL-CLOSED
                </span>
              </div>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="p-3 rounded-xl bg-surface-elevated/70 border border-border-subtle/80 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    <span className="text-text-primary text-[11px]">Docker Isolation</span>
                  </div>
                  <span className="text-text-muted text-[10px]">Non-root (1000:1000)</span>
                </div>

                <div className="p-3 rounded-xl bg-surface-elevated/70 border border-border-subtle/80 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-text-primary text-[11px]">Minimal Patch Scope</span>
                  </div>
                  <span className="text-text-muted text-[10px]">&le; 100 LoC per issue</span>
                </div>

                <div className="p-3 rounded-xl bg-surface-elevated/70 border border-border-subtle/80 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="text-text-primary text-[11px]">Human Approval Gate</span>
                  </div>
                  <span className="text-text-muted text-[10px]">Strict mandatory sign-off</span>
                </div>
              </div>
            </motion.div>

            {/* Subsystem Readiness Indicators */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.35 }}
              className="p-5 rounded-2xl bg-surface/90 border border-border-subtle space-y-3.5 shadow-sm"
            >
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                    Subsystem Probes
                  </h3>
                </div>
                <Link href="/health" className="text-[11px] text-emerald-400 font-mono hover:text-emerald-300 hover:underline">
                  Diagnostics &rarr;
                </Link>
              </div>

              <div className="space-y-2 text-xs font-mono">
                {/* LLM Engine */}
                <div className="p-2.5 rounded-xl bg-surface-elevated/70 border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-text-primary text-[11px]">LLM Synthesis Engine</span>
                  </div>
                  <span className="text-emerald-400 text-[11px] font-semibold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    GEMINI 2.0 FLASH
                  </span>
                </div>

                {/* Database */}
                <div className="p-2.5 rounded-xl bg-surface-elevated/70 border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-text-primary text-[11px]">Database (SQLite Async)</span>
                  </div>
                  <span className="text-emerald-400 text-[11px] font-semibold">
                    {health?.components?.database?.latency_ms
                      ? `${health.components.database.latency_ms.toFixed(1)}ms`
                      : "ACTIVE"}
                  </span>
                </div>

                {/* Docker */}
                <div className="p-2.5 rounded-xl bg-surface-elevated/70 border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Container className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-text-primary text-[11px]">Container Sandbox</span>
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
                <div className="p-2.5 rounded-xl bg-surface-elevated/70 border border-border-subtle flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-text-primary text-[11px]">Checkpoint Table</span>
                  </div>
                  <span className="text-cyan-400 text-[11px] font-semibold">
                    ISOLATED THREADS
                  </span>
                </div>
              </div>
            </motion.div>

            {/* High-Tech Activity Stream from Real Events */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.4 }}
              className="p-5 rounded-2xl bg-surface/90 border border-border-subtle space-y-3.5 shadow-sm"
            >
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                    Live Event Stream
                  </h3>
                </div>
                <Link href="/logs" className="text-[11px] text-cyan-400 font-mono hover:text-cyan-300 hover:underline">
                  View full &rarr;
                </Link>
              </div>

              {runEvents.length === 0 ? (
                <div className="p-4 text-center text-xs font-mono text-text-muted">
                  No recent agent events in stream.
                </div>
              ) : (
                <div className="space-y-2">
                  {runEvents.slice(0, 4).map((ev) => {
                    const agentLower = ev.agent_name.toLowerCase();
                    const badgeColor = agentLower.includes("plan")
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
                      : agentLower.includes("code")
                      ? "text-purple-400 bg-purple-500/10 border-purple-500/30"
                      : agentLower.includes("security")
                      ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
                      : agentLower.includes("test")
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
                      : "text-cyan-400 bg-cyan-500/10 border-cyan-500/30";

                    return (
                      <motion.div
                        key={ev.id}
                        whileHover={{ scale: 1.01 }}
                        className="p-3 rounded-xl bg-surface-elevated/70 border border-border-subtle/80 text-xs font-mono space-y-1.5 transition-all shadow-inner"
                      >
                        <div className="flex items-center justify-between text-[10px]">
                          <span className={`px-2 py-0.5 rounded-md font-bold uppercase border ${badgeColor}`}>
                            {ev.agent_name}
                          </span>
                          <span className="text-text-muted">
                            {formatDate(ev.created_at)}
                          </span>
                        </div>
                        <p className="text-text-secondary text-[11px] leading-relaxed truncate font-mono">
                          {ev.message}
                        </p>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}
