import React from "react";

interface DevSquadLogoProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
}

export function DevSquadLogo({
  className = "",
  size = "md",
  showWordmark = true,
}: DevSquadLogoProps) {
  const iconSizes = {
    sm: "w-6 h-6",
    md: "w-7 h-7",
    lg: "w-9 h-9",
  };

  const iconPixelSizes = {
    sm: 24,
    md: 28,
    lg: 36,
  };

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Connected 4-Agent Geometric Mark */}
      <svg
        viewBox="0 0 32 32"
        width={iconPixelSizes[size]}
        height={iconPixelSizes[size]}
        style={{
          width: `${iconPixelSizes[size]}px`,
          height: `${iconPixelSizes[size]}px`,
          maxWidth: `${iconPixelSizes[size]}px`,
          maxHeight: `${iconPixelSizes[size]}px`,
        }}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`${iconSizes[size]} shrink-0`}
      >
        {/* Background rounded frame */}
        <rect
          x="1"
          y="1"
          width="30"
          height="30"
          rx="6"
          fill="#14181C"
          stroke="#242C34"
          strokeWidth="1.5"
        />

        {/* Interconnected circuit paths */}
        <path
          d="M16 7V25M7 16H25M9.5 9.5L22.5 22.5M9.5 22.5L22.5 9.5"
          stroke="#2E3842"
          strokeWidth="1"
          strokeDasharray="2 2"
        />

        {/* Central Orchestrator core */}
        <circle cx="16" cy="16" r="3.5" fill="#0B0D0F" stroke="#333D48" strokeWidth="1.5" />
        <circle cx="16" cy="16" r="1.5" fill="#D7FF64" />

        {/* Node 1: Planner (North - Ultraviolet) */}
        <circle cx="16" cy="7" r="2.5" fill="#A78BFA" />

        {/* Node 2: Coder (East - Forge Lime) */}
        <circle cx="25" cy="16" r="2.5" fill="#D7FF64" />

        {/* Node 3: Sandbox Tester (South - Ice Cyan) */}
        <circle cx="16" cy="25" r="2.5" fill="#65E4F3" />

        {/* Node 4: Reviewer (West - Amber) */}
        <circle cx="7" cy="16" r="2.5" fill="#FFB454" />
      </svg>

      {/* Wordmark */}
      {showWordmark && (
        <div className="flex items-baseline font-mono tracking-tight">
          <span className="font-bold text-sm tracking-wider text-text-primary">
            DEV<span className="text-forge-lime">SQUAD</span>
          </span>
          <span className="ml-2 text-[9px] px-1 py-0.2 rounded bg-surface-elevated text-text-muted border border-border-subtle uppercase">
            Ops
          </span>
        </div>
      )}
    </div>
  );
}
