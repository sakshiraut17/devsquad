"use client";

import React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number | string | null;
  icon: React.ComponentType<{ className?: string }>;
  sublabel?: string;
  trend?: string;
  status?: "normal" | "warning" | "danger" | "success" | "lime";
  loading?: boolean;
}

export function MetricCard({
  label,
  value,
  icon: Icon,
  sublabel,
  trend,
  status = "normal",
  loading = false,
}: MetricCardProps) {
  let statusBorder = "border-border-subtle hover:border-border-strong";
  let statusText = "text-text-primary";
  let iconBg = "bg-surface-elevated text-text-secondary";
  let glowEffect = "";

  if (status === "lime") {
    statusBorder = "border-cyan-400/30 hover:border-cyan-400/60";
    statusText = "text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400";
    iconBg = "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20";
    glowEffect = "shadow-[0_0_20px_-5px_rgba(56,189,248,0.2)]";
  } else if (status === "warning") {
    statusBorder = "border-amber-400/30 hover:border-amber-400/60";
    statusText = "text-amber-400";
    iconBg = "bg-amber-500/10 text-amber-400 border border-amber-500/20";
    glowEffect = "shadow-[0_0_20px_-5px_rgba(245,158,11,0.2)]";
  } else if (status === "danger") {
    statusBorder = "border-rose-500/30 hover:border-rose-500/60";
    statusText = "text-rose-400";
    iconBg = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
    glowEffect = "shadow-[0_0_20px_-5px_rgba(244,63,94,0.2)]";
  } else if (status === "success") {
    statusBorder = "border-emerald-500/30 hover:border-emerald-500/60";
    statusText = "text-emerald-400";
    iconBg = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    glowEffect = "shadow-[0_0_20px_-5px_rgba(16,185,129,0.2)]";
  }

  return (
    <motion.div
      whileHover={{ y: -3, transition: { duration: 0.18, ease: "easeOut" } }}
      className={cn(
        "p-5 rounded-2xl bg-surface/90 backdrop-blur-xl border transition-all cursor-default relative overflow-hidden flex flex-col justify-between shadow-sm",
        statusBorder,
        glowEffect
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider font-sans">
          {label}
        </span>
        <div className={cn("p-2 rounded-xl transition-colors", iconBg)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>

      <div className="space-y-1">
        <div className="text-3xl font-extrabold font-sans tracking-tight">
          {loading ? (
            <div className="h-8 w-24 bg-surface-elevated animate-pulse rounded-lg" />
          ) : (
            <span className={statusText}>{value ?? 0}</span>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          {sublabel && (
            <span className="text-xs text-text-muted font-sans font-medium">{sublabel}</span>
          )}
          {trend && (
            <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
              {trend}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
