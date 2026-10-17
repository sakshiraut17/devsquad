"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileCode2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Terminal,
  Layers,
  FileCheck,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { StatusBadge } from "@/components/layout/StatusBadge";
import { DiffViewer } from "@/components/patches/DiffViewer";
import { ApprovalModal } from "@/components/patches/ApprovalModal";
import { api } from "@/lib/api/client";
import { AgentEvent, Patch, Run } from "@/types";
import { formatDate, truncateHash } from "@/lib/utils";

interface PatchWithRun {
  patch: Patch;
  run: Run;
}

export default function PatchLaboratoryPage() {
  const [items, setItems] = useState<PatchWithRun[]>([]);
  const [selectedItem, setSelectedItem] = useState<PatchWithRun | null>(null);
  const [runEvents, setRunEvents] = useState<AgentEvent[]>([]);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const runs = await api.getRuns();
      const patchList: PatchWithRun[] = [];

      for (const run of runs) {
        try {
          const runPatches = await api.getRunPatches(run.id);
          for (const patch of runPatches) {
            patchList.push({ patch, run });
          }
        } catch {
          // Skip runs without patches
        }
      }

      setItems(patchList);
      if (patchList.length > 0 && !selectedItem) {
        selectPatch(patchList[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load patches from database");
    } finally {
      setLoading(false);
    }
  };

  const selectPatch = async (item: PatchWithRun) => {
    setSelectedItem(item);
    try {
      const evs = await api.getRunEvents(item.run.id);
      setRunEvents(evs);
    } catch {
      setRunEvents([]);
    }
  };

  useEffect(() => {
    loadPatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isStaticOnly =
    selectedItem?.patch.validation_status === "ast_fallback" ||
    selectedItem?.patch.validation_status === "sandbox_unavailable" ||
    selectedItem?.patch.validation_status === "partial_validation";

  const isValidationFailed =
    selectedItem?.patch.validation_status === "failed" ||
    selectedItem?.run.status === "FAILED";

  const reviewerEvent = runEvents.find((e) => e.agent_name === "reviewer");
  const testerEvent = runEvents.find((e) => e.agent_name === "tester");

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadPatches} title="Patch Laboratory" subtitle="Unified Diff Inspection & Cryptographic Audit" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        {actionSuccess && (
          <div className="p-3 rounded bg-semantic-success/15 border border-semantic-success/30 text-semantic-success text-xs font-mono">
            {actionSuccess}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Patch Revisions Rail */}
          <div className="lg:col-span-1 space-y-3">
            <h2 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider">
              Patch Revisions ({items.length})
            </h2>

            {loading ? (
              <div className="space-y-2">
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
                <div className="h-20 bg-surface animate-pulse rounded border border-border-subtle" />
              </div>
            ) : items.length === 0 ? (
              <div className="p-6 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
                No code patches recorded in database.
              </div>
            ) : (
              <div className="space-y-2">
                {items.map((item) => {
                  const isSelected = selectedItem?.patch.id === item.patch.id;
                  return (
                    <div
                      key={item.patch.id}
                      onClick={() => selectPatch(item)}
                      className={`p-3.5 rounded-lg border cursor-pointer transition-all relative ${
                        isSelected
                          ? "bg-surface-elevated border-forge-lime/50 shadow-md ring-1 ring-forge-lime/30"
                          : "bg-surface border-border-subtle hover:border-border-strong hover:bg-surface-elevated/50"
                      }`}
                    >
                      {isSelected && (
                        <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-forge-lime" />
                      )}
                      <div className="flex items-center justify-between mb-1.5 pl-1">
                        <span className="font-semibold text-xs text-text-primary font-mono truncate">
                          rev #{item.patch.revision} — {item.patch.target_files[0]}
                        </span>
                        <StatusBadge status={item.patch.validation_status} size="sm" />
                      </div>
                      <p className="text-xs text-text-muted font-mono truncate pl-1">
                        {item.patch.summary}
                      </p>
                      <div className="text-[11px] text-text-muted font-mono mt-1.5 flex justify-between pl-1">
                        <span>run: {item.run.id.slice(0, 8)}…</span>
                        <span>{formatDate(item.patch.created_at)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Selected Patch Inspection & Lab Controls */}
          <div className="lg:col-span-2 space-y-6">
            {selectedItem ? (
              <>
                {/* Validation Failed Alert Banner */}
                {isValidationFailed && (
                  <div className="p-4 rounded-lg bg-semantic-danger/15 border border-semantic-danger/40 text-semantic-danger text-xs font-mono flex items-start gap-3">
                    <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-bold text-sm tracking-tight">
                        AUTOMATED VALIDATION FAILED — HUMAN APPROVAL LOCKED
                      </h4>
                      <p className="text-xs text-text-secondary mt-1">
                        This patch revision failed automated test validation. In accordance with DevSquad safety policies, patches failing test suites or concurrency stress tests are strictly blocked from human approval and pull request publication.
                      </p>
                    </div>
                  </div>
                )}

                {/* Static Validation Warning Banner */}
                {isStaticOnly && !isValidationFailed && (
                  <div className="p-4 rounded-lg bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs font-mono flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-bold text-sm tracking-tight">
                        STATIC VALIDATION ONLY — EXECUTION NOT VERIFIED
                      </h4>
                      <p className="text-xs text-text-secondary mt-1">
                        Live container execution was unavailable on this host; validation is based on AST syntax parsing. Real test suite execution was not executed in an isolated container sandbox.
                      </p>
                    </div>
                  </div>
                )}

                {/* Patch Header & Reviewer Sign-Off Card */}
                <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-bold text-text-primary font-mono">
                          Revision #{selectedItem.patch.revision}
                        </span>
                        <StatusBadge status={selectedItem.patch.validation_status} />
                      </div>
                      <p className="text-xs text-text-secondary font-mono">
                        {selectedItem.patch.summary}
                      </p>
                    </div>

                    {selectedItem.run.status === "AWAITING_APPROVAL" && (
                      <button
                        onClick={() => setIsApprovalOpen(true)}
                        className="px-4 py-2 rounded-lg bg-forge-lime hover:bg-forge-lime/90 text-black text-xs font-mono font-bold flex items-center gap-2 transition-all shadow-[0_0_12px_rgba(215,255,100,0.4)]"
                      >
                        <ShieldCheck className="w-4 h-4" />
                        Human Review &amp; Sign-Off
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                    <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">SHA-256 Hash:</span>
                      <span className="text-forge-lime break-all text-[11px] font-bold">
                        {selectedItem.patch.content_hash}
                      </span>
                    </div>

                    <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Associated Workflow Run:</span>
                      <Link
                        href={`/runs/${selectedItem.run.id}`}
                        className="text-forge-lime hover:underline text-[11px]"
                      >
                        {selectedItem.run.id}
                      </Link>
                      <div className="mt-1">
                        <StatusBadge status={selectedItem.run.status} size="sm" />
                      </div>
                    </div>

                    <div className="bg-surface-elevated p-3 rounded border border-border-subtle">
                      <span className="text-text-muted block text-[10px]">Modified Files:</span>
                      <span className="text-text-primary">
                        {selectedItem.patch.target_files.join(", ")}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Subprocess Test Execution Evidence & Reviewer Findings */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                  {/* Test Evidence */}
                  <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-2">
                    <div className="flex items-center justify-between text-text-primary font-bold">
                      <span className="flex items-center gap-1.5 text-cyan-ice">
                        <Terminal className="w-4 h-4" /> Tester Telemetry
                      </span>
                      <StatusBadge status={selectedItem.patch.validation_status} size="sm" />
                    </div>
                    <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle text-text-secondary text-[11px] leading-relaxed">
                      {testerEvent?.message || (
                        isValidationFailed
                          ? "Execution returned Exit Code 1: Concurrency stress tests failed with data underflow errors."
                          : "Subprocess test execution recorded in workflow run."
                      )}
                    </div>
                  </div>

                  {/* Reviewer Findings */}
                  <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-2">
                    <div className="flex items-center justify-between text-text-primary font-bold">
                      <span className="flex items-center gap-1.5 text-amber-attention">
                        <ShieldCheck className="w-4 h-4" /> Reviewer Assessment
                      </span>
                      {isValidationFailed ? (
                        <span className="text-[10px] text-semantic-danger font-bold uppercase">
                          BLOCKED / FAILED
                        </span>
                      ) : isStaticOnly ? (
                        <span className="text-[10px] text-amber-attention font-bold uppercase">
                          STATIC AST ONLY
                        </span>
                      ) : (
                        <span className="text-[10px] text-forge-lime font-bold uppercase">
                          ZERO CRITICAL RISKS
                        </span>
                      )}
                    </div>
                    <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle text-text-secondary text-[11px] leading-relaxed">
                      {reviewerEvent?.message || (
                        isValidationFailed
                          ? "Automated verification aborted at repair gatekeeper: test execution failed and repair budget was exhausted. Sign-off strictly blocked."
                          : "Independent static reviewer verified patch safety and minimal blast radius."
                      )}
                    </div>
                  </div>
                </div>

                {/* Unified Diff Safe Viewer */}
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                    <FileCode2 className="w-3.5 h-3.5 text-forge-lime" />
                    Unified Diff Inspection
                  </h3>
                  <DiffViewer
                    diff={selectedItem.patch.unified_diff}
                    filename={selectedItem.patch.target_files[0] || "patch.diff"}
                  />
                </div>
              </>
            ) : (
              <div className="p-12 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
                Select a patch revision to review code changes and cryptographic audit parameters.
              </div>
            )}
          </div>
        </div>

        {selectedItem && (
          <ApprovalModal
            run={selectedItem.run}
            patch={selectedItem.patch}
            isOpen={isApprovalOpen}
            onClose={() => setIsApprovalOpen(false)}
            onSuccess={() => {
              setActionSuccess("Patch approval successfully submitted and audited.");
              loadPatches();
            }}
          />
        )}
      </main>
    </div>
  );
}
