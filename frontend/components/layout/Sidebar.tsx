"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import {
  TerminalSquare,
  GitBranch,
  AlertCircle,
  PlayCircle,
  FileCode2,
  Radio,
  Gauge,
  Settings,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DevSquadLogo } from "./DevSquadLogo";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: "Command Center", href: "/", icon: TerminalSquare },
  { label: "Repositories", href: "/repositories", icon: GitBranch },
  { label: "Issues", href: "/issues", icon: AlertCircle },
  { label: "Agent Runs", href: "/runs", icon: PlayCircle },
  { label: "Patch Laboratory", href: "/patches", icon: FileCode2 },
  { label: "Activity Stream", href: "/logs", icon: Radio },
  { label: "System Diagnostics", href: "/health", icon: Gauge },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  if (pathname === "/login") {
    return null;
  }

  return (
    <aside className="w-64 border-r border-border-subtle bg-surface/90 backdrop-blur-xl flex flex-col h-screen sticky top-0 select-none z-30 shadow-2xl">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-border-subtle bg-surface/40">
        <DevSquadLogo size="md" showWordmark={true} />
      </div>

      {/* Navigation Rail */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        <div className="flex items-center justify-between px-3 mb-2.5">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-text-muted">
            Engineering Rail
          </span>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            Realtime
          </span>
        </div>
        {navItems.map((item) => {
          const Icon = item.icon as any;
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

          return (
            <motion.div
              key={item.href}
              whileHover={{ x: 3 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            >
              <Link
                href={item.href}
                className={cn(
                  "group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-mono transition-all overflow-hidden",
                  isActive
                    ? "bg-surface-elevated text-text-primary font-bold border border-cyan-500/20 shadow-sm"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/80"
                )}
              >
                {/* Active Indicator with Motion layoutId */}
                {isActive && (
                  <motion.span
                    layoutId="activeSidebarIndicator"
                    className="absolute left-0 top-1.5 bottom-1.5 w-[3.5px] rounded-r bg-gradient-to-b from-cyan-400 via-emerald-400 to-lime-300 shadow-[0_0_12px_rgba(0,242,254,0.8)]"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}
                <Icon
                  className={cn(
                    "w-4 h-4 shrink-0 transition-colors",
                    isActive
                      ? "text-cyan-400"
                      : "text-text-muted group-hover:text-text-secondary"
                  )}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            </motion.div>
          );
        })}
      </nav>

      {/* Control Room Engine Status */}
      <div className="p-3.5 border-t border-border-subtle bg-surface-elevated/40 text-xs font-mono">
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="text-text-muted flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-cyan-400" />
            Orchestrator
          </span>
          <span className="text-emerald-400 flex items-center gap-1.5 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            LangGraph 2.0
          </span>
        </div>
        <div className="text-[10px] text-text-muted">
          10-Stage State Machine • Realtime
        </div>
      </div>
    </aside>
  );
}
