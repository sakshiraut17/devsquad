"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  FileCode2,
  Clock,
  Layers,
  ShieldCheck,
  ShieldAlert,
  Radio,
  RotateCcw,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { RunStageStepper } from "@/components/runs/RunStageStepper";
import { GroundedPlanCard } from "@/components/runs/GroundedPlanCard";
import { RepositoryContextCard } from "@/components/runs/RepositoryContextCard";
import { TestResultCard } from "@/components/runs/TestResultCard";
import { ReviewerCard } from "@/components/runs/ReviewerCard";
import { DiffViewer } from "@/components/patches/DiffViewer";
import { ApprovalModal } from "@/components/patches/ApprovalModal";
import { api } from "@/lib/api/client";
import {
  AgentEvent,
  ApprovalRecord,
  Patch,
  Run,
  WorkflowStateSnapshot,
} from "@/types";
import { formatDate, truncateHash } from "@/lib/utils";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [stateSnapshot, setStateSnapshot] = useState<WorkflowStateSnapshot | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [patches, setPatches] = useState<Patch[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [selectedPatch, setSelectedPatch] = useState<Patch | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const lastEventIdRef = useRef<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRunData = async () => {
    if (!runId) return;
    setError(null);
    try {
      const [runData, stateData, eventsData, patchesData, approvalsData] =
        await Promise.all([
          api.getRun(runId),
          api.getRunState(runId),
          api.getRunEvents(runId),
          api.getRunPatches(runId),
          api.getRunApprovals(runId),
        ]);

      setRun(runData);
      setStateSnapshot(stateData);
      setEvents(eventsData);
      setPatches(patchesData);
      setApprovals(approvalsData);

      if (patchesData.length > 0 && !selectedPatch) {
        setSelectedPatch(patchesData[patchesData.length - 1]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load run details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRunData();

    if (!runId) return;

    // Connect to Server-Sent Events stream for real-time telemetry
    setIsLiveStreaming(true);
    const unsubscribe = api.subscribeToRunStream(
      runId,
      (newEvent) => {
        lastEventIdRef.current = newEvent.id;
        setEvents((prev) => {
          if (prev.some((e) => e.id === newEvent.id)) return prev;
          return [...prev, newEvent];
        });
      },
      (statusData) => {
        setRun((prev) =>
          prev ? { ...prev, status: statusData.status, current_node: statusData.current_node } : prev
        );
      },
      () => {
        setIsLiveStreaming(false);
      },
      () => {
        setIsLiveStreaming(false);
        loadRunData();
      },
      lastEventIdRef.current
    );

    return () => {
      unsubscribe();
      setIsLiveStreaming(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const latestPatch = patches.length > 0 ? patches[patches.length - 1] : null;
  const isLatestPatchSelected = selectedPatch && latestPatch && selectedPatch.id === latestPatch.id;
  const isStalePatch = selectedPatch && latestPatch && selectedPatch.id !== latestPatch.id;

  const reviewState = stateSnapshot?.state?.review;
  const hasBlockingFindings = Boolean(
    reviewState?.findings?.some(
      (f) => String(f.severity).toUpperCase() === "CRITICAL" || String(f.severity).toUpperCase() === "BLOCKING"
    )
  );

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar
        onRefresh={loadRunData}
        title={`Run Inspection: ${runId?.slice(0, 8)}…`}
        subtitle="Full Workflow State &amp; Live Telemetry"
      />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Navigation & Status Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <Link
            href="/runs"
            className="text-xs font-mono text-text-muted hover:text-text-primary flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Agent Runs
          </Link>

          {run && (
            <div className="flex items-center gap-3">
              {isLiveStreaming && (
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-ice/10 text-cyan-ice border border-cyan-ice/30 text-[10px] font-mono font-bold animate-pulse">
                  <Radio className="w-3 h-3 text-cyan-ice" /> Live Stream Connected
                </span>
              )}
              <StatusBadge status={run.status} size="md" />
              {run.status === "AWAITING_APPROVAL" && selectedPatch && (
                <button
                  onClick={() => setIsApprovalOpen(true)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold bg-forge-lime hover:bg-forge-lime/90 text-black flex items-center gap-1.5 transition-all shadow-[0_0_12px_rgba(215,255,100,0.4)]"
                >
                  <ShieldCheck className="w-4 h-4" />
                  Review &amp; Approve Patch
                </button>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        {actionMessage && (
          <div className="p-3 rounded bg-semantic-success/15 border border-semantic-success/30 text-semantic-success text-xs font-mono">
            {actionMessage}
          </div>
        )}

        {loading || !run ? (
          <div className="space-y-4">
            <div className="h-40 bg-surface animate-pulse rounded border border-border-subtle" />
            <div className="h-64 bg-surface animate-pulse rounded border border-border-subtle" />
          </div>
        ) : (
          <>
            {/* Run Lifecycle & Stepper Card */}
            <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-border-subtle pb-3">
                <div>
                  <h2 className="text-sm font-bold text-text-primary font-mono break-all">
                    {run.id}
                  </h2>
                  <div className="text-xs text-text-muted font-mono flex items-center gap-4 mt-1">
                    <span>Repository ID: {run.repository_id}</span>
                    <span>•</span>
                    <span>Issue ID: {run.issue_id}</span>
                  </div>
                </div>
                <div className="text-xs font-mono text-text-muted space-y-0.5">
                  <div>Started: {formatDate(run.started_at || run.created_at)}</div>
                  {run.finished_at && <div>Finished: {formatDate(run.finished_at)}</div>}
                </div>
              </div>

              {/* 6-Stage Stepper */}
              <RunStageStepper
                currentStage={run.current_node}
                status={run.status}
                repairAttempts={run.retry_count}
              />
            </div>

            {/* Grounded Engineering Plan with Evidence Citations */}
            {stateSnapshot?.state?.plan && (
              <GroundedPlanCard plan={stateSnapshot.state.plan} />
            )}

            {/* Repository Context Provenance & Truncation Warnings */}
            {stateSnapshot?.state?.repository_context && (
              <RepositoryContextCard context={stateSnapshot.state.repository_context} />
            )}

            {/* Sandbox Automated Validation Results & Console Logs */}
            {stateSnapshot?.state?.test_result && (
              <TestResultCard
                testResult={stateSnapshot.state.test_result}
                validationStatus={selectedPatch?.validation_status}
              />
            )}

            {/* Reviewer Agent Findings & Risk Assessment */}
            {stateSnapshot?.state?.review && (
              <ReviewerCard review={stateSnapshot.state.review} />
            )}

            {/* Failed Patches & Anti-Repetition Registry History */}
            {stateSnapshot?.state?.failed_patch_registry && stateSnapshot.state.failed_patch_registry.length > 0 && (
              <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3 font-mono">
                <div className="flex items-center gap-2 border-b border-border-subtle pb-2">
                  <RotateCcw className="w-4 h-4 text-amber-attention" />
                  <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                    Failed Patch Registry &amp; Anti-Repetition History ({stateSnapshot.state.failed_patch_registry.length})
                  </h3>
                </div>
                <div className="space-y-2">
                  {stateSnapshot.state.failed_patch_registry.map((fp, i) => (
                    <div
                      key={i}
                      className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-semantic-danger">
                          Revision #{fp.revision} ({fp.failure_stage})
                        </span>
                        <span className="text-[10px] text-text-muted">
                          hash: {truncateHash(fp.diff_hash, 12)}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-secondary leading-snug">
                        Failure Reason: {fp.failure_reason}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Checkpointer Snapshot & Human Decision Trail */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3 font-mono">
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-cyan-ice" />
                  LangGraph Checkpointer Snapshot
                </h3>
                <div className="text-xs bg-surface-elevated p-3 rounded border border-border-subtle space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Storage Driver:</span>
                    <span className="text-forge-lime">SQLite File Checkpointer</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Thread ID:</span>
                    <span className="text-text-primary">thread-{run.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Checkpoint Found:</span>
                    <span className="text-text-primary">
                      {stateSnapshot?.checkpoint_found ? "true" : "false"}
                    </span>
                  </div>
                  {stateSnapshot?.state && (
                    <>
                      <div className="flex justify-between">
                        <span className="text-text-muted">Snapshot Stage:</span>
                        <span className="text-text-primary">
                          {stateSnapshot.state.current_stage || run.current_node}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-muted">Validation Status:</span>
                        <span className="text-semantic-success font-bold uppercase">
                          {stateSnapshot.state.validation_status || "—"}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Human Approval Audit Trail */}
              <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-3 font-mono">
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-attention" />
                  Human Approval Records ({approvals.length})
                </h3>
                {approvals.length === 0 ? (
                  <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                    No approval decisions recorded yet for this workflow execution.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {approvals.map((appr) => (
                      <div
                        key={appr.id}
                        className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={
                              appr.decision === "approved"
                                ? "text-semantic-success font-bold uppercase"
                                : "text-semantic-danger font-bold uppercase"
                            }
                          >
                            {appr.decision}
                          </span>
                          <span className="text-text-muted text-[11px]">
                            {formatDate(appr.created_at)}
                          </span>
                        </div>
                        <div className="text-[11px] text-text-muted truncate">
                          Patch Hash: {truncateHash(appr.patch_hash, 16)}
                        </div>
                        {appr.feedback && (
                          <div className="text-text-secondary italic pt-1 border-t border-border-subtle">
                            &ldquo;{appr.feedback}&rdquo;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Synthesized Patch Revisions & Unified Diff */}
            <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <FileCode2 className="w-3.5 h-3.5 text-forge-lime" />
                  Synthesized Patch Revisions ({patches.length})
                </h3>
                {patches.length > 1 && (
                  <div className="flex items-center gap-1.5">
                    {patches.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setSelectedPatch(p)}
                        className={`px-2 py-0.5 rounded text-xs transition-colors ${
                          selectedPatch?.id === p.id
                            ? "bg-forge-lime text-black font-bold"
                            : "bg-surface-elevated text-text-muted hover:text-text-primary border border-border-subtle"
                        }`}
                      >
                        rev #{p.revision}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {isStalePatch && (
                <div className="p-3 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                  <span>
                    Viewing historical revision #{selectedPatch.revision}. The latest active revision is #{latestPatch?.revision}.
                  </span>
                </div>
              )}

              {selectedPatch ? (
                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded bg-surface-elevated border border-border-subtle text-xs">
                    <div>
                      <span className="text-text-primary font-semibold">
                        rev #{selectedPatch.revision}: {selectedPatch.summary}
                      </span>
                      <div className="text-text-muted text-[11px] mt-0.5">
                        Target file: {selectedPatch.target_files.join(", ")}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-text-muted block text-[10px]">SHA-256 Hash:</span>
                      <span className="text-forge-lime text-[11px]">
                        {truncateHash(selectedPatch.content_hash, 16)}
                      </span>
                    </div>
                  </div>

                  <DiffViewer
                    diff={selectedPatch.unified_diff}
                    filename={selectedPatch.target_files[0] || "patch.diff"}
                  />
                </div>
              ) : (
                <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                  No code patches synthesized for this execution run yet.
                </div>
              )}
            </div>

            {/* Sanitized Agent Events Log */}
            <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-cyan-ice" />
                Chronological Sanitized Agent Events ({events.length})
              </h3>

              {events.length === 0 ? (
                <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded border border-border-subtle">
                  No agent events recorded yet.
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {events.map((ev) => {
                    const isHumanGatekeeper = ev.agent_name === "human_gatekeeper" || ev.event_type.startsWith("human_");
                    const isAiReviewer = ev.agent_name === "reviewer" || ev.event_type.includes("review");
                    const isTester = ev.agent_name === "tester" || ev.event_type.includes("test");

                    return (
                      <div
                        key={ev.id}
                        className="p-3 rounded bg-surface-elevated border border-border-subtle text-xs flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {isHumanGatekeeper ? (
                              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold border bg-forge-lime/10 text-forge-lime border-forge-lime/30">
                                HUMAN GATEKEEPER
                              </span>
                            ) : isAiReviewer ? (
                              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold border bg-amber-attention/10 text-amber-attention border-amber-attention/30">
                                AI REVIEWER
                              </span>
                            ) : isTester ? (
                              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold border bg-cyan-ice/10 text-cyan-ice border-cyan-ice/30">
                                TESTER
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded bg-surface text-forge-lime text-[10px] uppercase font-bold border border-border-subtle">
                                {ev.agent_name}
                              </span>
                            )}
                            <span className="text-text-secondary font-semibold font-mono">
                              {ev.agent_name === "reviewer" && ev.event_type === "patch_approved"
                                ? "ai_review_recommendation (approve)"
                                : ev.event_type}
                            </span>
                          </div>
                          <p className="text-text-primary leading-relaxed" title={ev.message}>{ev.message}</p>
                        </div>

                        <div className="text-right text-[11px] text-text-muted whitespace-nowrap">
                          <div>{formatDate(ev.created_at)}</div>
                          {ev.duration_ms && (
                            <div className="text-text-muted">{ev.duration_ms} ms</div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {/* Approval Modal */}
        {run && selectedPatch && (
          <ApprovalModal
            run={run}
            patch={selectedPatch}
            isOpen={isApprovalOpen}
            onClose={() => setIsApprovalOpen(false)}
            onSuccess={() => {
              setActionMessage("Human approval recorded successfully. State updated.");
              loadRunData();
            }}
            baseCommitSha={stateSnapshot?.state?.repository_context?.base_commit_sha}
            reviewerRecommendation={reviewState?.recommendation}
            hasBlockingReviewFindings={hasBlockingFindings}
          />
        )}
      </main>
    </div>
  );
}
