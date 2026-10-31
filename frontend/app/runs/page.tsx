"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { PlayCircle, ShieldAlert, ArrowRight, Filter, Activity } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { RunStageStepper } from "@/components/runs/RunStageStepper";
import { api } from "@/lib/api/client";
import { Run, RunStatus } from "@/types";
import { formatDate } from "@/lib/utils";
import { useInterval } from "@/hooks/useInterval";
import { IssueDispatcherModal } from "@/components/runs/IssueDispatcherModal";

export default function RunsDashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [filterStatus, setFilterStatus] = useState<RunStatus | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDispatcherOpen, setIsDispatcherOpen] = useState(false);

  const loadRuns = async () => {
    setError(null);
    try {
      const data = await api.getRuns(
        undefined,
        filterStatus === "ALL" ? undefined : filterStatus
      );
      setRuns(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load workflow execution traces");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  // Bounded polling every 6 seconds for active workflows
  const hasActiveRuns = runs.some(
    (r) =>
      r.status === "INGESTING" ||
      r.status === "PLANNING" ||
      r.status === "CODING" ||
      r.status === "TESTING" ||
      r.status === "REVIEWING"
  );

  useInterval(() => {
    if (hasActiveRuns) {
      loadRuns();
    }
  }, hasActiveRuns ? 6000 : null);

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadRuns} title="Agent Runs" subtitle="Execution Traces &amp; Workflow Lifecycles" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6 font-sans">
        {/* Top Control Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-text-primary tracking-tight flex items-center gap-2">
              <PlayCircle className="w-5 h-5 text-cyan-400" />
              LangGraph Multi-Agent Execution Traces
            </h2>
            <p className="text-xs sm:text-sm text-text-secondary mt-0.5">
              Pipeline: <span className="text-sky-400 font-semibold font-mono">CONTEXT</span> &rarr; <span className="text-emerald-400 font-semibold font-mono">PLAN</span> &rarr; <span className="text-purple-400 font-semibold font-mono">PATCH</span> &rarr; <span className="text-rose-400 font-semibold font-mono">SECURITY</span> &rarr; <span className="text-amber-400 font-semibold font-mono">TEST</span> &rarr; <span className="text-cyan-400 font-semibold font-mono">REVIEW</span> &rarr; <span className="text-pink-400 font-semibold font-mono">HUMAN GATE</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsDispatcherOpen(true)}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 text-black text-xs sm:text-sm font-bold flex items-center gap-2 shadow-md shadow-cyan-500/20 transition-all"
            >
              <PlayCircle className="w-4 h-4 fill-black" />
              Dispatch Issue Run
            </button>

            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="text-xs sm:text-sm bg-surface-elevated border border-border-subtle rounded-xl px-3 py-2 text-text-primary focus:outline-none focus:border-cyan-400"
              >
                <option value="ALL">All Run Statuses</option>
                <option value="AWAITING_APPROVAL">Awaiting Approval</option>
                <option value="TESTING">Testing</option>
                <option value="APPROVED">Approved</option>
                <option value="FAILED">Failed (Fail-Closed)</option>
                <option value="COMPLETED">Completed</option>
              </select>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            <div className="h-32 bg-surface animate-pulse rounded border border-border-subtle" />
            <div className="h-32 bg-surface animate-pulse rounded border border-border-subtle" />
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
            No execution runs found matching filter criteria.
          </div>
        ) : (
          <div className="space-y-4">
            {runs.map((run) => (
              <div
                key={run.id}
                className="p-6 rounded-2xl bg-surface/90 border border-border-subtle hover:border-cyan-400/40 transition-all space-y-4 shadow-sm"
              >
                {/* Run Card Top Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3.5">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-cyan-400 font-mono">
                      {run.id.slice(0, 8)}…
                    </span>
                    <StatusBadge status={run.status} />
                  </div>

                  <div className="flex items-center gap-4 text-xs font-sans text-text-secondary">
                    <span>
                      Repairs: <strong className="text-text-primary font-mono">{run.retry_count} / 3</strong>
                    </span>
                    <span className="font-mono text-text-muted">Started: {formatDate(run.started_at || run.created_at)}</span>
                    <Link
                      href={`/runs/${run.id}`}
                      className="px-3.5 py-1.5 rounded-xl bg-surface-elevated hover:bg-surface-hover text-text-primary text-xs font-semibold border border-border-subtle flex items-center gap-1.5 transition-colors shadow-sm"
                    >
                      Inspect Trace <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
                    </Link>
                  </div>
                </div>

                {/* 6-Stage Execution Trace Stepper */}
                <RunStageStepper
                  currentStage={run.current_node}
                  status={run.status}
                  repairAttempts={run.retry_count}
                />

                {/* Error Summary / Policy Rejection */}
                {run.error_summary && (
                  <div className="p-3.5 rounded-xl bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
                    <strong>Fail-Closed Gate Reason:</strong> {run.error_summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <IssueDispatcherModal
          isOpen={isDispatcherOpen}
          onClose={() => {
            setIsDispatcherOpen(false);
            loadRuns();
          }}
        />
      </main>
    </div>
  );
}
