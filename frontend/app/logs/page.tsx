"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Radio, Filter, Terminal } from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { api } from "@/lib/api/client";
import { AgentEvent } from "@/types";
import { formatDate } from "@/lib/utils";

interface EventWithRun extends AgentEvent {
  run_status?: string;
}

export default function ActivityStreamPage() {
  const [events, setEvents] = useState<EventWithRun[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const runs = await api.getRuns();
      const allEvents: EventWithRun[] = [];

      for (const run of runs) {
        try {
          const runEvents = await api.getRunEvents(run.id);
          for (const ev of runEvents) {
            allEvents.push({ ...ev, run_status: run.status });
          }
        } catch {
          // Skip runs without events
        }
      }

      // Chronological sort descending
      allEvents.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setEvents(allEvents);
    } catch (err: any) {
      setError(err?.message || "Failed to load activity stream");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredEvents =
    selectedAgent === "ALL"
      ? events
      : events.filter((e) => e.agent_name.toLowerCase() === selectedAgent.toLowerCase());

  const getAgentBadge = (agent: string) => {
    switch (agent.toLowerCase()) {
      case "human_gatekeeper":
        return "bg-semantic-success/15 text-semantic-success border-semantic-success/30 font-bold";
      case "reviewer":
        return "bg-amber-attention/15 text-amber-attention border-amber-attention/30 font-semibold";
      case "tester":
        return "bg-cyan-ice/15 text-cyan-ice border-cyan-ice/30";
      case "coder":
        return "bg-forge-lime/15 text-forge-lime border-forge-lime/30";
      case "planner":
        return "bg-ultraviolet/15 text-ultraviolet border-ultraviolet/30";
      default:
        return "bg-surface-elevated text-forge-lime border-border-subtle";
    }
  };

  const getEventSemanticType = (agent: string, eventType: string) => {
    if (agent.toLowerCase() === "reviewer" && eventType === "patch_approved") {
      return "ai_review_recommendation (approve)";
    }
    if (agent.toLowerCase() === "human_gatekeeper") {
      return `${eventType} (human gate)`;
    }
    return eventType;
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      <Navbar onRefresh={loadLogs} title="Activity Stream" subtitle="Sanitized Agent Telemetry & Event Audit Log" />

      <main className="p-6 max-w-7xl w-full mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
          <div>
            <h2 className="text-sm font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
              <Radio className="w-4 h-4 text-forge-lime animate-pulse" />
              Live Sanitized Event Stream
            </h2>
            <p className="text-xs text-text-muted font-mono mt-0.5">
              Secret scrubbing active: API keys, tokens, and authorization headers are redacted before emission.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-text-muted" />
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="text-xs font-mono bg-surface border border-border-subtle rounded px-2.5 py-1.5 text-text-primary focus:outline-none focus:border-forge-lime"
            >
              <option value="ALL">All Agents &amp; Gates</option>
              <option value="context_ranker">Context Ranker</option>
              <option value="planner">Planner Agent</option>
              <option value="coder">Coder Agent</option>
              <option value="tester">Tester Agent</option>
              <option value="reviewer">Reviewer Agent (AI Advisory)</option>
              <option value="repair_gatekeeper">Repair Gatekeeper</option>
              <option value="human_gatekeeper">Human Gatekeeper (Sign-Off)</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded bg-semantic-danger/10 border border-semantic-danger/30 text-semantic-danger text-xs font-mono">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            <div className="h-16 bg-surface animate-pulse rounded border border-border-subtle" />
            <div className="h-16 bg-surface animate-pulse rounded border border-border-subtle" />
            <div className="h-16 bg-surface animate-pulse rounded border border-border-subtle" />
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-text-muted bg-surface border border-border-subtle rounded-lg">
            No agent events recorded in telemetry stream.
          </div>
        ) : (
          <div className="bg-surface border border-border-subtle rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono text-left">
                <thead>
                  <tr className="border-b border-border-subtle bg-surface-elevated/80 text-text-muted uppercase text-[10px]">
                    <th className="py-2.5 px-4">Timestamp</th>
                    <th className="py-2.5 px-4">Agent / Service</th>
                    <th className="py-2.5 px-4">Event Type</th>
                    <th className="py-2.5 px-4">Workflow Run</th>
                    <th className="py-2.5 px-4">Sanitized Telemetry</th>
                    <th className="py-2.5 px-4 text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {filteredEvents.map((ev) => (
                    <tr key={ev.id} className="hover:bg-surface-elevated/40 transition-colors">
                      <td className="py-3 px-4 text-text-muted whitespace-nowrap text-[11px]">
                        {formatDate(ev.created_at)}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded border text-[10px] uppercase ${getAgentBadge(ev.agent_name)}`}>
                          {ev.agent_name.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-semibold text-text-secondary">
                        <span className={ev.agent_name === "human_gatekeeper" ? "text-semantic-success" : ""}>
                          {getEventSemanticType(ev.agent_name, ev.event_type)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-forge-lime font-semibold">
                        <Link href={`/runs/${ev.run_id}`} className="hover:underline">
                          {ev.run_id.slice(0, 8)}…
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-text-primary max-w-md truncate" title={ev.message}>
                        {ev.message}
                      </td>
                      <td className="py-3 px-4 text-right text-text-muted whitespace-nowrap text-[11px]">
                        {ev.duration_ms ? `${ev.duration_ms} ms` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
