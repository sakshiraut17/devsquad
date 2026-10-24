"use client";

import React from "react";
import { motion } from "motion/react";
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
  let glowEffect = "";

  if (status === "lime") {
    statusBorder = "border-cyan-400/40";
    statusText = "text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-emerald-400";
    iconColor = "text-cyan-400";
    glowEffect = "shadow-[0_0_15px_-3px_rgba(0,242,254,0.15)]";
  } else if (status === "warning") {
    statusBorder = "border-amber-attention/40";
    statusText = "text-amber-300";
    iconColor = "text-amber-300";
    glowEffect = "shadow-[0_0_15px_-3px_rgba(255,180,84,0.15)]";
  } else if (status === "danger") {
    statusBorder = "border-rose-500/40";
    statusText = "text-rose-400";
    iconColor = "text-rose-400";
    glowEffect = "shadow-[0_0_15px_-3px_rgba(244,63,94,0.15)]";
  } else if (status === "success") {
    statusBorder = "border-emerald-500/40";
    statusText = "text-emerald-400";
    iconColor = "text-emerald-400";
    glowEffect = "shadow-[0_0_15px_-3px_rgba(16,185,129,0.15)]";
  }

  return (
    <motion.div
      whileHover={{ scale: 1.025, y: -2 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        "p-4 rounded-2xl bg-surface/90 backdrop-blur-xl border transition-all cursor-default relative overflow-hidden",
        statusBorder,
        glowEffect
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider font-mono">
          {label}
        </span>
        <div className="p-2 rounded-xl bg-surface-elevated border border-border-subtle">
          <Icon className={cn("w-3.5 h-3.5", iconColor)} />
        </div>
      </div>

      <div className="text-2xl font-black font-mono tracking-tight">
        {loading ? (
          <div className="h-7 w-16 bg-surface-elevated animate-pulse rounded-lg" />
        ) : (
          <span className={statusText}>{value ?? "—"}</span>
        )}
      </div>

      {sublabel && (
        <div className="text-[11px] text-text-muted mt-1 font-mono">{sublabel}</div>
      )}
    </motion.div>
  );
}
