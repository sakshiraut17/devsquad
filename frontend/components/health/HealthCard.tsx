import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface HealthCardProps {
  title: string;
  status: "healthy" | "operational" | "degraded" | "unavailable" | "unconfigured" | "unhealthy" | "error" | string;
  latencyMs?: number | null;
  details?: Record<string, any> | null;
  description?: string;
  remediation?: string;
}

export function HealthCard({
  title,
  status,
  latencyMs,
  details,
  description,
  remediation,
}: HealthCardProps) {
  let statusBadge = (
    <span className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted">
      <Info className="w-3.5 h-3.5" /> UNKNOWN
    </span>
  );
  let borderColor = "border-border-subtle";

  const normStatus = (status || "").toLowerCase();

  if (normStatus === "healthy" || normStatus === "operational") {
    statusBadge = (
      <span className="flex items-center gap-1.5 text-[11px] font-mono text-semantic-success font-semibold">
        <CheckCircle2 className="w-3.5 h-3.5" /> OPERATIONAL
      </span>
    );
    borderColor = "border-semantic-success/30";
  } else if (normStatus === "degraded") {
    statusBadge = (
      <span className="flex items-center gap-1.5 text-[11px] font-mono text-amber-attention font-semibold">
        <AlertTriangle className="w-3.5 h-3.5" /> DEGRADED
      </span>
    );
    borderColor = "border-amber-attention/30";
  } else if (normStatus === "unavailable") {
    statusBadge = (
      <span className="flex items-center gap-1.5 text-[11px] font-mono text-amber-attention font-semibold">
        <AlertTriangle className="w-3.5 h-3.5" /> UNAVAILABLE
      </span>
    );
    borderColor = "border-amber-attention/30";
  } else if (normStatus === "unconfigured") {
    statusBadge = (
      <span className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted font-semibold">
        <Info className="w-3.5 h-3.5" /> UNCONFIGURED
      </span>
    );
    borderColor = "border-border-subtle";
  } else if (normStatus === "unhealthy" || normStatus === "error" || normStatus === "failed") {
    statusBadge = (
      <span className="flex items-center gap-1.5 text-[11px] font-mono text-semantic-danger font-semibold">
        <XCircle className="w-3.5 h-3.5" /> FAILED
      </span>
    );
    borderColor = "border-semantic-danger/30";
  }

  return (
    <div className={cn("p-5 rounded-lg bg-surface border space-y-3", borderColor)}>
      <div className="flex items-center justify-between border-b border-border-subtle pb-2.5">
        <h3 className="text-xs font-bold text-text-primary font-mono tracking-wide">{title}</h3>
        {statusBadge}
      </div>

      {description && <p className="text-xs text-text-secondary leading-relaxed font-mono">{description}</p>}

      <div className="space-y-1.5 text-xs font-mono bg-surface-elevated p-3 rounded border border-border-subtle">
        {latencyMs !== undefined && latencyMs !== null && (
          <div className="flex justify-between">
            <span className="text-text-muted">Live Probe Latency:</span>
            <span className="text-forge-lime font-bold">{latencyMs.toFixed(2)} ms</span>
          </div>
        )}
        {details &&
          Object.entries(details).map(([key, val]) => (
            <div key={key} className="flex justify-between text-[11px]">
              <span className="text-text-muted capitalize">{key.replace(/_/g, " ")}:</span>
              <span className="text-text-primary font-mono">
                {typeof val === "boolean"
                  ? val
                    ? "true"
                    : "false"
                  : typeof val === "object"
                  ? JSON.stringify(val)
                  : String(val)}
              </span>
            </div>
          ))}
      </div>

      {remediation && (
        <div className="p-2.5 rounded bg-amber-attention/10 border border-amber-attention/30 text-amber-attention text-[11px] font-mono flex items-start gap-1.5">
          <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>{remediation}</span>
        </div>
      )}
    </div>
  );
}
