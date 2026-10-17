"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Terminal,
  Clock,
  Cpu,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { TestResult } from "@/types";

interface TestResultCardProps {
  testResult: TestResult | null | undefined;
  validationStatus?: string;
}

export function TestResultCard({ testResult, validationStatus }: TestResultCardProps) {
  const [showLogs, setShowLogs] = useState(true);

  if (!testResult) {
    return (
      <div className="p-5 rounded-lg bg-surface border border-border-subtle text-xs font-mono text-text-muted">
        Sandbox tester has not evaluated any patch revision yet.
      </div>
    );
  }

  const status = testResult.status || validationStatus || "PENDING";
  const isPassed = status === "TESTS_PASSED" || status === "passed" || status === "VALIDATED";
  const isPartial = status === "PARTIAL_VALIDATION" || status === "partial_validation" || status === "ast_fallback";
  const isSandboxUnavailable = status === "SANDBOX_UNAVAILABLE" || status === "sandbox_unavailable";
  const isFailed = status === "FAILED" || status === "failed" || testResult.failed > 0 || testResult.exit_code !== 0;

  return (
    <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
      {/* Header & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-ice" />
          <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            Automated Validation &amp; Sandbox Execution
          </h3>
        </div>

        <div>
          {isPassed ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-semantic-success/15 border border-semantic-success/40 text-semantic-success text-[11px] font-bold uppercase">
              <CheckCircle2 className="w-3.5 h-3.5" /> Tests Passed
            </span>
          ) : isPartial ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-[11px] font-bold uppercase">
              <AlertTriangle className="w-3.5 h-3.5" /> Partial Validation (AST Fallback)
            </span>
          ) : isSandboxUnavailable ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-[11px] font-bold uppercase">
              <AlertTriangle className="w-3.5 h-3.5" /> Sandbox Unavailable
            </span>
          ) : isFailed ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-semantic-danger/15 border border-semantic-danger/40 text-semantic-danger text-[11px] font-bold uppercase">
              <XCircle className="w-3.5 h-3.5" /> Tests Failed (Exit Code {testResult.exit_code})
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-elevated border border-border-subtle text-text-muted text-[11px] uppercase">
              {status}
            </span>
          )}
        </div>
      </div>

      {/* Prominent Banner for Partial or Fallback Validation */}
      {isPartial && (
        <div className="p-3.5 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">STATIC AST VALIDATION ONLY — EXECUTION NOT CERTIFIED</p>
            <p className="text-[11px] text-text-secondary mt-0.5">
              Docker container sandbox was unavailable or bypassed; only AST syntax tree verification was executed. Test execution cannot be certified as fully passing.
            </p>
          </div>
        </div>
      )}

      {/* Execution Telemetry Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Environment</span>
          <span className="text-text-primary font-bold flex items-center gap-1 mt-0.5">
            <Cpu className="w-3 h-3 text-cyan-ice" />
            {testResult.environment || "isolated_container"}
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Duration</span>
          <span className="text-text-primary font-bold flex items-center gap-1 mt-0.5">
            <Clock className="w-3 h-3 text-text-muted" />
            {testResult.duration_ms} ms
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Passed / Total</span>
          <span className="text-semantic-success font-bold mt-0.5 block">
            {testResult.passed} passed / {testResult.passed + testResult.failed + testResult.skipped} total
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Failures / Exit</span>
          <span className={testResult.failed > 0 || testResult.exit_code !== 0 ? "text-semantic-danger font-bold mt-0.5 block" : "text-text-muted mt-0.5 block"}>
            {testResult.failed} failed (code {testResult.exit_code})
          </span>
        </div>
      </div>

      {/* Commands Executed */}
      {testResult.commands_executed && testResult.commands_executed.length > 0 && (
        <div className="space-y-1 text-xs">
          <span className="text-[11px] text-text-muted uppercase tracking-wider block font-bold">
            Commands Executed:
          </span>
          <div className="p-2 rounded bg-[#0E1114] border border-border-subtle text-text-secondary text-[11px] font-mono space-y-0.5">
            {testResult.commands_executed.map((cmd, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className="text-forge-lime">$</span>
                <span>{cmd}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Test Logs / stdout / stderr */}
      {(testResult.stdout || testResult.stderr || testResult.error_message) && (
        <div className="space-y-1 pt-1">
          <button
            type="button"
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center justify-between w-full text-xs text-text-muted hover:text-text-primary font-bold uppercase tracking-wider py-1"
          >
            <span>Sandbox Console Output (stdout / stderr)</span>
            {showLogs ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showLogs && (
            <div className="p-3 rounded bg-[#090B0D] border border-border-subtle text-xs font-mono space-y-2 max-h-64 overflow-y-auto">
              {testResult.stdout && (
                <div>
                  <span className="text-[10px] text-cyan-ice block mb-0.5 uppercase font-bold">[stdout]</span>
                  <pre className="text-text-primary whitespace-pre-wrap leading-relaxed text-[11px]">
                    {testResult.stdout}
                  </pre>
                </div>
              )}

              {testResult.stderr && (
                <div>
                  <span className="text-[10px] text-semantic-danger block mb-0.5 uppercase font-bold">[stderr]</span>
                  <pre className="text-semantic-danger whitespace-pre-wrap leading-relaxed text-[11px]">
                    {testResult.stderr}
                  </pre>
                </div>
              )}

              {testResult.error_message && (
                <div className="p-2 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-[11px]">
                  {testResult.error_message}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
