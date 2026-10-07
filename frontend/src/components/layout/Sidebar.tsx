import React from 'react';
import { Bot, FolderGit2, AlertCircle, PlayCircle, BarChart3, ShieldCheck } from 'lucide-react';

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-surface border-r border-border h-screen flex flex-col fixed left-0 top-0 z-20">
      {/* Brand Logo Header */}
      <div className="p-5 border-b border-border flex items-center space-x-3">
        <div className="p-2 bg-primary/20 text-primary rounded-lg">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-white tracking-wide">DevSquad</h1>
          <p className="text-xs text-muted">AI Engineering Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
        <a
          href="#"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium bg-primary/10 text-primary border border-primary/20"
        >
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-4 h-4" />
            <span>Dashboard</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-semibold">
            LIVE
          </span>
        </a>

        <a
          href="#"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-card transition-colors group"
        >
          <div className="flex items-center space-x-3">
            <FolderGit2 className="w-4 h-4" />
            <span>Repositories</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
            Roadmap
          </span>
        </a>

        <a
          href="#"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-card transition-colors group"
        >
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-4 h-4" />
            <span>GitHub Issues</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
            Roadmap
          </span>
        </a>

        <a
          href="#"
          className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-card transition-colors group"
        >
          <div className="flex items-center space-x-3">
            <PlayCircle className="w-4 h-4" />
            <span>Workflow Runs</span>
          </div>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700">
            Roadmap
          </span>
        </a>
      </nav>

      {/* Footer System Status */}
      <div className="p-4 border-t border-border bg-card/40">
        <div className="flex items-center justify-between text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Foundation Ready</span>
          </span>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-semibold">
            v0.1.0
          </span>
        </div>
      </div>
    </aside>
  );
};
