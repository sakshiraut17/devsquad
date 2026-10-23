"use client";

import React, { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Loader2 } from "lucide-react";
import { Patch, Run } from "@/types";
import { api, ApiError } from "@/lib/api/client";

interface ApprovalModalProps {
  run: Run;
  patch: Patch;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  baseCommitSha?: string;
  reviewerRecommendation?: string;
  hasBlockingReviewFindings?: boolean;
  securityGateStatus?: "PASSED" | "BLOCKED" | "UNVERIFIED";
  securityBlockReasons?: string[];
}

export function ApprovalModal({
  run,
  patch,
  isOpen,
  onClose,
  onSuccess,
  baseCommitSha,
  reviewerRecommendation,
  hasBlockingReviewFindings = false,
  securityGateStatus,
  securityBlockReasons = [],
}: ApprovalModalProps) {
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [feedback, setFeedback] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const isAwaiting = run.status === "AWAITING_APPROVAL";
  const isExecutionVerified =
    patch.validation_status === "passed" ||
    patch.validation_status === "TESTS_PASSED" ||
    patch.validation_status === "VALIDATED";
  const isStaticOnly =
    patch.validation_status === "ast_fallback" ||
    patch.validation_status === "sandbox_unavailable" ||
    patch.validation_status === "partial_validation" ||
    patch.validation_status === "PARTIAL_VALIDATION" ||
    patch.validation_status === "SANDBOX_UNAVAILABLE";

  const isReviewBlocking =
    hasBlockingReviewFindings ||
    String(reviewerRecommendation || "").toLowerCase() === "reject";

  const isSecurityBlocked =
    securityGateStatus !== undefined && securityGateStatus !== "PASSED";

  const canApprove =
    isAwaiting && isExecutionVerified && !isReviewBlocking && !isSecurityBlocked;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmed && decision === "approved") {
      setErrorMessage("You must explicitly confirm SHA-256 hash inspection before approving.");
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      await api.approveRun(run.id, {
        patch_id: patch.id,
        decision,
        patch_hash: patch.content_hash,
        base_commit_sha: baseCommitSha,
        feedback: feedback.trim() || undefined,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMessage(`Backend rejected approval (${err.status}): ${err.message}`);
      } else {
        setErrorMessage(err?.message || "Failed to record approval decision.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
      <div className="bg-surface border border-border-subtle rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 font-mono">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2 text-text-primary font-bold text-sm">
            <ShieldCheck className="w-5 h-5 text-forge-lime" />
            <span>Human Approval Gatekeeper</span>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-sm"
          >
            ✕
          </button>
        </div>

        {/* Prominent Static Validation Warning when applicable */}
        {isStaticOnly && (
          <div className="p-3.5 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs font-mono flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">STATIC VALIDATION ONLY — EXECUTION NOT VERIFIED</p>
              <p className="text-[11px] mt-0.5 text-text-secondary">
                Container sandbox was unavailable; only AST syntax parsing was performed. Execution cannot be certified as passing.
              </p>
            </div>
          </div>
        )}

        {/* Policy Verification Warning */}
        {decision === "approved" && !canApprove && (
          <div className="p-3 rounded bg-semantic-danger/15 border border-semantic-danger/30 text-semantic-danger text-xs font-mono flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Approval Policy Disallowed:</p>
              <p className="text-[11px] text-text-secondary mt-0.5">
                {isSecurityBlocked
                  ? `Security Guardian gate is ${securityGateStatus || "BLOCKED"}: ${
                      securityBlockReasons.length > 0
                        ? securityBlockReasons.join("; ")
                        : "Mandatory security evaluation failed or contains active blockers."
                    }`
                  : run.status !== "AWAITING_APPROVAL"
                  ? `Run status is '${run.status}', not 'AWAITING_APPROVAL'.`
                  : isReviewBlocking
                  ? `Reviewer recommended rejection or identified blocking findings.`
                  : `Patch validation status is '${patch.validation_status}', not passing tests.`}
              </p>
            </div>
          </div>
        )}

        {/* Patch Verification Metadata */}
        <div className="space-y-2 text-xs bg-surface-elevated p-3.5 rounded border border-border-subtle">
          <div className="flex justify-between">
            <span className="text-text-muted">Workflow Run ID:</span>
            <span className="text-text-primary">{run.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Patch Revision:</span>
            <span className="text-forge-lime font-bold">rev #{patch.revision}</span>
          </div>
          {baseCommitSha && (
            <div className="flex justify-between">
              <span className="text-text-muted">Base Commit SHA:</span>
              <span className="text-text-primary text-[11px] font-mono">{baseCommitSha}</span>
            </div>
          )}
          <div className="flex flex-col gap-1 pt-1.5 border-t border-border-subtle">
            <span className="text-text-muted">Canonical SHA-256 Content Hash:</span>
            <span className="text-forge-lime break-all bg-background p-1.5 rounded text-[11px] border border-border-subtle">
              {patch.content_hash}
            </span>
          </div>
          <div className="flex justify-between pt-1.5 border-t border-border-subtle">
            <span className="text-text-muted">Test Execution Evidence:</span>
            <span className={patch.validation_status === "passed" ? "text-semantic-success font-bold uppercase" : "text-amber-attention uppercase"}>
              {patch.validation_status}
            </span>
          </div>
          {securityGateStatus && (
            <div className="flex justify-between pt-1.5 border-t border-border-subtle">
              <span className="text-text-muted">Security Guardian Gate:</span>
              <span className={securityGateStatus === "PASSED" ? "text-semantic-success font-bold uppercase" : "text-semantic-danger font-bold uppercase"}>
                {securityGateStatus}
              </span>
            </div>
          )}
        </div>

        {/* Form Controls */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">
              Decision
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled={!canApprove}
                onClick={() => setDecision("approved")}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs transition-all ${
                  decision === "approved"
                    ? "bg-forge-lime/15 border-forge-lime text-forge-lime font-bold"
                    : "bg-surface-elevated border-border-subtle text-text-muted hover:bg-surface-hover"
                } disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                <CheckCircle2 className="w-4 h-4 text-forge-lime" />
                Approve Patch
              </button>
              <button
                type="button"
                onClick={() => setDecision("rejected")}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs transition-all ${
                  decision === "rejected"
                    ? "bg-semantic-danger/15 border-semantic-danger text-semantic-danger font-bold"
                    : "bg-surface-elevated border-border-subtle text-text-muted hover:bg-surface-hover"
                }`}
              >
                <XCircle className="w-4 h-4 text-semantic-danger" />
                Reject Patch
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Maintainer Feedback / Audit Log
            </label>
            <textarea
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Verified discount logic and edge cases..."
              className="w-full text-xs font-mono bg-surface-elevated border border-border-subtle rounded p-2 text-text-primary placeholder-text-muted focus:outline-none focus:border-forge-lime"
            />
          </div>

          {/* Explicit Confirmation Checkbox */}
          {decision === "approved" && (
            <label className="flex items-start gap-2 cursor-pointer text-xs text-text-secondary select-none">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 rounded border-border-subtle bg-surface-elevated text-forge-lime focus:ring-0"
              />
              <span>
                I confirm that I have reviewed the patch diff, verified the canonical SHA-256 hash, and checked test execution results.
              </span>
            </label>
          )}

          {errorMessage && (
            <div className="p-2.5 rounded bg-semantic-danger/15 border border-semantic-danger/30 text-semantic-danger text-xs">
              {errorMessage}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-border-subtle">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded text-xs text-text-muted hover:text-text-primary hover:bg-surface-elevated transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || (decision === "approved" && (!canApprove || !confirmed))}
              className="flex items-center gap-2 px-4 py-2 rounded text-xs font-bold bg-forge-lime hover:bg-forge-lime/90 text-black transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-[0_0_8px_rgba(215,255,100,0.3)]"
            >
              {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Submit Decision
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
