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

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Top Control Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
          <div>
            <h2 className="text-sm font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <PlayCircle className="w-4 h-4 text-forge-lime" />
              LangGraph Multi-Agent Execution Traces
            </h2>
            <p className="text-xs text-text-muted font-mono mt-0.5">
              Sequence: <span className="text-cyan-ice">CONTEXT</span> → <span className="text-ultraviolet">PLAN</span> → <span className="text-forge-lime">PATCH</span> → <span className="text-cyan-ice">TEST</span> → <span className="text-amber-attention">REVIEW</span> → <span className="text-forge-lime">HUMAN GATE</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsDispatcherOpen(true)}
              className="px-3.5 py-1.5 rounded-lg bg-forge-lime hover:bg-forge-lime/90 text-black text-xs font-mono font-bold flex items-center gap-1.5 shadow-[0_0_10px_rgba(215,255,100,0.3)] transition-all"
            >
              <PlayCircle className="w-3.5 h-3.5" />
              Dispatch Issue Run
            </button>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-text-muted" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="text-xs font-mono bg-surface border border-border-subtle rounded px-2.5 py-1.5 text-text-primary focus:outline-none focus:border-forge-lime"
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
                className="p-5 rounded-lg bg-surface border border-border-subtle hover:border-border-strong transition-all space-y-4"
              >
                {/* Run Card Top Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-forge-lime font-mono">
                      {run.id}
                    </span>
                    <StatusBadge status={run.status} />
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono text-text-muted">
                    <span>
                      Repairs: <strong className="text-text-primary">{run.retry_count} / 3</strong>
                    </span>
                    <span>Started: {formatDate(run.started_at || run.created_at)}</span>
                    <Link
                      href={`/runs/${run.id}`}
                      className="px-3 py-1 rounded bg-surface-elevated hover:bg-surface-hover text-text-primary text-[11px] border border-border-subtle flex items-center gap-1 transition-colors"
                    >
                      Inspect Trace <ArrowRight className="w-3 h-3 text-forge-lime" />
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
                  <div className="p-3 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
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
