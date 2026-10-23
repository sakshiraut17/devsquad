"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  Lock,
  KeyRound,
  FileCode2,
  Package,
  History,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { SecurityScanResult, SecurityFinding, SecuritySeverity } from "@/types";

interface SecurityGuardianCardProps {
  security: SecurityScanResult | null | undefined;
  isLoading?: boolean;
}

export function SecurityGuardianCard({ security, isLoading }: SecurityGuardianCardProps) {
  const [expandedFindings, setExpandedFindings] = useState<Record<string, boolean>>({});

  if (isLoading) {
    return (
      <div className="p-5 rounded-lg bg-surface border border-border-subtle animate-pulse space-y-3 font-mono">
        <div className="h-4 w-48 bg-surface-elevated rounded"></div>
        <div className="h-16 w-full bg-surface-elevated rounded"></div>
      </div>
    );
  }

  if (!security || security.status === "UNVERIFIED") {
    return (
      <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-2 font-mono">
        <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
          <ShieldAlert className="w-4 h-4 text-amber-attention" />
          <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            AI Security Guardian Gate
          </h3>
          <span className="ml-auto inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-surface-elevated border border-border-subtle text-amber-attention text-[11px] font-bold uppercase">
            Awaiting Verification
          </span>
        </div>
        <p className="text-xs text-text-muted">
          Mandatory security evaluation has not yet executed for this run revision. Patches remain strictly fail-closed until certified by all security scanners.
        </p>
      </div>
    );
  }

  const isPassed = security.status === "PASSED" && security.can_approve;
  const isBlocked = security.status === "BLOCKED" || !security.can_approve;
  const findings = security.findings || [];
  const blockReasons = security.block_reasons || [];

  const criticalCount = security.critical_count ?? security.summary?.critical ?? 0;
  const highCount = security.high_count ?? security.summary?.high ?? 0;
  const mediumCount = security.medium_count ?? security.summary?.medium ?? 0;
  const lowCount = security.low_count ?? security.summary?.low ?? 0;

  const toggleFinding = (id: string) => {
    setExpandedFindings((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "secret_exposure":
        return <KeyRound className="w-3.5 h-3.5 text-semantic-danger" />;
      case "source_vulnerability":
        return <FileCode2 className="w-3.5 h-3.5 text-amber-attention" />;
      case "dependency_audit":
        return <Package className="w-3.5 h-3.5 text-blue-400" />;
      case "security_regression":
      case "patch_scope":
        return <History className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <Lock className="w-3.5 h-3.5 text-text-muted" />;
    }
  };

  const getSeverityBadge = (severity: SecuritySeverity) => {
    switch (severity) {
      case "CRITICAL":
        return (
          <span className="px-2 py-0.5 rounded bg-semantic-danger/20 border border-semantic-danger/50 text-semantic-danger text-[10px] font-bold">
            CRITICAL
          </span>
        );
      case "HIGH":
        return (
          <span className="px-2 py-0.5 rounded bg-orange-500/20 border border-orange-500/50 text-orange-400 text-[10px] font-bold">
            HIGH
          </span>
        );
      case "MEDIUM":
        return (
          <span className="px-2 py-0.5 rounded bg-amber-attention/20 border border-amber-attention/50 text-amber-attention text-[10px] font-bold">
            MEDIUM
          </span>
        );
      case "LOW":
        return (
          <span className="px-2 py-0.5 rounded bg-blue-500/20 border border-blue-500/50 text-blue-400 text-[10px] font-bold">
            LOW
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded bg-surface-elevated border border-border-subtle text-text-muted text-[10px] font-bold">
            INFO
          </span>
        );
    }
  };

  return (
    <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
      {/* Header & Gate Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2.5">
          {isPassed ? (
            <ShieldCheck className="w-5 h-5 text-forge-lime" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-semantic-danger" />
          )}
          <div>
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
              AI Security Guardian Gate
            </h3>
            <p className="text-[11px] text-text-muted">
              Deterministic secrets, AST static analysis, dependency auditor &amp; anti-tamper controls
            </p>
          </div>
        </div>

        <div>
          {isPassed ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-semantic-success/15 border border-semantic-success/40 text-semantic-success text-[11px] font-bold uppercase">
              <CheckCircle2 className="w-3.5 h-3.5" /> Gate Passed — Certified For Approval
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-semantic-danger/15 border border-semantic-danger/40 text-semantic-danger text-[11px] font-bold uppercase">
              <AlertOctagon className="w-3.5 h-3.5" /> Gate Blocked — Approval Prohibited
            </span>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex flex-col">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Critical Blockers</span>
          <span className={`text-base font-bold ${criticalCount > 0 ? "text-semantic-danger" : "text-text-primary"}`}>
            {criticalCount}
          </span>
        </div>
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex flex-col">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">High Severity</span>
          <span className={`text-base font-bold ${highCount > 0 ? "text-orange-400" : "text-text-primary"}`}>
            {highCount}
          </span>
        </div>
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex flex-col">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Medium Risks</span>
          <span className={`text-base font-bold ${mediumCount > 0 ? "text-amber-attention" : "text-text-primary"}`}>
            {mediumCount}
          </span>
        </div>
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle flex flex-col">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Low / Info</span>
          <span className="text-base font-bold text-text-muted">
            {lowCount}
          </span>
        </div>
      </div>

      {/* Scanners Executed */}
      {security.scanners_executed && security.scanners_executed.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[10px] text-text-muted uppercase">Scanners:</span>
          {security.scanners_executed.map((s) => (
            <span
              key={s}
              className="px-2 py-0.5 rounded text-[10px] bg-surface-elevated border border-border-subtle text-text-muted"
            >
              {s}
            </span>
          ))}
          {security.duration_ms !== undefined && (
            <span className="ml-auto text-[10px] text-text-muted">
              Scan time: {security.duration_ms}ms
            </span>
          )}
        </div>
      )}

      {/* Block Reasons Callout Banner */}
      {isBlocked && blockReasons.length > 0 && (
        <div className="p-3 rounded bg-semantic-danger/10 border border-semantic-danger/30 space-y-1.5">
          <div className="flex items-center gap-1.5 text-semantic-danger text-[11px] font-bold uppercase">
            <AlertTriangle className="w-3.5 h-3.5" />
            Approval Gate Blocked By Security Guardian
          </div>
          <ul className="text-xs text-text-primary space-y-1 list-disc list-inside">
            {blockReasons.map((reason, idx) => (
              <li key={idx} className="text-semantic-danger/90">
                {reason}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-text-muted pt-1">
            Human approval endpoint will fail-closed (HTTP 409) until the coder agent repairs these issues or generates a compliant revision.
          </p>
        </div>
      )}

      {/* Clean Certified State */}
      {isPassed && findings.length === 0 && (
        <div className="p-3.5 rounded bg-semantic-success/10 border border-semantic-success/25 flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-semantic-success flex-shrink-0" />
          <div className="text-xs text-semantic-success">
            Zero security regressions, exposed secrets, or critical vulnerabilities detected. Patch revision is certified safe for human approval.
          </div>
        </div>
      )}

      {/* Findings List */}
      {findings.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-border-subtle">
          <div className="flex items-center justify-between">
            <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-wider">
              Security Findings ({findings.length})
            </h4>
            <span className="text-[10px] text-text-muted">
              Click finding to inspect evidence &amp; remediation
            </span>
          </div>

          <div className="space-y-1.5">
            {findings.map((f, index) => {
              const findingId = f.id || `f-${index}`;
              const isExpanded = !!expandedFindings[findingId];

              return (
                <div
                  key={findingId}
                  className={`rounded border text-xs transition-colors ${
                    f.is_blocking
                      ? "border-semantic-danger/30 bg-semantic-danger/5 hover:border-semantic-danger/50"
                      : "border-border-subtle bg-surface-elevated/40 hover:border-border-muted"
                  }`}
                >
                  <button
                    onClick={() => toggleFinding(findingId)}
                    className="w-full text-left p-2.5 flex items-start gap-2.5 focus:outline-none"
                  >
                    <div className="mt-0.5">{getCategoryIcon(f.category)}</div>

                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        {getSeverityBadge(f.severity)}
                        <span className="font-bold text-text-primary truncate">
                          {f.title}
                        </span>
                        <span className="text-[10px] text-text-muted font-mono">
                          [{f.rule_id}]
                        </span>
                        {f.is_blocking && (
                          <span className="text-[10px] text-semantic-danger font-bold uppercase tracking-wider">
                            BLOCKING
                          </span>
                        )}
                      </div>

                      {f.file_path && (
                        <div className="text-[11px] text-text-muted pt-0.5">
                          {f.file_path}
                          {f.line_start ? `:L${f.line_start}` : ""}
                        </div>
                      )}
                    </div>

                    <div className="text-text-muted">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="px-3 pb-3 pt-1 border-t border-border-subtle space-y-2 text-xs">
                      <div>
                        <span className="text-[10px] text-text-muted uppercase font-bold">
                          Description:
                        </span>
                        <p className="text-text-primary pt-0.5">{f.description}</p>
                      </div>

                      {f.evidence_redacted && (
                        <div>
                          <span className="text-[10px] text-text-muted uppercase font-bold">
                            Evidence Snippet (Redacted):
                          </span>
                          <pre className="mt-1 p-2 rounded bg-black/40 border border-border-subtle text-[11px] overflow-x-auto text-amber-attention whitespace-pre-wrap font-mono">
                            {f.evidence_redacted}
                          </pre>
                        </div>
                      )}

                      {f.remediation && (
                        <div>
                          <span className="text-[10px] text-text-muted uppercase font-bold">
                            Remediation Guidance:
                          </span>
                          <p className="text-semantic-success text-[11px] pt-0.5">
                            {f.remediation}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center gap-3 text-[10px] text-text-muted pt-1 border-t border-border-subtle/50">
                        <span>Scanner: {f.scanner_name}</span>
                        <span>Confidence: {f.confidence}</span>
                        {f.advisory_id && <span>Advisory: {f.advisory_id}</span>}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
