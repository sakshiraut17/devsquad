import React from "react";
import { Check, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { RunStatus } from "@/types";

interface RunStageStepperProps {
  currentStage: string;
  status: RunStatus;
  repairAttempts?: number;
}

const STAGES = [
  { key: "context", label: "CONTEXT", color: "cyan" },
  { key: "planner", label: "PLAN", color: "ultraviolet" },
  { key: "coder", label: "PATCH", color: "lime" },
  { key: "tester", label: "TEST", color: "cyan" },
  { key: "reviewer", label: "REVIEW", color: "amber" },
  { key: "approval", label: "HUMAN GATE", color: "lime" },
];

export function RunStageStepper({
  currentStage,
  status,
  repairAttempts = 0,
}: RunStageStepperProps) {
  const getStageIndex = (stage: string) => {
    const s = stage.toLowerCase();
    if (s.includes("context") || s.includes("ingest") || s.includes("validat")) return 0;
    if (s.includes("plan")) return 1;
    if (s.includes("code") || s.includes("patch")) return 2;
    if (s.includes("test")) return 3;
    if (s.includes("review") || s.includes("repair")) return 4;
    if (s.includes("approv") || s.includes("wait") || s.includes("gate")) return 5;
    return -1;
  };

  const activeIdx = getStageIndex(currentStage);
  const isFailed = status === "FAILED" || status === "REJECTED";
  const isCompleted = status === "COMPLETED" || status === "APPROVED";

  return (
    <div className="w-full py-3 overflow-x-auto select-none">
      <div className="flex items-center justify-between min-w-[620px]">
        {STAGES.map((st, idx) => {
          const isPassed = isCompleted || (!isFailed && activeIdx > idx);
          const isCurrent = !isCompleted && activeIdx === idx;
          const isCurrentFailed = isFailed && activeIdx === idx;

          return (
            <React.Fragment key={st.key}>
              <div className="flex flex-col items-center relative">
                <div
                  className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-mono font-bold border transition-all",
                    isPassed &&
                      "bg-semantic-success/20 text-semantic-success border-semantic-success/50",
                    isCurrent &&
                      !isFailed &&
                      "bg-forge-lime/20 text-forge-lime border-forge-lime shadow-[0_0_8px_rgba(215,255,100,0.5)] animate-pulse",
                    isCurrentFailed &&
                      "bg-semantic-danger/20 text-semantic-danger border-semantic-danger/50",
                    !isPassed &&
                      !isCurrent &&
                      !isCurrentFailed &&
                      "bg-surface-elevated text-text-muted border-border-subtle"
                  )}
                >
                  {isPassed ? (
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  ) : isCurrent && !isFailed ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : isCurrentFailed ? (
                    <AlertCircle className="w-3.5 h-3.5" />
                  ) : (
                    idx + 1
                  )}
                </div>

                <span
                  className={cn(
                    "text-[10px] mt-1.5 font-mono tracking-wider font-semibold whitespace-nowrap",
                    isCurrent
                      ? "text-forge-lime"
                      : isPassed
                      ? "text-text-primary"
                      : "text-text-muted"
                  )}
                >
                  {st.label}
                  {st.key === "reviewer" && repairAttempts > 0 && (
                    <span className="text-[9px] text-amber-attention ml-1">
                      (repairs: {repairAttempts}/3)
                    </span>
                  )}
                </span>
              </div>

              {idx < STAGES.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-[2px] mx-2 -mt-4 transition-colors",
                    isPassed ? "bg-semantic-success/60" : "bg-border-subtle"
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
