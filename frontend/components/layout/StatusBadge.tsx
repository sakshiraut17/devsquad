import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
  className?: string;
}

export function StatusBadge({ status, size = "sm", className }: StatusBadgeProps) {
  const normalized = status.toUpperCase();

  let colorClasses = "bg-surface-elevated text-text-secondary border-border-subtle";

  switch (normalized) {
    case "COMPLETED":
    case "APPROVED":
    case "PASSED":
    case "HEALTHY":
    case "ACTIVE":
      colorClasses = "bg-semantic-success/15 text-semantic-success border-semantic-success/30";
      break;
    case "AWAITING_APPROVAL":
    case "WAITING_FOR_APPROVAL":
      colorClasses = "bg-amber-attention/15 text-amber-attention border-amber-attention/40 animate-pulse";
      break;
    case "PLANNING":
      colorClasses = "bg-ultraviolet/15 text-ultraviolet border-ultraviolet/30";
      break;
    case "CODING":
      colorClasses = "bg-forge-lime/15 text-forge-lime border-forge-lime/30";
      break;
    case "TESTING":
      colorClasses = "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30";
      break;
    case "REVIEWING":
      colorClasses = "bg-amber-attention/15 text-amber-attention border-amber-attention/30";
      break;
    case "INGESTING":
    case "RUNNING":
      colorClasses = "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30";
      break;
    case "FAILED":
    case "REJECTED":
    case "UNHEALTHY":
    case "ERROR":
      colorClasses = "bg-semantic-danger/15 text-semantic-danger border-semantic-danger/30";
      break;
    case "DEGRADED":
    case "SANDBOX_UNAVAILABLE":
    case "PARTIAL_VALIDATION":
    case "AST_FALLBACK":
      colorClasses = "bg-amber-attention/15 text-amber-attention border-amber-attention/30";
      break;
    case "QUEUED":
    case "CANCELLED":
    case "INACTIVE":
    default:
      colorClasses = "bg-surface-elevated text-text-muted border-border-subtle";
      break;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-medium rounded border uppercase tracking-wider select-none",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
        colorClasses,
        className
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
