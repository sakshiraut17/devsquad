"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  FileCode2,
  ListOrdered,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Target,
  FlaskConical,
  HelpCircle,
} from "lucide-react";
import { StructuredPlan, EvidenceReference } from "@/types";
import { truncateHash } from "@/lib/utils";

interface GroundedPlanCardProps {
  plan: StructuredPlan | null | undefined;
}

export function GroundedPlanCard({ plan }: GroundedPlanCardProps) {
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});

  if (!plan) {
    return (
      <div className="p-5 rounded-lg bg-surface border border-border-subtle text-xs font-mono text-text-muted">
        Planner agent has not synthesized an engineering plan for this execution yet.
      </div>
    );
  }

  const toggleCitation = (idx: number) => {
    setExpandedCitations((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const isVerified = Boolean(plan.is_verified);
  const citations = plan.evidence_citations || [];

  return (
    <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
      {/* Header with Verification Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <ListOrdered className="w-4 h-4 text-ultraviolet" />
          <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            Structured Engineering Plan
          </h3>
        </div>

        {isVerified ? (
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-semantic-success/15 border border-semantic-success/40 text-semantic-success text-[11px] font-bold">
            <ShieldCheck className="w-3.5 h-3.5" />
            Evidence-Grounded &amp; Cryptographically Verified
          </div>
        ) : (
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-[11px] font-bold">
            <ShieldAlert className="w-3.5 h-3.5" />
            Unverified Evidence / Pending Verification
          </div>
        )}
      </div>

      {/* Plan Objective & Root Cause */}
      <div className="space-y-3">
        <div>
          <span className="text-[11px] text-text-muted uppercase tracking-wider block mb-1">
            Objective:
          </span>
          <p className="text-xs text-text-primary font-semibold leading-relaxed bg-surface-elevated p-2.5 rounded border border-border-subtle">
            {plan.objective}
          </p>
        </div>

        {plan.problem_interpretation && (
          <div>
            <span className="text-[11px] text-text-muted uppercase tracking-wider block mb-1">
              Problem Interpretation:
            </span>
            <p className="text-xs text-text-secondary leading-relaxed bg-surface-elevated/60 p-2.5 rounded border border-border-subtle">
              {plan.problem_interpretation}
            </p>
          </div>
        )}

        {plan.root_cause_hypothesis && (
          <div>
            <span className="text-[11px] text-forge-lime uppercase tracking-wider block mb-1 font-bold">
              Root Cause Hypothesis:
            </span>
            <p className="text-xs text-text-primary leading-relaxed bg-[#0E1114] p-2.5 rounded border border-border-subtle">
              {plan.root_cause_hypothesis}
            </p>
          </div>
        )}
      </div>

      {/* Verified Evidence Citations */}
      <div className="space-y-2 pt-2 border-t border-border-subtle">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-1.5">
            <FileCode2 className="w-3.5 h-3.5 text-cyan-ice" />
            Line-Span Evidence Citations ({citations.length})
          </span>
        </div>

        {citations.length === 0 ? (
          <div className="p-3 rounded bg-surface-elevated text-xs text-text-muted border border-border-subtle">
            No source code citations attached to this plan.
          </div>
        ) : (
          <div className="space-y-2">
            {citations.map((cite, idx) => {
              const isExpanded = expandedCitations[idx] ?? true;
              return (
                <div
                  key={idx}
                  className="rounded border border-border-subtle bg-surface-elevated text-xs overflow-hidden"
                >
                  <div
                    onClick={() => toggleCitation(idx)}
                    className="p-2.5 flex items-center justify-between cursor-pointer hover:bg-surface-hover transition-colors"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-forge-lime">{cite.file_path}</span>
                      <span className="px-1.5 py-0.2 rounded bg-background border border-border-subtle text-[10px] text-cyan-ice">
                        L{cite.start_line}–L{cite.end_line}
                      </span>
                      <span className="px-1.5 py-0.2 rounded bg-background border border-border-subtle text-[10px] text-text-muted uppercase">
                        {cite.purpose}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="text-[10px] hidden sm:inline">
                        sha: {truncateHash(cite.file_sha256, 10)}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </div>
                  </div>

                  {isExpanded && cite.excerpt && (
                    <div className="p-3 bg-[#0B0D0F] border-t border-border-subtle">
                      <pre className="text-[11px] text-text-primary font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                        {cite.excerpt}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Target Files & Regression Test Strategy */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-border-subtle text-xs">
        <div className="space-y-1.5">
          <span className="text-[11px] text-text-muted uppercase tracking-wider flex items-center gap-1 font-bold">
            <Target className="w-3 h-3 text-forge-lime" /> Target Modification Files:
          </span>
          {plan.target_files && plan.target_files.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {plan.target_files.map((tf) => (
                <span
                  key={tf}
                  className="px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle text-text-primary text-[11px]"
                >
                  {tf}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-text-muted text-[11px]">No specific target files specified.</span>
          )}
        </div>

        <div className="space-y-1.5">
          <span className="text-[11px] text-text-muted uppercase tracking-wider flex items-center gap-1 font-bold">
            <FlaskConical className="w-3 h-3 text-cyan-ice" /> Regression Test Strategy:
          </span>
          {plan.regression_test_strategy && plan.regression_test_strategy.length > 0 ? (
            <ul className="list-disc list-inside text-text-secondary text-[11px] space-y-0.5">
              {plan.regression_test_strategy.map((strat, i) => (
                <li key={i}>{strat}</li>
              ))}
            </ul>
          ) : (
            <span className="text-text-muted text-[11px]">Standard test suite coverage.</span>
          )}
        </div>
      </div>

      {/* Sequential Implementation Steps */}
      {plan.steps && plan.steps.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-border-subtle">
          <span className="text-[11px] text-text-muted uppercase tracking-wider block font-bold">
            Sequential Engineering Steps ({plan.steps.length}):
          </span>
          <div className="space-y-1.5">
            {plan.steps.map((step, idx) => (
              <div
                key={step.id || idx}
                className="p-2.5 rounded bg-surface-elevated/70 border border-border-subtle text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-text-primary">
                    Step {idx + 1}: {step.description}
                  </span>
                  {step.target_files && step.target_files.length > 0 && (
                    <span className="text-[10px] text-forge-lime">
                      {step.target_files.join(", ")}
                    </span>
                  )}
                </div>
                {step.rationale && (
                  <p className="text-[11px] text-text-muted leading-snug">
                    Rationale: {step.rationale}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Context Requests or Decline Notices */}
      {plan.needs_additional_context && (
        <div className="p-3 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs flex items-start gap-2">
          <HelpCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">Additional Context Requested</p>
            <p className="text-[11px] text-text-secondary mt-0.5">
              {plan.additional_context_request || "Planner agent noted missing context for complete repair certainty."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
