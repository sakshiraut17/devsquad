"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Brain,
  Code2,
  Terminal,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Info,
  ChevronRight,
  Zap,
  Activity,
  FileCheck,
  FileText,
  FlaskConical,
  UserCheck,
  RotateCcw,
  Play,
  Pause,
  Loader2,
  Check,
} from "lucide-react";
import { AgentEvent, Run, WorkflowStateSnapshot } from "@/types";

interface AgentFlowVisualizationProps {
  run: Run | null;
  events?: AgentEvent[];
  stateSnapshot?: WorkflowStateSnapshot | null;
  className?: string;
}

type NodeStatus = "idle" | "running" | "completed" | "failed" | "waiting";

interface AgentNodeDef {
  key: string;
  name: string;
  role: string;
  color: string;
  borderColor: string;
  activeRing: string;
  bgColor: string;
  textColor: string;
  capabilities: string[];
  systemInstruction: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AGENTS: AgentNodeDef[] = [
  {
    key: "context",
    name: "Context Ranker",
    role: "Finds relevant files and code sections in repository",
    color: "#38BDF8",
    borderColor: "border-sky-400/30",
    activeRing: "ring-2 ring-sky-400/60 shadow-[0_0_20px_rgba(56,189,248,0.3)]",
    bgColor: "bg-sky-500/10",
    textColor: "text-sky-400",
    capabilities: [
      "Repository tree ingestion & token budgeting",
      "Semantic relevance scoring & BM25 ranking",
      "Target file boundary isolation",
    ],
    systemInstruction:
      "Finds relevant files and code sections in the repository to provide exact context for planning and patching.",
    icon: FileText,
  },
  {
    key: "planner",
    name: "Planner Agent",
    role: "Creates a step-by-step plan to solve the issue",
    color: "#10B981",
    borderColor: "border-emerald-400/30",
    activeRing: "ring-2 ring-emerald-400/60 shadow-[0_0_20px_rgba(16,185,129,0.3)]",
    bgColor: "bg-emerald-500/10",
    textColor: "text-emerald-400",
    capabilities: [
      "Root cause hypothesis synthesis",
      "Structured resolution step formulation",
      "Defect acceptance criteria definition",
    ],
    systemInstruction:
      "Creates a step-by-step plan to solve the issue with verifiable acceptance criteria.",
    icon: Brain,
  },
  {
    key: "coder",
    name: "Coder Agent",
    role: "Generates the proposed code changes",
    color: "#A78BFA",
    borderColor: "border-purple-400/30",
    activeRing: "ring-2 ring-purple-400/60 shadow-[0_0_20px_rgba(167,139,250,0.3)]",
    bgColor: "bg-purple-500/10",
    textColor: "text-purple-400",
    capabilities: [
      "Minimal unified diff synthesis (zero extraneous edits)",
      "Strict target file adherence",
      "Bounded repair loop adaptation",
    ],
    systemInstruction:
      "Produces clean, minimal unified diffs resolving the bug while strictly preserving unrelated source code and formatting.",
    icon: Code2,
  },
  {
    key: "security",
    name: "Security Guardian",
    role: "Checks for security risks and vulnerabilities",
    color: "#F43F5E",
    borderColor: "border-rose-400/30",
    activeRing: "ring-2 ring-rose-400/60 shadow-[0_0_20px_rgba(244,63,94,0.3)]",
    bgColor: "bg-rose-500/10",
    textColor: "text-rose-400",
    capabilities: [
      "AST syntax & dangerous function vulnerability scan",
      "Secret & token pattern detection",
      "Fail-closed mandatory gate blocking",
    ],
    systemInstruction:
      "Checks for security risks, injection vulnerabilities, and secret leaks before tests or review.",
    icon: ShieldCheck,
  },
  {
    key: "tester",
    name: "Tester Agent",
    role: "Runs tests to verify changes work correctly",
    color: "#F59E0B",
    borderColor: "border-amber-400/30",
    activeRing: "ring-2 ring-amber-400/60 shadow-[0_0_20px_rgba(245,158,11,0.3)]",
    bgColor: "bg-amber-500/10",
    textColor: "text-amber-400",
    capabilities: [
      "Ephemeral Docker container isolation",
      "Non-root execution (user 1000:1000) & network disabled",
      "Dynamic exit code validation (Exit 0 strictly required)",
    ],
    systemInstruction:
      "Runs tests inside disposable Docker sandbox to verify that the proposed changes work correctly.",
    icon: FlaskConical,
  },
  {
    key: "reviewer",
    name: "Reviewer Agent",
    role: "Reviews the solution and identifies possible issues",
    color: "#06B6D4",
    borderColor: "border-cyan-400/30",
    activeRing: "ring-2 ring-cyan-400/60 shadow-[0_0_20px_rgba(6,182,212,0.3)]",
    bgColor: "bg-cyan-500/10",
    textColor: "text-cyan-400",
    capabilities: [
      "Independent multi-angle code review",
      "Acceptance criteria satisfaction verification",
      "Approval recommendation synthesis",
    ],
    systemInstruction:
      "Reviews the solution and identifies possible issues, edge cases, and regressions.",
    icon: FileCheck,
  },
  {
    key: "approval",
    name: "Human Approval",
    role: "Developer reviews and approves the changes",
    color: "#EC4899",
    borderColor: "border-pink-400/30",
    activeRing: "ring-2 ring-pink-400/60 shadow-[0_0_20px_rgba(236,72,153,0.3)]",
    bgColor: "bg-pink-500/10",
    textColor: "text-pink-400",
    capabilities: [
      "Cryptographic patch content hash verification",
      "Zero automated push / strict human-in-the-loop sign-off",
      "Audit trail log recording",
    ],
    systemInstruction:
      "Developer reviews and approves the changes before any git write-back or PR publication.",
    icon: UserCheck,
  },
];

export function AgentFlowVisualization({
  run,
  events = [],
  stateSnapshot,
  className = "",
}: AgentFlowVisualizationProps) {
  const [selectedAgentKey, setSelectedAgentKey] = useState<string>("context");
  const [inspectorTab, setInspectorTab] = useState<"telemetry" | "spec" | "capabilities">("telemetry");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simStep, setSimStep] = useState<number>(-1);

  // Live simulation stepper loop
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isSimulating) {
      if (simStep < AGENTS.length - 1) {
        timer = setTimeout(() => {
          const next = simStep + 1;
          setSimStep(next);
          setSelectedAgentKey(AGENTS[next].key);
        }, 1200);
      } else {
        timer = setTimeout(() => {
          setIsSimulating(false);
        }, 2000);
      }
    }
    return () => clearTimeout(timer);
  }, [isSimulating, simStep]);

  const handleStartSimulation = () => {
    setSimStep(0);
    setSelectedAgentKey(AGENTS[0].key);
    setIsSimulating(true);
  };

  const handleResetSimulation = () => {
    setIsSimulating(false);
    setSimStep(-1);
    setSelectedAgentKey("context");
  };

  const getNodeStatus = (agentKey: string): NodeStatus => {
    if (isSimulating || simStep >= 0) {
      const idx = AGENTS.findIndex((a) => a.key === agentKey);
      if (idx < simStep) return "completed";
      if (idx === simStep) return "running";
      return "idle";
    }

    if (!run) return "idle";

    const current = run.current_node?.toLowerCase() || "";
    const runStatus = run.status;

    if (runStatus === "COMPLETED" || runStatus === "APPROVED" || runStatus === "AWAITING_APPROVAL") {
      return "completed";
    }

    if (current.includes(agentKey)) {
      if (runStatus === "FAILED" || runStatus === "REJECTED") return "failed";
      return "running";
    }

    const order = ["context", "planner", "coder", "security", "tester", "reviewer", "approval", "finalization"];
    const agentIndex = order.findIndex((k) => k.includes(agentKey));
    const currentIndex = order.findIndex((k) => current.includes(k));

    if (currentIndex > agentIndex) {
      return "completed";
    }

    if (currentIndex === agentIndex) {
      if (runStatus === "FAILED") return "failed";
      return "running";
    }

    return "idle";
  };

  const getAgentEvent = (agentKey: string) => {
    return (
      events.find((e) => e.agent_name.toLowerCase().includes(agentKey)) ||
      events.find((e) => e.event_type.toLowerCase().includes(agentKey))
    );
  };

  const selectedAgent = AGENTS.find((a) => a.key === selectedAgentKey) || AGENTS[0];
  const selectedEvent = getAgentEvent(selectedAgent.key);
  const selectedStatus = getNodeStatus(selectedAgent.key);

  return (
    <div className={`p-6 lg:p-7 rounded-3xl bg-surface/90 backdrop-blur-xl border border-border-subtle space-y-6 shadow-2xl ${className}`}>
      {/* Header matching Infographic Section 4 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-5">
        <div>
          <div className="flex items-center gap-3">
            <span className="w-7 h-7 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center text-xs font-mono font-bold shadow-sm">
              4
            </span>
            <h3 className="text-base sm:text-lg font-bold font-sans tracking-tight text-text-primary">
              System Architecture &amp; Multi-Agent Workflow
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/30 font-semibold">
              LangGraph StateGraph
            </span>
          </div>
          <p className="text-xs sm:text-sm text-text-secondary font-sans mt-1">
            Click any agent to inspect its real-time synthesis, telemetry logs, and LLM invariants.
          </p>
        </div>

        {/* Live Simulation Controls & Target Run Badge */}
        <div className="flex items-center gap-3">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={isSimulating ? handleResetSimulation : handleStartSimulation}
            className={`px-4 py-2 rounded-xl text-xs font-sans font-bold flex items-center gap-2 transition-all shadow-md ${
              isSimulating
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
                : "bg-gradient-to-r from-cyan-400 via-teal-300 to-emerald-400 hover:from-cyan-300 hover:to-emerald-300 text-black shadow-cyan-500/20"
            }`}
          >
            {isSimulating ? (
              <>
                <Pause className="w-4 h-4" />
                <span>Pause Live Flow</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-black" />
                <span>Watch Agents Work</span>
              </>
            )}
          </motion.button>

          {run && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-elevated/80 border border-border-subtle text-xs font-mono">
              <span className="text-text-muted">Target:</span>
              <span className="text-cyan-400 font-bold">{run.id.slice(0, 8)}…</span>
              <span className="text-text-secondary">({run.status})</span>
            </div>
          )}
        </div>
      </div>

      {/* 7-Stage Horizontal Pipeline Flow with Connected Arrows */}
      <div className="relative overflow-x-auto pb-2">
        <div className="min-w-[850px] flex items-stretch gap-2.5">
          {AGENTS.map((agent, index) => {
            const Icon = agent.icon;
            const status = getNodeStatus(agent.key);
            const isSelected = selectedAgentKey === agent.key;
            const isRunning = status === "running";
            const isCompleted = status === "completed";
            const isFailed = status === "failed";

            return (
              <React.Fragment key={agent.key}>
                <motion.div
                  whileHover={{ y: -3, transition: { duration: 0.18, ease: "easeOut" } }}
                  onClick={() => setSelectedAgentKey(agent.key)}
                  className={`flex-1 min-w-[140px] p-4 rounded-2xl border cursor-pointer transition-all relative overflow-hidden flex flex-col justify-between select-none ${
                    isSelected
                      ? `${agent.borderColor} bg-surface-elevated shadow-xl ${agent.activeRing}`
                      : isRunning
                      ? `${agent.borderColor} bg-surface-elevated ${agent.activeRing}`
                      : "border-border-subtle bg-surface hover:border-border-strong hover:bg-surface-elevated/70"
                  }`}
                >
                  {/* Active selection badge */}
                  {isSelected && (
                    <motion.span
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md text-[9px] font-mono font-bold bg-cyan-400 text-black uppercase"
                    >
                      Viewing
                    </motion.span>
                  )}

                  {/* Running glow pulse */}
                  {isRunning && (
                    <div className="absolute inset-0 bg-cyan-400/10 animate-pulse pointer-events-none" />
                  )}

                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div
                        className={`p-2.5 rounded-xl border border-border-subtle ${agent.bgColor} ${agent.textColor} shadow-inner`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>

                      {/* Node Status Badge */}
                      <div className="text-right">
                        {isRunning && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-cyan-400 font-bold animate-pulse">
                            <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />
                            ACTIVE
                          </span>
                        )}
                        {isCompleted && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 font-bold">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            DONE
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-rose-400 font-bold">
                            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                            FAIL
                          </span>
                        )}
                        {status === "waiting" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-400 font-bold">
                            <Clock className="w-3 h-3 text-amber-400" />
                            GATE
                          </span>
                        )}
                        {status === "idle" && (
                          <span className="text-[10px] font-mono text-text-muted uppercase">
                            IDLE
                          </span>
                        )}
                      </div>
                    </div>

                    <h4 className="text-sm font-bold text-text-primary font-sans tracking-tight">
                      {agent.name}
                    </h4>
                    <p className="text-xs text-text-secondary font-sans mt-1 line-clamp-2 leading-relaxed">
                      {agent.role}
                    </p>
                  </div>

                  {/* Stage Step Indicator */}
                  <div className="mt-3 pt-2.5 border-t border-border-subtle/80 flex items-center justify-between text-xs font-mono text-text-muted">
                    <span className="font-semibold">Step 0{index + 1}</span>
                    <span className={isRunning ? "text-cyan-400 font-bold" : isCompleted ? "text-emerald-400 font-bold" : "text-text-muted"}>
                      {status.toUpperCase()}
                    </span>
                  </div>
                </motion.div>

                {/* Flow Connector Arrow between nodes */}
                {index < AGENTS.length - 1 && (
                  <div className="flex items-center justify-center shrink-0 text-text-muted/50">
                    <div className="flex flex-col items-center">
                      <ArrowRight className={`w-3.5 h-3.5 transition-colors ${
                        (isSimulating && simStep > index) || (run && getNodeStatus(AGENTS[index+1].key) !== "idle")
                          ? "text-cyan-400 animate-pulse"
                          : "text-text-muted/40"
                      }`} />
                    </div>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Bounded Feedback Loop Banner */}
        <div className="mt-4 p-3.5 rounded-2xl bg-purple-950/20 border border-purple-500/30 flex items-center justify-center gap-3 text-center text-xs sm:text-sm font-sans text-purple-200 shadow-sm">
          <RotateCcw className="w-4 h-4 text-purple-400 shrink-0" />
          <span>
            <strong>Bounded Repair Loop:</strong> If tests or review criteria fail, the system repairs and refines the code patch automatically (up to 3 attempts).
          </span>
        </div>
      </div>

      {/* Selected Node Real Telemetry Inspector */}
      <div className="p-5 rounded-2xl bg-[#06080E] border border-border-subtle space-y-4 shadow-inner">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2.5">
            <span className={`font-bold text-sm sm:text-base font-sans ${selectedAgent.textColor}`}>
              {selectedAgent.name}
            </span>
            <span className="text-text-secondary text-xs font-sans">({selectedAgent.role})</span>
          </div>

          {/* Inspector Tabs */}
          <div className="flex items-center gap-1 bg-surface-elevated p-1 rounded-xl border border-border-subtle">
            {[
              { id: "telemetry", label: "Live Telemetry" },
              { id: "spec", label: "Agent Persona" },
              { id: "capabilities", label: "Invariants" },
            ].map((tab) => {
              const isCur = inspectorTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setInspectorTab(tab.id as any)}
                  className={`relative px-3 py-1.5 text-xs rounded-lg transition-colors font-sans font-medium ${
                    isCur ? "text-cyan-400 font-semibold" : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  <span>{tab.label}</span>
                  {isCur && (
                    <motion.div
                      layoutId="activeInspectorTab"
                      className="absolute inset-0 bg-surface border border-cyan-500/30 rounded-lg -z-10 shadow-sm"
                      transition={{ type: "spring", stiffness: 350, damping: 30 }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {inspectorTab === "telemetry" && (
          <div>
            {isSimulating ? (
              <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/30 text-cyan-300 space-y-2">
                <div className="flex items-center gap-2 text-sm font-bold font-sans">
                  <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                  <span>{selectedAgent.name} executing in live simulation loop...</span>
                </div>
                <p className="text-xs text-text-secondary font-sans leading-relaxed">
                  Executing autonomous task: {selectedAgent.role}. Coordinating through LangGraph state machine with deterministic JSON schemas.
                </p>
              </div>
            ) : selectedEvent ? (
              <div className="space-y-3 text-xs font-sans">
                <div className="flex justify-between text-xs text-text-secondary font-mono">
                  <span>Event: <strong className="text-text-primary">{selectedEvent.event_type}</strong></span>
                  <span>Duration: {selectedEvent.duration_ms ? `${selectedEvent.duration_ms} ms` : "—"}</span>
                </div>
                <div className="p-3.5 rounded-xl bg-surface border border-border-subtle text-text-primary font-mono text-xs leading-relaxed">
                  {selectedEvent.message}
                </div>
                {selectedEvent.output_summary && (
                  <div className="text-xs text-text-secondary p-3 rounded-xl bg-surface-elevated border border-border-subtle">
                    <span className="text-text-muted font-bold">Output summary: </span>
                    {selectedEvent.output_summary}
                  </div>
                )}
              </div>
            ) : run ? (
              <div className="p-5 text-center text-text-muted text-xs sm:text-sm font-sans">
                No specific event record logged for {selectedAgent.name} in run {run.id.slice(0, 8)}… yet.
              </div>
            ) : (
              <div className="p-6 text-center text-text-secondary text-xs sm:text-sm font-sans flex flex-col items-center justify-center gap-2">
                <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
                <span>Backend agent loop is ready. Click <strong>&quot;Watch Agents Work&quot;</strong> to see the live workflow in action.</span>
              </div>
            )}
          </div>
        )}

        {inspectorTab === "spec" && (
          <div className="space-y-2 text-xs sm:text-sm font-sans">
            <span className="text-xs text-text-muted uppercase font-bold block font-mono">
              Autonomous System Instruction:
            </span>
            <p className="p-3.5 rounded-xl bg-surface border border-border-subtle text-text-secondary leading-relaxed">
              {selectedAgent.systemInstruction}
            </p>
          </div>
        )}

        {inspectorTab === "capabilities" && (
          <div className="space-y-2 text-xs sm:text-sm font-sans">
            <span className="text-xs text-text-muted uppercase font-bold block font-mono">
              Safety &amp; Architecture Invariants:
            </span>
            <div className="space-y-2">
              {selectedAgent.capabilities.map((cap, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl bg-surface border border-border-subtle flex items-center gap-2.5 text-text-secondary"
                >
                  <FileCheck className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>{cap}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
