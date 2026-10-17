"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface DiffViewerProps {
  diff: string;
  filename?: string;
  className?: string;
}

export function DiffViewer({ diff, filename, className }: DiffViewerProps) {
  if (!diff || !diff.trim()) {
    return (
      <div className="p-6 text-center text-xs text-text-muted font-mono bg-surface-elevated/40 rounded border border-border-subtle">
        No unified diff content available for this revision.
      </div>
    );
  }

  const lines = diff.split("\n");

  return (
    <div className={cn("rounded-lg border border-border-subtle overflow-hidden bg-[#0A0C0E]", className)}>
      {filename && (
        <div className="px-4 py-2 border-b border-border-subtle bg-surface flex items-center justify-between text-xs font-mono text-text-primary">
          <span className="font-semibold text-forge-lime">{filename}</span>
          <span className="text-text-muted text-[11px]">{lines.length} lines</span>
        </div>
      )}

      <div className="overflow-x-auto text-xs font-mono p-2">
        <table className="w-full border-collapse">
          <tbody>
            {lines.map((line, idx) => {
              const isAdded = line.startsWith("+") && !line.startsWith("+++");
              const isRemoved = line.startsWith("-") && !line.startsWith("---");
              const isHunkHeader = line.startsWith("@@");
              const isFileHeader = line.startsWith("diff") || line.startsWith("---") || line.startsWith("+++");

              let rowBg = "hover:bg-surface-elevated/40";
              let textColor = "text-text-primary";

              if (isAdded) {
                rowBg = "bg-semantic-success/10 hover:bg-semantic-success/20";
                textColor = "text-semantic-success";
              } else if (isRemoved) {
                rowBg = "bg-semantic-danger/10 hover:bg-semantic-danger/20";
                textColor = "text-semantic-danger";
              } else if (isHunkHeader) {
                rowBg = "bg-ultraviolet/10";
                textColor = "text-ultraviolet";
              } else if (isFileHeader) {
                textColor = "text-text-muted font-semibold";
              }

              return (
                <tr key={idx} className={cn("transition-colors select-text", rowBg)}>
                  <td className="w-10 text-right pr-3 select-none text-text-muted border-r border-border-subtle text-[11px] align-top py-0.5">
                    {idx + 1}
                  </td>
                  <td className={cn("pl-4 pr-2 py-0.5 whitespace-pre font-mono text-left", textColor)}>
                    {line || " "}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
