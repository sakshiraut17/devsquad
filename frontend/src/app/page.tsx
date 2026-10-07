import React from 'react';
import { SprintBanner } from '@/components/dashboard/SprintBanner';
import { SystemHealthCard } from '@/components/dashboard/SystemHealthCard';
import { GitPullRequest, ShieldCheck, Terminal, Layers } from 'lucide-react';

export default function DashboardHome() {
  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <SprintBanner />

      {/* Infrastructure Health Status */}
      <SystemHealthCard />

      {/* Agent Workflow Architecture Overview */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">Multi-Agent Workflow Architecture Roadmap</h3>
          <span className="text-xs text-muted">LangGraph Execution Loop</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Planner Node Card */}
          <div className="bg-surface border border-border p-5 rounded-xl hover:border-blue-500/50 transition-colors relative">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-lg">
                <Layers className="w-5 h-5" />
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-blue-500/20 text-blue-400 border border-blue-500/30">
                PLANNED
              </span>
            </div>
            <h4 className="font-semibold text-white mb-1">1. Planner Subsystem</h4>
            <p className="text-xs text-muted leading-relaxed">
              Analyzes GitHub issue context and repository file trees to formulate structured task lists and acceptance criteria.
            </p>
          </div>

          {/* Coder Node Card */}
          <div className="bg-surface border border-border p-5 rounded-xl hover:border-emerald-500/50 transition-colors relative">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-lg">
                <Terminal className="w-5 h-5" />
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                PLANNED
              </span>
            </div>
            <h4 className="font-semibold text-white mb-1">2. Coder Subsystem</h4>
            <p className="text-xs text-muted leading-relaxed">
              Synthesizes syntactically valid code diff patches and targeted unit tests matching codebase conventions.
            </p>
          </div>

          {/* Tester Node Card */}
          <div className="bg-surface border border-border p-5 rounded-xl hover:border-purple-500/50 transition-colors relative">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 bg-purple-500/10 text-purple-400 rounded-lg">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-purple-500/20 text-purple-400 border border-purple-500/30">
                PLANNED
              </span>
            </div>
            <h4 className="font-semibold text-white mb-1">3. Tester Subsystem</h4>
            <p className="text-xs text-muted leading-relaxed">
              Executes tests inside isolated Docker Sandbox containers, parsing tracebacks for auto-repair loops.
            </p>
          </div>

          {/* Reviewer Node Card */}
          <div className="bg-surface border border-border p-5 rounded-xl hover:border-amber-500/50 transition-colors relative">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-lg">
                <GitPullRequest className="w-5 h-5" />
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                PLANNED
              </span>
            </div>
            <h4 className="font-semibold text-white mb-1">4. Reviewer Subsystem</h4>
            <p className="text-xs text-muted leading-relaxed">
              Evaluates security, code quality, and criteria compliance before human PR approval.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
