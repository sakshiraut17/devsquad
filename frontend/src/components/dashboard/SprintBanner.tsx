import React from 'react';
import { Rocket, CheckCircle2, Layers, Database } from 'lucide-react';

export const SprintBanner: React.FC = () => {
  return (
    <div className="bg-gradient-to-r from-blue-900/40 via-surface to-surface border border-blue-500/30 rounded-xl p-6 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
        <Rocket className="w-48 h-48 text-blue-400" />
      </div>

      <div className="relative z-10 max-w-3xl">
        <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-blue-400 mb-2">
          <span className="px-2.5 py-0.5 rounded-full bg-blue-500/20 border border-blue-500/30 font-bold">
            Sprint 1 (Days 1–6)
          </span>
          <span>•</span>
          <span className="text-emerald-400 font-bold">Foundation & Architecture — COMPLETED</span>
        </div>

        <h2 className="text-2xl font-bold text-white mb-2">
          DevSquad Autonomous AI Software Engineering Team
        </h2>

        <p className="text-sm text-gray-300 leading-relaxed mb-4">
          Sprint 1 checkpoint verified for professor evaluation. Monorepo architecture established with FastAPI async REST API server, SQLAlchemy 2.0 ORM database layer, LangGraph state engine configuration, and Next.js 14 dashboard UI.
        </p>

        <div className="flex flex-wrap gap-3 text-xs font-medium">
          <div className="flex items-center gap-1.5 bg-card px-3 py-1.5 rounded-lg border border-emerald-500/30 text-emerald-400">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>FastAPI Async Server (IMPLEMENTED)</span>
          </div>

          <div className="flex items-center gap-1.5 bg-card px-3 py-1.5 rounded-lg border border-blue-500/30 text-blue-400">
            <Layers className="w-4 h-4 text-blue-400" />
            <span>LangGraph Schema (CONFIGURED)</span>
          </div>

          <div className="flex items-center gap-1.5 bg-card px-3 py-1.5 rounded-lg border border-purple-500/30 text-purple-300">
            <Database className="w-4 h-4 text-purple-400" />
            <span>8 ORM Models (FOUNDATION READY)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
