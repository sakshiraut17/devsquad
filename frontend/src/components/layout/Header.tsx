import React from 'react';
import { GitBranch, Layers, Github } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="h-16 bg-surface/80 backdrop-blur border-b border-border fixed top-0 right-0 left-64 z-10 flex items-center justify-between px-6">
      <div className="flex items-center space-x-4">
        <span className="text-sm font-semibold text-white">DevSquad Console</span>
        <span className="text-gray-600">/</span>
        <div className="flex items-center space-x-2 text-xs bg-card px-2.5 py-1 rounded-full text-muted border border-border">
          <GitBranch className="w-3.5 h-3.5 text-primary" />
          <span>v0.1.0-foundation (Sprint 1 Target)</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 px-3 py-1 rounded-full">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <span>LangGraph Engine: CONFIGURED</span>
        </div>
        
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="p-2 text-gray-400 hover:text-white transition-colors"
          title="GitHub Repository"
        >
          <Github className="w-5 h-5" />
        </a>
      </div>
    </header>
  );
};
