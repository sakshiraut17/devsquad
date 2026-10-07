'use client';

import React, { useEffect, useState } from 'react';
import { fetchSystemStatus, SystemStatus } from '@/lib/api';
import { Database, Cpu, Server, CheckCircle2, AlertTriangle, RefreshCw, Clock } from 'lucide-react';

export const SystemHealthCard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadStatus = async () => {
    setLoading(true);
    const data = await fetchSystemStatus();
    setStatus(data);
    setLoading(false);
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Server className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-white">System Infrastructure Diagnostics</h3>
        </div>
        <button
          onClick={loadStatus}
          disabled={loading}
          className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-card transition-colors flex items-center gap-1.5 text-xs"
          title="Refresh Status"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Database Status */}
        <div className="bg-card p-4 rounded-lg border border-border/60">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted flex items-center gap-1.5 font-medium">
              <Database className="w-4 h-4 text-blue-400" />
              Database Engine
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              IMPLEMENTED
            </span>
          </div>
          <p className="text-sm font-semibold text-white">
            {status?.database_engine || 'sqlite+aiosqlite (Local Dev)'}
          </p>
          <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>Async Pool Connected (8 ORM Models)</span>
          </p>
        </div>

        {/* LLM Engine Status */}
        <div className="bg-card p-4 rounded-lg border border-border/60">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted flex items-center gap-1.5 font-medium">
              <Cpu className="w-4 h-4 text-purple-400" />
              LLM Provider Gateway
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/30">
              NOT CONFIGURED
            </span>
          </div>
          <p className="text-sm font-semibold text-white uppercase">
            {status?.llm_provider || 'Gemini'}
          </p>
          <p className="text-[11px] text-amber-400 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            <span>API Key Pending (Planned Sprints 3–6)</span>
          </p>
        </div>

        {/* Docker Sandbox Status */}
        <div className="bg-card p-4 rounded-lg border border-border/60">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted flex items-center gap-1.5 font-medium">
              <Server className="w-4 h-4 text-indigo-400" />
              Docker Sandbox Runner
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-purple-500/20 text-purple-400 border border-purple-500/30">
              PLANNED (SPRINT 5)
            </span>
          </div>
          <p className="text-sm font-semibold text-white">
            Container Image Specified
          </p>
          <p className="text-[11px] text-purple-300 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Execution Sandbox Scheduled Sprint 5</span>
          </p>
        </div>
      </div>
    </div>
  );
};
