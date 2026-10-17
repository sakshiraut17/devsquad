"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  TerminalSquare,
  GitBranch,
  AlertCircle,
  PlayCircle,
  FileCode2,
  Radio,
  Gauge,
  Settings,
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
    <aside className="w-64 border-r border-border-subtle bg-surface flex flex-col h-screen sticky top-0 select-none z-30">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-border-subtle">
        <DevSquadLogo size="md" showWordmark={true} />
      </div>

      {/* Navigation Rail */}
      <nav className="flex-1 px-2.5 py-4 space-y-1 overflow-y-auto">
        <div className="text-[10px] font-mono font-medium uppercase tracking-wider text-text-muted px-3 mb-2.5">
          Engineering Rail
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 px-3 py-2 rounded text-xs font-mono transition-all",
                isActive
                  ? "bg-surface-elevated text-text-primary font-semibold border border-border-subtle"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover/70"
              )}
            >
              {/* Forge Lime Active Indicator Bar */}
              {isActive && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r bg-forge-lime shadow-[0_0_8px_rgba(215,255,100,0.6)]" />
              )}
              <Icon
                className={cn(
                  "w-4 h-4 shrink-0 transition-colors",
                  isActive
                    ? "text-forge-lime"
                    : "text-text-muted group-hover:text-text-secondary"
                )}
              />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Control Room Engine Status */}
      <div className="p-3.5 border-t border-border-subtle bg-[#0D1013] text-xs font-mono">
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="text-text-muted">Orchestrator</span>
          <span className="text-forge-lime flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-forge-lime animate-pulse" />
            LangGraph 2.0
          </span>
        </div>
        <div className="text-[10px] text-text-muted">
          10-Stage State Machine • SQLite
        </div>
      </div>
    </aside>
  );
}
