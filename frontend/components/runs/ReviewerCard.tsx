"use client";

import React from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertOctagon,
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { ReviewResponse, ReviewFinding } from "@/types";

interface ReviewerCardProps {
  review: ReviewResponse | null | undefined;
}

export function ReviewerCard({ review }: ReviewerCardProps) {
  if (!review) {
    return (
      <div className="p-5 rounded-lg bg-surface border border-border-subtle text-xs font-mono text-text-muted">
        Reviewer agent has not conducted risk analysis on this execution yet.
      </div>
    );
  }

  const rec = String(review.recommendation || "").toLowerCase();
  const isApproved = rec === "approve";
  const isReject = rec === "reject";
  const isChanges = rec === "request_changes";

  const findings = review.findings || [];
  const risks = review.unresolved_risks || [];

  return (
    <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
      {/* Header & Recommendation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-amber-attention" />
          <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            Reviewer Agent Evaluation &amp; Risk Audit
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {isApproved ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-semantic-success/15 border border-semantic-success/40 text-semantic-success text-[11px] font-bold uppercase">
              <CheckCircle2 className="w-3.5 h-3.5" /> Recommendation: Approve
            </span>
          ) : isReject ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-semantic-danger/15 border border-semantic-danger/40 text-semantic-danger text-[11px] font-bold uppercase">
              <AlertOctagon className="w-3.5 h-3.5" /> Recommendation: Reject (Blocking)
            </span>
          ) : isChanges ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-[11px] font-bold uppercase">
              <AlertTriangle className="w-3.5 h-3.5" /> Recommendation: Request Changes
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-text-muted text-[11px] uppercase">
              {review.recommendation}
            </span>
          )}

          <span
            className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold ${
              review.acceptance_criteria_met
                ? "bg-semantic-success/10 border-semantic-success/30 text-semantic-success"
                : "bg-semantic-danger/10 border-semantic-danger/30 text-semantic-danger"
            }`}
          >
            {review.acceptance_criteria_met ? "Criteria Met" : "Criteria Unmet"}
          </span>
        </div>
      </div>

      {/* Review Findings List */}
      <div className="space-y-2">
        <span className="text-xs font-bold text-text-primary uppercase tracking-wider block">
          Audited Findings ({findings.length}):
        </span>

        {findings.length === 0 ? (
          <div className="p-3 rounded bg-surface-elevated text-xs text-semantic-success border border-border-subtle flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Clean review audit. Zero blocking defects or security vulnerabilities identified.</span>
          </div>
        ) : (
          <div className="space-y-2">
            {findings.map((f, idx) => {
              const sev = String(f.severity || "info").toLowerCase();
              const isBlocking = sev === "blocking" || sev === "critical";
              const isWarn = sev === "warning";

              return (
                <div
                  key={idx}
                  className={`p-3 rounded border text-xs space-y-1.5 ${
                    isBlocking
                      ? "bg-semantic-danger/10 border-semantic-danger/30 text-semantic-danger"
                      : isWarn
                      ? "bg-amber-attention/10 border-amber-attention/30 text-amber-attention"
                      : "bg-surface-elevated border-border-subtle text-text-primary"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isBlocking ? (
                        <AlertOctagon className="w-3.5 h-3.5 text-semantic-danger shrink-0" />
                      ) : isWarn ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-attention shrink-0" />
                      ) : (
                        <Info className="w-3.5 h-3.5 text-cyan-ice shrink-0" />
                      )}
                      <span className="font-bold uppercase text-[10px]">
                        [{f.severity}]
                      </span>
                      <span className="text-text-primary font-semibold">
                        {f.file_path} {f.line_number ? `(line ${f.line_number})` : ""}
                      </span>
                    </div>
                  </div>

                  <p className="text-text-secondary text-[11px] leading-relaxed">
                    {f.description}
                  </p>

                  {f.suggested_fix && (
                    <div className="text-[10px] text-forge-lime bg-[#0B0D0F] p-2 rounded border border-border-subtle font-mono">
                      Suggested Fix: {f.suggested_fix}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Unresolved Risks */}
      {risks.length > 0 && (
        <div className="p-3 rounded bg-[#0E1114] border border-border-subtle text-xs space-y-1.5">
          <span className="text-[11px] text-amber-attention font-bold uppercase tracking-wider block">
            Unresolved Architectural / Operational Risks:
          </span>
          <ul className="list-disc list-inside text-text-secondary text-[11px] space-y-0.5">
            {risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
