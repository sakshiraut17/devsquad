"use client";

import React, { useState } from "react";
import {
  GitBranch,
  Layers,
  AlertTriangle,
  FileCheck2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { RepositoryContextSummary } from "@/types";
import { truncateHash } from "@/lib/utils";

interface RepositoryContextCardProps {
  context: RepositoryContextSummary | null | undefined;
}

export function RepositoryContextCard({ context }: RepositoryContextCardProps) {
  const [showFiles, setShowFiles] = useState(false);

  if (!context) {
    return null;
  }

  const selectedFiles = context.selected_files || {};
  const fileEntries = Object.entries(selectedFiles);

  return (
    <div className="p-5 rounded-lg bg-surface border border-border-subtle space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-forge-lime" />
          <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider">
            Repository Context &amp; Revision Provenance
          </h3>
        </div>

        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span>Branch: <span className="text-text-primary font-bold">{context.target_branch}</span></span>
          <span>•</span>
          <span>Base SHA: <span className="text-forge-lime">{truncateHash(context.base_commit_sha, 12)}</span></span>
        </div>
      </div>

      {/* Truncation Warning */}
      {context.truncation_applied && (
        <div className="p-3.5 rounded bg-amber-attention/15 border border-amber-attention/40 text-amber-attention text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold">REPOSITORY CONTEXT TRUNCATED TO BUDGET</p>
            <p className="text-[11px] text-text-secondary mt-0.5">
              The full repository size exceeded the context token budget ({context.total_token_count} / {context.context_window_limit} tokens). Only highest-ranked files are included.
            </p>
          </div>
        </div>
      )}

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Ranked Files</span>
          <span className="text-text-primary font-bold mt-0.5 block">
            {fileEntries.length} files
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Omitted / Unranked</span>
          <span className="text-text-muted font-bold mt-0.5 block">
            {context.unranked_files_count} files
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Token Footprint</span>
          <span className="text-cyan-ice font-bold mt-0.5 block">
            {context.total_token_count.toLocaleString()} tokens
          </span>
        </div>

        <div className="p-2.5 rounded bg-surface-elevated border border-border-subtle">
          <span className="text-[10px] text-text-muted uppercase block">Provenance State</span>
          <span className="text-semantic-success font-bold mt-0.5 block flex items-center gap-1">
            <FileCheck2 className="w-3.5 h-3.5" /> Bound to Commit
          </span>
        </div>
      </div>

      {/* Retrieval Limitations */}
      {context.retrieval_limitations && context.retrieval_limitations.length > 0 && (
        <div className="space-y-1 text-xs">
          <span className="text-[11px] text-text-muted uppercase tracking-wider block font-bold">
            Retrieval Boundary Limitations:
          </span>
          <ul className="list-disc list-inside text-text-secondary text-[11px] space-y-0.5 bg-surface-elevated/40 p-2.5 rounded border border-border-subtle">
            {context.retrieval_limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Ranked Files Table (Collapsible) */}
      {fileEntries.length > 0 && (
        <div className="space-y-1 pt-1">
          <button
            type="button"
            onClick={() => setShowFiles(!showFiles)}
            className="flex items-center justify-between w-full text-xs text-text-muted hover:text-text-primary font-bold uppercase tracking-wider py-1"
          >
            <span>Ranked Source Files &amp; Cryptographic SHA-256 Hashes ({fileEntries.length})</span>
            {showFiles ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showFiles && (
            <div className="p-2.5 rounded bg-[#0A0D0F] border border-border-subtle text-xs font-mono space-y-1 max-h-52 overflow-y-auto">
              {fileEntries.map(([path, fMeta]) => (
                <div
                  key={path}
                  className="flex items-center justify-between py-1 px-2 rounded hover:bg-surface-elevated/50 text-[11px]"
                >
                  <span className="text-text-primary font-bold truncate max-w-[60%]">
                    {path}
                  </span>
                  <div className="flex items-center gap-3 text-text-muted">
                    <span>{fMeta.total_lines} lines</span>
                    <span>sha: {truncateHash(fMeta.sha256, 10)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
