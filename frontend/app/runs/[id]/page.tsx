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
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  XCircle,
  FileText,
  Terminal,
  Shield,
  Eye,
  Check,
  Loader2,
  ChevronRight,
  GitCommit,
  Sparkles,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { RunStageStepper } from "@/components/runs/RunStageStepper";
import { GroundedPlanCard } from "@/components/runs/GroundedPlanCard";
import { RepositoryContextCard } from "@/components/runs/RepositoryContextCard";
import { TestResultCard } from "@/components/runs/TestResultCard";
import { ReviewerCard } from "@/components/runs/ReviewerCard";
import { SecurityGuardianCard } from "@/components/runs/SecurityGuardianCard";
import { DiffViewer } from "@/components/patches/DiffViewer";
import { ApprovalModal } from "@/components/patches/ApprovalModal";
import { api } from "@/lib/api/client";
import {
  AgentEvent,
  ApprovalRecord,
  Issue,
  Patch,
  Run,
  SecurityScanResult,
  WorkflowStateSnapshot,
} from "@/types";
import { formatDate, truncateHash } from "@/lib/utils";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;

  const [run, setRun] = useState<Run | null>(null);
  const [issue, setIssue] = useState<Issue | null>(null);
  const [repo, setRepo] = useState<any | null>(null);
  const [stateSnapshot, setStateSnapshot] = useState<WorkflowStateSnapshot | null>(null);
  const [securityScan, setSecurityScan] = useState<SecurityScanResult | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [patches, setPatches] = useState<Patch[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [selectedPatch, setSelectedPatch] = useState<Patch | null>(null);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState(false);
  const [activeOutputTab, setActiveOutputTab] = useState<"plan" | "code" | "tests" | "review">("code");
  const [viewMode, setViewMode] = useState<"workflow" | "diagnostics">("workflow");
  const lastEventIdRef = useRef<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCommitting, setIsCommitting] = useState(false);
  const [isCreatingPR, setIsCreatingPR] = useState(false);
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);

  const loadRunData = async () => {
    if (!runId) return;
    setError(null);
    try {
      const [runData, stateData, eventsData, patchesData, approvalsData, securityData] =
        await Promise.all([
          api.getRun(runId),
          api.getRunState(runId),
          api.getRunEvents(runId),
          api.getRunPatches(runId),
          api.getRunApprovals(runId),
          api.getRunSecurity(runId).catch(() => null),
        ]);

      setRun(runData);
      setStateSnapshot(stateData);
      setEvents(eventsData);
      setPatches(patchesData);
      setApprovals(approvalsData);
      if (securityData) {
        setSecurityScan(securityData);
      }

      if (patchesData.length > 0 && !selectedPatch) {
        setSelectedPatch(patchesData[patchesData.length - 1]);
      }

      if (runData.repository_id) {
        try {
          const repoData = await api.getRepository(runData.repository_id);
          setRepo(repoData);
        } catch {
          // Fallback if repo not directly retrievable
        }
      }

      if (runData.issue_id) {
        try {
          const issueData = await api.getIssue(runData.issue_id);
          setIssue(issueData);
        } catch {
          // Fallback if issue not directly retrievable
        }
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load run details");
    } finally {
      setLoading(false);
    }
  };

  const handleCommitToMain = async () => {
    if (!selectedPatch || !run) return;
    setIsCommitting(true);
    setActionMessage(null);
    setError(null);
    try {
      const target = repo?.full_name || repo?.html_url || run.repository_id;
      const ghToken = typeof window !== "undefined" ? localStorage.getItem("devsquad_github_token") : null;
      const res = await api.createPullRequest({
        target,
        issue_number: issue?.github_issue_number,
        issue_title: issue?.title,
        code_patch: selectedPatch.unified_diff,
        commit_direct: true,
        token: ghToken || undefined,
      });
      setPublishedUrl(res.html_url || res.pr_url || null);
      setActionMessage(`Fix committed directly to main branch on GitHub! Verified code is live.`);
    } catch (err: any) {
      setError(err?.message || "Failed to commit fix directly to GitHub repository.");
    } finally {
      setIsCommitting(false);
    }
  };

  const handleCreatePR = async () => {
    if (!selectedPatch || !run) return;
    setIsCreatingPR(true);
    setActionMessage(null);
    setError(null);
    try {
      const target = repo?.full_name || repo?.html_url || run.repository_id;
      const ghToken = typeof window !== "undefined" ? localStorage.getItem("devsquad_github_token") : null;
      const res = await api.createPullRequest({
        target,
        issue_number: issue?.github_issue_number,
        issue_title: issue?.title,
        code_patch: selectedPatch.unified_diff,
        commit_direct: false,
        token: ghToken || undefined,
      });
      setPublishedUrl(res.html_url || res.pr_url || null);
      setActionMessage(`Pull Request #${res.pr_number || ""} created successfully!`);
    } catch (err: any) {
      setError(err?.message || "Failed to create Pull Request on GitHub repository.");
    } finally {
      setIsCreatingPR(false);
    }
  };

  useEffect(() => {
    loadRunData();

    if (!runId) return;

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

  // Compute stage statuses for the 6-stage vertical stepper
  const currentNode = run?.current_node?.toLowerCase() || "";
  const isRunDone = run?.status === "COMPLETED" || run?.status === "APPROVED" || run?.status === "AWAITING_APPROVAL";
  const isRunFailed = run?.status === "FAILED" || run?.status === "REJECTED";
  const errSummary = (run?.error_summary || "").toLowerCase();

  const hasPlan = Boolean(stateSnapshot?.state?.plan || patches.length > 0);
  const hasCode = Boolean(selectedPatch || latestPatch || patches.length > 0);

  // Identify which stage failed if isRunFailed
  let failedStageId: string | null = null;
  if (isRunFailed) {
    if (errSummary.includes("coder") || (!hasCode && hasPlan)) {
      failedStageId = "coding";
    } else if (errSummary.includes("planner") || (!hasPlan && !hasCode && (currentNode.includes("plan") || errSummary.includes("plan")))) {
      failedStageId = "planning";
    } else if (errSummary.includes("security")) {
      failedStageId = "security";
    } else if (errSummary.includes("test")) {
      failedStageId = "testing";
    } else if (errSummary.includes("review") || run?.status === "REJECTED") {
      failedStageId = "review";
    } else if (errSummary.includes("github") || errSummary.includes("credential") || errSummary.includes("validate_input") || errSummary.includes("context_preparation") || errSummary.includes("context ranker")) {
      failedStageId = "context";
    } else {
      failedStageId = "coding";
    }
  }

  const stageOrder = ["context", "planning", "coding", "security", "testing", "review"];
  const failedStageIdx = failedStageId ? stageOrder.indexOf(failedStageId) : -1;

  const rawSteps = [
    { id: "context", title: "Context Analysis", agent: "Context Ranker", tab: "plan" },
    { id: "planning", title: "Planning", agent: "Planner Agent", tab: "plan" },
    { id: "coding", title: "Code Generation", agent: "Coder Agent", tab: "code" },
    { id: "security", title: "Security Check", agent: "Security Guardian", tab: "review" },
    { id: "testing", title: "Testing", agent: "Tester Agent", tab: "tests" },
    { id: "review", title: "Review", agent: "Reviewer Agent", tab: "review" },
  ];

  const workflowSteps = rawSteps.map((step, idx) => {
    if (isRunDone) {
      return { ...step, isCompleted: true, isFailed: false, isInProgress: false, label: "Completed" };
    }
    if (isRunFailed) {
      if (idx < failedStageIdx) {
        return { ...step, isCompleted: true, isFailed: false, isInProgress: false, label: "Completed" };
      }
      if (idx === failedStageIdx) {
        return { ...step, isCompleted: false, isFailed: true, isInProgress: false, label: "Failed" };
      }
      return { ...step, isCompleted: false, isFailed: false, isInProgress: false, label: "Skipped" };
    }

    const isInProgress =
      (step.id === "context" && (currentNode.includes("context") || currentNode.includes("validate"))) ||
      (step.id === "planning" && currentNode.includes("plan")) ||
      (step.id === "coding" && (currentNode.includes("coder") || currentNode.includes("patch"))) ||
      (step.id === "security" && currentNode.includes("security")) ||
      (step.id === "testing" && currentNode.includes("test")) ||
      (step.id === "review" && (currentNode.includes("review") || currentNode.includes("approv") || currentNode.includes("gate")));

    const isCompleted =
      (step.id === "context" && !currentNode.includes("validate") && !currentNode.includes("context")) ||
      (step.id === "planning" && (hasPlan || currentNode.includes("coder") || currentNode.includes("security") || currentNode.includes("test") || currentNode.includes("review"))) ||
      (step.id === "coding" && (hasCode || currentNode.includes("security") || currentNode.includes("test") || currentNode.includes("review"))) ||
      (step.id === "security" && (currentNode.includes("test") || currentNode.includes("review"))) ||
      (step.id === "testing" && currentNode.includes("review")) ||
      (step.id === "review" && isRunDone);

    return {
      ...step,
      isCompleted,
      isFailed: false,
      isInProgress,
      label: isCompleted ? "Completed" : isInProgress ? "In Progress" : "Pending",
    };
  });

  // Calculate file additions/deletions for Files Changed card
  const diffLines = selectedPatch?.unified_diff ? selectedPatch.unified_diff.split("\n") : [];
  const additionsCount = diffLines.filter((l) => l.startsWith("+") && !l.startsWith("+++")).length;
  const deletionsCount = diffLines.filter((l) => l.startsWith("-") && !l.startsWith("---")).length;

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar
        onRefresh={loadRunData}
        title={`Workflow Execution: ${runId?.slice(0, 8)}…`}
        subtitle="Multi-Agent AI Engineering Platform"
      />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Navigation, Issue Banner & Mode Toggle */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-surface/50 p-4 rounded-2xl border border-border-subtle">
          <div className="flex items-center gap-3">
            <Link
              href="/runs"
              className="text-xs font-mono text-text-muted hover:text-text-primary flex items-center gap-1.5 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </Link>
            <div className="h-4 w-px bg-border-subtle" />
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <h1 className="text-sm sm:text-base font-bold text-text-primary font-mono truncate max-w-md">
                Issue: {issue?.title || `Runtime Defect in Repo ${run?.repository_id || "Target"}`}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 font-mono">
            {isLiveStreaming && (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-ice/10 text-cyan-ice border border-cyan-ice/30 text-[10px] font-bold animate-pulse">
                <Radio className="w-3 h-3 text-cyan-ice" /> Live
              </span>
            )}

            {run && <StatusBadge status={run.status} size="sm" />}

            {/* View Mode Toggle */}
            <div className="flex items-center bg-surface-elevated rounded-xl p-0.5 border border-border-subtle text-xs">
              <button
                type="button"
                onClick={() => setViewMode("workflow")}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  viewMode === "workflow"
                    ? "bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                Workflow View
              </button>
              <button
                type="button"
                onClick={() => setViewMode("diagnostics")}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  viewMode === "diagnostics"
                    ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                Raw Diagnostics
              </button>
            </div>

            {/* Primary Action Button: Review and Approve / Commit Fix / Approved Status */}
            {selectedPatch && (
              run?.status === "APPROVED" ? (
                <div className="flex items-center gap-2">
                  <div className="px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 flex items-center gap-1.5 font-mono shadow-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Approved
                  </div>
                  <button
                    type="button"
                    onClick={handleCommitToMain}
                    disabled={isCommitting || isCreatingPR}
                    className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-400 text-black flex items-center gap-1.5 transition-all shadow-md font-mono disabled:opacity-50"
                  >
                    {isCommitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitCommit className="w-3.5 h-3.5" />}
                    Commit Fix to main
                  </button>
                  <button
                    type="button"
                    onClick={handleCreatePR}
                    disabled={isCommitting || isCreatingPR}
                    className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-surface-elevated hover:bg-surface-hover text-cyan-300 border border-cyan-400/40 flex items-center gap-1.5 transition-all font-mono disabled:opacity-50"
                  >
                    {isCreatingPR ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                    Create PR
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsApprovalOpen(true)}
                  className="px-4 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-400 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 text-black flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/20"
                >
                  <ShieldCheck className="w-4 h-4" />
                  Review and Approve
                </button>
              )
            )}
          </div>
        </div>

        {publishedUrl && (
          <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono flex items-center justify-between">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Patch applied and committed to GitHub successfully!
            </span>
            <a
              href={publishedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-white font-bold ml-2"
            >
              View on GitHub →
            </a>
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-xl bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        {actionMessage && (
          <div className="p-3.5 rounded-xl bg-semantic-success/15 border border-semantic-success/30 text-semantic-success text-xs font-mono">
            {actionMessage}
          </div>
        )}

        {loading || !run ? (
          <div className="space-y-4">
            <div className="h-48 bg-surface animate-pulse rounded-2xl border border-border-subtle" />
            <div className="h-96 bg-surface animate-pulse rounded-2xl border border-border-subtle" />
          </div>
        ) : viewMode === "workflow" ? (
          /* ========================================================================= */
          /* INFOGRAPHIC WORKFLOW VIEW (SCREENSHOT 2: ISSUE DETAILS & WORKFLOW)         */
          /* ========================================================================= */
          <div className="space-y-6">
            {isRunFailed && run.error_summary && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-xs flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
                <div className="space-y-1">
                  <div className="font-bold uppercase tracking-wider text-rose-400 flex items-center gap-2">
                    <span>Execution Halted / Failure Reason</span>
                    {failedStageId && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 uppercase">
                        Failed at: {failedStageId}
                      </span>
                    )}
                  </div>
                  <div className="text-text-secondary text-xs leading-relaxed font-sans">
                    {run.error_summary}
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Timeline Stepper matching Screenshot 2 (4/12 cols) */}
            <div className="lg:col-span-4 p-5 rounded-2xl bg-surface border border-border-subtle space-y-4 shadow-sm">
              <div className="border-b border-border-subtle pb-3">
                <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center justify-between">
                  <span>Workflow Progress</span>
                  <span className="text-[10px] text-emerald-400">
                    {run.retry_count > 0 ? `Repairs: ${run.retry_count}/3` : "LangGraph StateGraph"}
                  </span>
                </h3>
                <p className="text-[11px] font-sans text-text-muted mt-0.5">
                  Autonomous agents collaborating in real time
                </p>
              </div>

              {/* Vertical Timeline */}
              <div className="space-y-4 relative pl-2">
                <div className="absolute left-[18px] top-3 bottom-3 w-0.5 bg-border-subtle -z-0" />

                {workflowSteps.map((step, idx) => {
                  return (
                    <div
                      key={step.id}
                      onClick={() => setActiveOutputTab(step.tab as any)}
                      className="flex items-center gap-3.5 group cursor-pointer relative z-10 select-none"
                    >
                      {/* Status Circle */}
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-mono font-bold border transition-all ${
                          step.isCompleted
                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/60 shadow-[0_0_8px_rgba(16,185,129,0.3)]"
                            : step.isFailed
                            ? "bg-rose-500/20 text-rose-400 border-rose-500/60 shadow-[0_0_8px_rgba(244,63,94,0.3)]"
                            : step.isInProgress
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 animate-pulse shadow-[0_0_10px_rgba(34,211,238,0.4)]"
                            : "bg-surface-elevated text-text-muted border-border-subtle"
                        }`}
                      >
                        {step.isCompleted ? (
                          <Check className="w-3.5 h-3.5 stroke-[3]" />
                        ) : step.isFailed ? (
                          <XCircle className="w-3.5 h-3.5 stroke-[2.5]" />
                        ) : step.isInProgress ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          idx + 1
                        )}
                      </div>

                      {/* Step Labels */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-xs font-mono font-bold transition-colors ${
                              step.isFailed
                                ? "text-rose-400"
                                : step.isInProgress
                                ? "text-cyan-300"
                                : step.isCompleted
                                ? "text-text-primary group-hover:text-emerald-400"
                                : "text-text-muted"
                            }`}
                          >
                            {step.title}
                          </span>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                              step.isCompleted
                                ? "bg-emerald-500/15 text-emerald-400"
                                : step.isFailed
                                ? "bg-rose-500/20 text-rose-400 font-bold border border-rose-500/30"
                                : step.isInProgress
                                ? "bg-cyan-500/15 text-cyan-300 font-bold animate-pulse"
                                : "text-text-muted bg-surface-elevated"
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                        <span className="text-[10px] font-sans text-text-muted block mt-0.5">
                          {step.agent}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Run Metrics Summary */}
              <div className="pt-3 border-t border-border-subtle text-[11px] font-mono text-text-muted space-y-1">
                <div className="flex justify-between">
                  <span>Started:</span>
                  <span className="text-text-secondary">{formatDate(run.started_at || run.created_at)}</span>
                </div>
                {run.finished_at && (
                  <div className="flex justify-between">
                    <span>Completed:</span>
                    <span className="text-text-secondary">{formatDate(run.finished_at)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Target Repository:</span>
                  <span className="text-cyan-400">{run.repository_id}</span>
                </div>
              </div>
            </div>

            {/* Right Column: Agent Output & Files Changed matching Screenshot 2 (8/12 cols) */}
            <div className="lg:col-span-8 space-y-6">
              {/* Top Card: Agent Output with Tabs [Plan], [Code], [Tests], [Review] */}
              <div className="rounded-2xl bg-surface border border-border-subtle overflow-hidden shadow-sm">
                {/* Card Header & Tabs */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between px-5 pt-4 pb-0 border-b border-border-subtle bg-surface/70 gap-3">
                  <div>
                    <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
                      Agent Output
                    </h3>
                    <p className="text-[11px] font-sans text-text-muted mt-0.5">
                      Inspect multi-agent synthesis, code generation, and verification
                    </p>
                  </div>

                  {/* Tabs: Plan, Code, Tests, Review */}
                  <div className="flex items-center gap-1 font-mono text-xs">
                    <button
                      type="button"
                      onClick={() => setActiveOutputTab("plan")}
                      className={`px-3.5 py-2 rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
                        activeOutputTab === "plan"
                          ? "border-emerald-400 text-emerald-400 bg-surface-elevated font-bold"
                          : "border-transparent text-text-muted hover:text-text-primary"
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" />
                      Plan
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveOutputTab("code")}
                      className={`px-3.5 py-2 rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
                        activeOutputTab === "code"
                          ? "border-cyan-400 text-cyan-400 bg-surface-elevated font-bold"
                          : "border-transparent text-text-muted hover:text-text-primary"
                      }`}
                    >
                      <FileCode2 className="w-3.5 h-3.5" />
                      Code
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveOutputTab("tests")}
                      className={`px-3.5 py-2 rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
                        activeOutputTab === "tests"
                          ? "border-lime-400 text-lime-400 bg-surface-elevated font-bold"
                          : "border-transparent text-text-muted hover:text-text-primary"
                      }`}
                    >
                      <Terminal className="w-3.5 h-3.5" />
                      Tests
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveOutputTab("review")}
                      className={`px-3.5 py-2 rounded-t-lg transition-all border-b-2 flex items-center gap-1.5 ${
                        activeOutputTab === "review"
                          ? "border-amber-400 text-amber-400 bg-surface-elevated font-bold"
                          : "border-transparent text-text-muted hover:text-text-primary"
                      }`}
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Review
                    </button>
                  </div>
                </div>

                {/* Tab Output Body */}
                <div className="p-5 font-mono">
                  {activeOutputTab === "plan" && (
                    <div className="space-y-4">
                      {stateSnapshot?.state?.plan ? (
                        <GroundedPlanCard plan={stateSnapshot.state.plan} />
                      ) : (
                        <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl">
                          Planning phase in progress or initializing.
                        </div>
                      )}
                    </div>
                  )}

                  {activeOutputTab === "code" && (
                    <div className="space-y-4">
                      {selectedPatch ? (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between text-xs text-text-muted p-2 rounded bg-surface-elevated border border-border-subtle">
                            <span className="font-semibold text-text-primary">
                              Revision #{selectedPatch.revision}: {selectedPatch.summary || "Synthesized Fix"}
                            </span>
                            <span className="text-forge-lime text-[11px]">
                              SHA-256: {truncateHash(selectedPatch.content_hash, 16)}
                            </span>
                          </div>
                          <DiffViewer
                            diff={selectedPatch.unified_diff}
                            filename={selectedPatch.target_files[0] || "patch.diff"}
                          />
                        </div>
                      ) : (
                        <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl">
                          Code patch will appear once Coder Agent completes synthesis.
                        </div>
                      )}
                    </div>
                  )}

                  {activeOutputTab === "tests" && (
                    <div className="space-y-4">
                      {stateSnapshot?.state?.test_result ? (
                        <TestResultCard
                          testResult={stateSnapshot.state.test_result}
                          validationStatus={selectedPatch?.validation_status}
                        />
                      ) : (
                        <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl">
                          Automated Sandbox & AST test results will display after execution.
                        </div>
                      )}
                    </div>
                  )}

                  {activeOutputTab === "review" && (
                    <div className="space-y-4">
                      {stateSnapshot?.state?.review && (
                        <ReviewerCard review={stateSnapshot.state.review} />
                      )}
                      <SecurityGuardianCard
                        security={securityScan || (stateSnapshot?.state?.security_result as any)}
                        isLoading={loading && !securityScan}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom Card: Files Changed matching Screenshot 2 */}
              <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-3 shadow-sm font-mono">
                <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                  <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                    <FileCode2 className="w-3.5 h-3.5 text-cyan-400" />
                    Files Changed ({selectedPatch?.target_files.length || 0})
                  </h3>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-emerald-400 font-bold">+{additionsCount}</span>
                    <span className="text-semantic-danger font-bold">-{deletionsCount}</span>
                  </div>
                </div>

                {selectedPatch?.target_files && selectedPatch.target_files.length > 0 ? (
                  <div className="space-y-2">
                    {selectedPatch.target_files.map((file, i) => (
                      <div
                        key={i}
                        onClick={() => setActiveOutputTab("code")}
                        className="flex items-center justify-between p-3 rounded-xl bg-surface-elevated/70 border border-border-subtle hover:border-cyan-400/50 cursor-pointer transition-colors"
                      >
                        <div className="flex items-center gap-2.5">
                          <FileText className="w-4 h-4 text-cyan-400" />
                          <span className="text-xs font-semibold text-text-primary">{file}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-bold text-[10px]">
                            +{additionsCount}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-semantic-danger/15 text-semantic-danger font-bold text-[10px]">
                            -{deletionsCount}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl">
                    No modified files detected yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        ) : (
          /* ========================================================================= */
          /* DETAILED DIAGNOSTICS VIEW (FULL SYSTEM & DATABASE LEVEL DEEP INSPECTION)  */
          /* ========================================================================= */
          <>
            {/* Run Lifecycle & Stepper Card */}
            <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-4">
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

            {/* AI Security Guardian Verification Gate */}
            <SecurityGuardianCard
              security={securityScan || (stateSnapshot?.state?.security_result as any)}
              isLoading={loading && !securityScan}
            />

            {/* Failed Patches & Anti-Repetition Registry History */}
            {stateSnapshot?.state?.failed_patch_registry && stateSnapshot.state.failed_patch_registry.length > 0 && (
              <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-3 font-mono">
                <div className="flex items-center gap-2 border-b border-border-subtle pb-2">
                  <RotateCcw className="w-4 h-4 text-amber-attention" />
                  <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                    Failed Patch Registry & Anti-Repetition History ({stateSnapshot.state.failed_patch_registry.length})
                  </h3>
                </div>
                <div className="space-y-2">
                  {stateSnapshot.state.failed_patch_registry.map((fp, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-surface-elevated border border-border-subtle text-xs space-y-1"
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
              <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-3 font-mono">
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-cyan-ice" />
                  LangGraph Checkpointer Snapshot
                </h3>
                <div className="text-xs bg-surface-elevated p-3.5 rounded-xl border border-border-subtle space-y-1.5">
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
              <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-3 font-mono">
                <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-attention" />
                  Human Approval Records ({approvals.length})
                </h3>
                {approvals.length === 0 ? (
                  <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl border border-border-subtle">
                    No approval decisions recorded yet for this workflow execution.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {approvals.map((appr) => (
                      <div
                        key={appr.id}
                        className="p-3 rounded-xl bg-surface-elevated border border-border-subtle text-xs space-y-1"
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

            {/* Sanitized Agent Events Log */}
            <div className="p-5 rounded-2xl bg-surface border border-border-subtle space-y-4 font-mono">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-cyan-ice" />
                Chronological Sanitized Agent Events ({events.length})
              </h3>

              {events.length === 0 ? (
                <div className="p-6 text-center text-xs text-text-muted bg-surface-elevated/40 rounded-xl border border-border-subtle">
                  No agent events recorded yet.
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {events.map((ev) => {
                    return (
                      <div
                        key={ev.id}
                        className="p-3 rounded-xl bg-surface-elevated/60 border border-border-subtle text-xs flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-text-primary uppercase text-[11px]">
                              {ev.agent_name}
                            </span>
                            <span className="text-[10px] text-text-muted">
                              {ev.event_type}
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
            securityGateStatus={securityScan?.status || (stateSnapshot?.state?.security_result as any)?.status}
            securityBlockReasons={securityScan?.block_reasons || (stateSnapshot?.state?.security_result as any)?.block_reasons || []}
            testOutput={stateSnapshot?.state?.test_result?.stdout}
          />
        )}
      </main>
    </div>
  );
}