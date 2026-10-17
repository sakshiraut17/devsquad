import React from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number | string | null;
  icon: React.ComponentType<{ className?: string }>;
  sublabel?: string;
  status?: "normal" | "warning" | "danger" | "success" | "lime";
  loading?: boolean;
}

export function MetricCard({
  label,
  value,
  icon: Icon,
  sublabel,
  status = "normal",
  loading = false,
}: MetricCardProps) {
  let statusBorder = "border-border-subtle";
  let statusText = "text-text-primary";
  let iconColor = "text-text-muted";

  if (status === "lime") {
    statusBorder = "border-forge-lime/40";
    statusText = "text-forge-lime";
    iconColor = "text-forge-lime";
  } else if (status === "warning") {
    statusBorder = "border-amber-attention/40";
    statusText = "text-amber-attention";
    iconColor = "text-amber-attention";
  } else if (status === "danger") {
    statusBorder = "border-semantic-danger/40";
    statusText = "text-semantic-danger";
    iconColor = "text-semantic-danger";
  } else if (status === "success") {
    statusBorder = "border-semantic-success/40";
    statusText = "text-semantic-success";
    iconColor = "text-semantic-success";
  }

  return (
    <div
      className={cn(
        "p-4 rounded-lg bg-surface border transition-colors",
        statusBorder
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider font-mono">
          {label}
        </span>
        <div className="p-1.5 rounded bg-surface-elevated border border-border-subtle">
          <Icon className={cn("w-3.5 h-3.5", iconColor)} />
        </div>
      </div>

      <div className="text-2xl font-bold font-mono tracking-tight">
        {loading ? (
          <div className="h-7 w-16 bg-surface-elevated animate-pulse rounded" />
        ) : (
          <span className={statusText}>{value ?? "—"}</span>
        )}
      </div>

      {sublabel && (
        <div className="text-[11px] text-text-muted mt-1 font-mono">{sublabel}</div>
      )}
    </div>
  );
}
