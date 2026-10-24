"use client";

import React, { useState } from "react";
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
  bgColor: string;
  textColor: string;
  capabilities: string[];
  systemInstruction: string;
  icon: React.ComponentType<{ className?: string }>;
}

const AGENTS: AgentNodeDef[] = [
  {
    key: "planner",
    name: "Planner Agent",
    role: "Context Analysis & Structured Plan",
    color: "#A78BFA", // Ultraviolet
    borderColor: "border-ultraviolet/40",
    bgColor: "bg-ultraviolet/10",
    textColor: "text-ultraviolet",
    capabilities: [
      "Repository tree ingestion & token budgeting",
      "Root cause hypothesis synthesis",
      "Defect acceptance criteria formulation",
    ],
    systemInstruction:
      "Analyzes repository issue context and git trees to formulate a step-by-step resolution plan and explicit acceptance criteria.",
    icon: Brain,
  },
  {
    key: "coder",
    name: "Coder Agent",
    role: "Minimal Unified Diff Synthesis",
    color: "#D7FF64", // Forge Lime
    borderColor: "border-forge-lime/40",
    bgColor: "bg-forge-lime/10",
    textColor: "text-forge-lime",
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
    key: "tester",
    name: "Sandbox Tester",
    role: "Isolated Subprocess & AST Validation",
    color: "#65E4F3", // Ice Cyan
    borderColor: "border-cyan-ice/40",
    bgColor: "bg-cyan-ice/10",
    textColor: "text-cyan-ice",
    capabilities: [
      "Ephemeral Docker container isolation",
      "Python AST static syntax verification fallback",
      "Dynamic exit code validation (Exit 0 strictly required)",
    ],
    systemInstruction:
      "Applies the patch inside an isolated sandbox and runs test assertions to verify the defect is resolved with exit code 0.",
    icon: Terminal,
  },
  {
    key: "reviewer",
    name: "Reviewer Agent",
    role: "Static Analysis & Approval Gate",
    color: "#FFB454", // Amber
    borderColor: "border-amber-attention/40",
    bgColor: "bg-amber-attention/10",
    textColor: "text-amber-attention",
    capabilities: [
      "Independent multi-angle security review",
      "Secret & injection vulnerability audit",
      "Fail-closed cryptographic approval gate gating",
    ],
    systemInstruction:
      "Audits generated code against security policies, secret scanners, and regression hazards before enabling human approval.",
    icon: ShieldCheck,
  },
];

export function AgentFlowVisualization({
  run,
  events = [],
  stateSnapshot,
  className = "",
}: AgentFlowVisualizationProps) {
  const [selectedAgentKey, setSelectedAgentKey] = useState<string>("planner");
  const [inspectorTab, setInspectorTab] = useState<"telemetry" | "spec" | "capabilities">("telemetry");

  const getNodeStatus = (agentKey: string): NodeStatus => {
    if (!run) return "idle";

    const current = run.current_node?.toLowerCase() || "";
    const runStatus = run.status;

    // Check if currently running this node
    if (current.includes(agentKey)) {
      if (runStatus === "FAILED" || runStatus === "REJECTED") return "failed";
      if (runStatus === "AWAITING_APPROVAL" && agentKey === "reviewer") return "waiting";
      return "running";
    }

    // Determine lifecycle ordering
    const order = ["context", "planner", "coder", "tester", "reviewer", "approval"];
    const agentIndex = order.findIndex((k) => k.includes(agentKey));
    const currentIndex = order.findIndex((k) => current.includes(k));

    if (runStatus === "COMPLETED" || runStatus === "APPROVED") {
      return "completed";
    }

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

  const selectedAgent =
    AGENTS.find((a) => a.key === selectedAgentKey) || AGENTS[0];
  const selectedEvent = getAgentEvent(selectedAgent.key);
  const selectedStatus = getNodeStatus(selectedAgent.key);

  return (
    <div className={`p-6 rounded-3xl bg-surface/85 backdrop-blur-xl border border-border-subtle space-y-6 shadow-2xl ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-text-primary">
              Multi-Agent Orchestration Topology
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/30 font-semibold">
              LangGraph StateGraph
            </span>
          </div>
          <p className="text-[11px] text-text-muted font-mono mt-1">
            Click any agent node to inspect real stage events, LLM specifications, and execution telemetry.
          </p>
        </div>

        {run && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-elevated border border-border-subtle text-xs font-mono">
            <span className="text-text-muted">Target Run:</span>
            <span className="text-cyan-400 font-bold">{run.id.slice(0, 8)}…</span>
            <span className="text-text-secondary">({run.status})</span>
          </div>
        )}
      </div>

      {/* Connected 4-Agent Workflow Flowchart */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 relative">
        {AGENTS.map((agent, index) => {
          const Icon = agent.icon;
          const status = getNodeStatus(agent.key);
          const isSelected = selectedAgentKey === agent.key;
          const isRunning = status === "running";

          return (
            <motion.div
              key={agent.key}
              whileHover={{ scale: 1.025, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedAgentKey(agent.key)}
              className={`p-4 rounded-2xl border cursor-pointer transition-all relative overflow-hidden ${
                isSelected
                  ? `${agent.borderColor} bg-surface-elevated/90 shadow-xl ring-2 ring-cyan-400/20`
                  : "border-border-subtle bg-surface hover:border-border-strong hover:bg-surface-elevated/60"
              }`}
            >
              {/* Active selection badge */}
              {isSelected && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute -top-1.5 right-3 px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-gradient-to-r from-cyan-400 to-emerald-400 text-black uppercase shadow-sm"
                >
                  Inspecting
                </motion.span>
              )}

              {/* Running glow pulse */}
              {isRunning && (
                <div className="absolute inset-0 bg-cyan-400/5 animate-pulse pointer-events-none" />
              )}

              <div className="flex items-center justify-between mb-3">
                <div
                  className={`p-2.5 rounded-xl border border-border-subtle ${agent.bgColor} ${agent.textColor} shadow-inner`}
                >
                  <Icon className="w-5 h-5" />
                </div>

                {/* Node Status Badge */}
                <div className="flex items-center gap-1.5">
                  {status === "running" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-cyan-400 uppercase font-bold">
                      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                      ACTIVE
                    </span>
                  )}
                  {status === "completed" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 uppercase font-bold">
                      <CheckCircle2 className="w-3.5 h-3.5" /> DONE
                    </span>
                  )}
                  {status === "failed" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-rose-400 uppercase font-bold">
                      <AlertCircle className="w-3.5 h-3.5" /> FAIL
                    </span>
                  )}
                  {status === "waiting" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-amber-300 uppercase font-bold">
                      <Clock className="w-3.5 h-3.5" /> GATE
                    </span>
                  )}
                  {status === "idle" && (
                    <span className="text-[10px] font-mono text-text-muted uppercase">
                      IDLE
                    </span>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-text-primary font-mono tracking-tight">
                  {agent.name}
                </h4>
                <p className="text-[10px] text-text-muted font-mono mt-0.5 truncate">
                  {agent.role}
                </p>
              </div>

              {/* Stage Step Tag */}
              <div className="mt-3 pt-2.5 border-t border-border-subtle/70 flex items-center justify-between text-[10px] font-mono text-text-muted">
                <span>Stage 0{index + 2}</span>
                <span className="text-cyan-400 font-semibold uppercase">
                  {status}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Selected Node Real Telemetry Inspector */}
      <div className="p-5 rounded-2xl bg-[#06080E] border border-border-subtle space-y-4 font-mono text-xs shadow-inner">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle/80 pb-3">
          <div className="flex items-center gap-2">
            <span className={`font-bold text-sm ${selectedAgent.textColor}`}>
              {selectedAgent.name}
            </span>
            <span className="text-text-muted text-[11px]">({selectedAgent.role})</span>
          </div>

          {/* Inspector Tabs with Motion layoutId */}
          <div className="flex items-center gap-1 bg-surface-elevated/80 p-1 rounded-xl border border-border-subtle">
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
                  className={`relative px-2.5 py-1 text-[10px] rounded-lg transition-colors font-mono font-semibold ${
                    isCur ? "text-cyan-400" : "text-text-muted hover:text-text-primary"
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
            {selectedEvent ? (
              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-[11px] text-text-muted">
                  <span>Event: <strong className="text-text-primary">{selectedEvent.event_type}</strong></span>
                  <span>Duration: {selectedEvent.duration_ms ? `${selectedEvent.duration_ms} ms` : "—"}</span>
                </div>
                <div className="p-3 rounded-xl bg-surface border border-border-subtle text-text-primary leading-relaxed">
                  {selectedEvent.message}
                </div>
                {selectedEvent.output_summary && (
                  <div className="text-[11px] text-text-secondary p-2 rounded-lg bg-surface-elevated/40">
                    <span className="text-text-muted">Output summary: </span>
                    {selectedEvent.output_summary}
                  </div>
                )}
              </div>
            ) : run ? (
              <div className="p-4 text-center text-text-muted text-xs">
                No specific event record logged for {selectedAgent.name} in run {run.id.slice(0, 8)}… yet.
              </div>
            ) : (
              <div className="p-4 text-center text-text-muted text-xs flex flex-col items-center justify-center gap-1.5">
                <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
                <span>Backend agent loop is ready. Start a workflow to stream live node telemetry.</span>
              </div>
            )}
          </div>
        )}

        {inspectorTab === "spec" && (
          <div className="space-y-2 text-xs">
            <span className="text-[11px] text-text-muted uppercase font-bold block">
              Autonomous System Instruction:
            </span>
            <p className="p-3 rounded-xl bg-surface border border-border-subtle text-text-secondary leading-relaxed">
              {selectedAgent.systemInstruction}
            </p>
          </div>
        )}

        {inspectorTab === "capabilities" && (
          <div className="space-y-2 text-xs">
            <span className="text-[11px] text-text-muted uppercase font-bold block">
              Safety &amp; Architecture Invariants:
            </span>
            <div className="space-y-1.5">
              {selectedAgent.capabilities.map((cap, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-xl bg-surface border border-border-subtle flex items-center gap-2 text-text-secondary"
                >
                  <FileCheck className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
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
