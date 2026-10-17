"use client";

import React, { useState } from "react";
import {
  Brain,
  Code2,
  Terminal,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Clock,
  Info,
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
    <div className={`p-5 rounded-lg bg-surface border border-border-subtle space-y-5 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-text-primary">
              Multi-Agent Orchestration Topology
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-elevated text-text-muted font-mono border border-border-subtle">
              LangGraph Core
            </span>
          </div>
          <p className="text-[11px] text-text-muted font-mono mt-0.5">
            Select an agent node to inspect real stage events, outputs, and execution telemetry.
          </p>
        </div>

        {run && (
          <div className="text-right text-xs font-mono">
            <span className="text-text-muted">Target Run: </span>
            <span className="text-forge-lime font-bold">{run.id.slice(0, 8)}…</span>
            <span className="text-text-secondary ml-2">({run.status})</span>
          </div>
        )}
      </div>

      {/* Connected 4-Agent Workflow Flowchart (SVG Connectors + Interactive Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 relative">
        {AGENTS.map((agent, index) => {
          const Icon = agent.icon;
          const status = getNodeStatus(agent.key);
          const isSelected = selectedAgentKey === agent.key;
          const isRunning = status === "running";

          return (
            <div
              key={agent.key}
              onClick={() => setSelectedAgentKey(agent.key)}
              className={`p-3.5 rounded-lg border cursor-pointer transition-all relative ${
                isSelected
                  ? `${agent.borderColor} bg-surface-elevated shadow-lg ring-1 ring-${agent.color}/30`
                  : "border-border-subtle bg-surface hover:border-border-strong hover:bg-surface-elevated/60"
              }`}
            >
              {/* Active selection dot in Forge Lime */}
              {isSelected && (
                <span className="absolute -top-1.5 right-3 px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-forge-lime text-black uppercase">
                  Inspecting
                </span>
              )}

              <div className="flex items-center justify-between mb-2">
                <div
                  className={`p-2 rounded border border-border-subtle ${agent.bgColor} ${agent.textColor}`}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Node Status Badge */}
                <div className="flex items-center gap-1.5">
                  {status === "running" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-forge-lime uppercase">
                      <span className="w-1.5 h-1.5 rounded-full bg-forge-lime animate-pulse" />
                      ACTIVE
                    </span>
                  )}
                  {status === "completed" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-semantic-success uppercase">
                      <CheckCircle2 className="w-3 h-3" /> DONE
                    </span>
                  )}
                  {status === "failed" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-semantic-danger uppercase">
                      <AlertCircle className="w-3 h-3" /> FAIL
                    </span>
                  )}
                  {status === "waiting" && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-amber-attention uppercase">
                      <Clock className="w-3 h-3" /> GATE
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
                <h4 className="text-xs font-semibold text-text-primary font-mono">
                  {agent.name}
                </h4>
                <p className="text-[10px] text-text-muted font-mono mt-0.5 truncate">
                  {agent.role}
                </p>
              </div>

              {/* Stage Step Tag */}
              <div className="mt-2.5 pt-2 border-t border-border-subtle/60 flex items-center justify-between text-[10px] font-mono text-text-muted">
                <span>Stage 0{index + 2}</span>
                <span className="text-text-secondary uppercase">
                  {status}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Node Real Telemetry Inspector */}
      <div className="p-4 rounded-lg bg-[#0E1114] border border-border-subtle space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-border-subtle/70 pb-2">
          <div className="flex items-center gap-2">
            <span className={`font-bold ${selectedAgent.textColor}`}>
              {selectedAgent.name} Telemetry
            </span>
            <span className="text-text-muted text-[11px]">({selectedAgent.role})</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-text-muted text-[11px]">Real Node State:</span>
            <span className="px-2 py-0.5 rounded bg-surface text-text-primary text-[10px] uppercase border border-border-subtle">
              {selectedStatus}
            </span>
          </div>
        </div>

        {selectedEvent ? (
          <div className="space-y-2 text-xs">
            <div className="flex justify-between text-[11px] text-text-muted">
              <span>Event: <strong className="text-text-primary">{selectedEvent.event_type}</strong></span>
              <span>Duration: {selectedEvent.duration_ms ? `${selectedEvent.duration_ms} ms` : "—"}</span>
            </div>
            <div className="p-2.5 rounded bg-surface border border-border-subtle text-text-primary leading-relaxed">
              {selectedEvent.message}
            </div>
            {selectedEvent.output_summary && (
              <div className="text-[11px] text-text-secondary">
                <span className="text-text-muted">Output summary: </span>
                {selectedEvent.output_summary}
              </div>
            )}
          </div>
        ) : run ? (
          <div className="p-3 text-center text-text-muted text-[11px]">
            No specific event record logged for {selectedAgent.name} in run {run.id.slice(0, 8)}… yet.
          </div>
        ) : (
          <div className="p-3 text-center text-text-muted text-[11px]">
            Backend is currently idle. Start a workflow or select an existing run to stream live node telemetry.
          </div>
        )}
      </div>
    </div>
  );
}
