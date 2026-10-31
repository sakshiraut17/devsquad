"use client";

import React, { useState } from "react";
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
  ChevronLeft,
  ChevronRight,
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
  const [collapsed, setCollapsed] = useState(false);

  if (pathname === "/login") {
    return null;
  }

  return (
    <aside
      className={cn(
        "border-r border-border-subtle bg-surface/90 backdrop-blur-xl flex flex-col h-screen sticky top-0 select-none z-30 shadow-2xl transition-all duration-300",
        collapsed ? "w-[72px]" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border-subtle bg-surface/40">
        <div className="overflow-hidden">
          <DevSquadLogo size="md" showWordmark={!collapsed} />
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-elevated transition-colors"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation Rail */}
      <nav className="flex-1 px-2.5 py-4 space-y-1 overflow-y-auto">
        {!collapsed && (
          <div className="flex items-center justify-between px-3 mb-2.5">
            <span className="text-xs font-sans font-semibold uppercase tracking-wider text-text-muted">
              Platform
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-semibold">
              Live
            </span>
          </div>
        )}

        {navItems.map((item) => {
          const Icon = item.icon as any;
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

          return (
            <motion.div
              key={item.href}
              whileHover={{ x: collapsed ? 0 : 3 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            >
              <Link
                href={item.href}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-sans transition-all overflow-hidden",
                  isActive
                    ? "bg-surface-elevated text-text-primary font-semibold border border-cyan-500/20 shadow-sm"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/80 font-medium",
                  collapsed && "justify-center px-0"
                )}
              >
                {/* Active Indicator with Motion layoutId */}
                {isActive && (
                  <motion.span
                    layoutId="activeSidebarIndicator"
                    className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-gradient-to-b from-cyan-400 to-emerald-400 shadow-[0_0_12px_rgba(0,242,254,0.8)]"
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
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            </motion.div>
          );
        })}
      </nav>

      {/* Control Room Engine Status */}
      <div className="p-3.5 border-t border-border-subtle bg-surface-elevated/40 text-xs font-sans">
        <div className="flex items-center justify-between mb-1">
          <span className="text-text-muted flex items-center gap-1.5 font-medium">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            {!collapsed && "Orchestrator"}
          </span>
          <span className="text-emerald-400 flex items-center gap-1.5 font-semibold font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {!collapsed && "LangGraph 2.0"}
          </span>
        </div>
        {!collapsed && (
          <div className="text-[11px] text-text-muted font-mono">
            7-Agent State Machine • Realtime
          </div>
        )}
      </div>
    </aside>
  );
}
