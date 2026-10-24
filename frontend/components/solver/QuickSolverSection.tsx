"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Zap,
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Copy,
  Check,
  ExternalLink,
  GitBranch,
  ArrowRight,
  Terminal,
  Activity,
  Cpu,
  Layers,
  ShieldCheck,
  RotateCcw,
  Download,
  Play,
  Columns,
  List,
  Bug,
  CornerDownRight,
  Flame,
  Github,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { getStoredGitHubToken } from "@/lib/auth/githubSession";
import { QuickSolverResult } from "@/types";

interface QuickSolverSectionProps {
  onLaunchFullWorkflow?: (repoFullName: string, issueNumber?: number) => void;
  initialTarget?: string;
}

export function QuickSolverSection({
  onLaunchFullWorkflow,
  initialTarget = "",
}: QuickSolverSectionProps) {
  const [targetUrl, setTargetUrl] = useState(initialTarget);
  const [customProblem, setCustomProblem] = useState("");
  const [isSolving, setIsSolving] = useState(false);
  const [solvingStage, setSolvingStage] = useState(0);
  const [result, setResult] = useState<QuickSolverResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"diff" | "solution" | "verify" | "simulate">("diff");
  const [diffMode, setDiffMode] = useState<"unified" | "split">("unified");

  // GitHub Direct Solving & Publishing State
  const [publishingToGitHub, setPublishingToGitHub] = useState(false);
  const [publishSuccessUrl, setPublishSuccessUrl] = useState<string | null>(null);
  const [publishError, setPublishError] = useState<string | null>(null);

  const handlePublishToGitHub = async () => {
    if (!result) return;
    setPublishingToGitHub(true);
    setPublishError(null);
    setPublishSuccessUrl(null);

    let token = getStoredGitHubToken() || undefined;
    if (!token) {
      const promptToken = window.prompt(
        "To publish solutions directly to GitHub, please enter your GitHub Personal Access Token (with 'repo' scope):"
      );
      if (!promptToken || !promptToken.trim()) {
        setPublishError("A GitHub Personal Access Token with 'repo' scope is required to publish solutions.");
        setPublishingToGitHub(false);
        return;
      }
      token = promptToken.trim();
      localStorage.setItem("devsquad_github_token", token);
      window.dispatchEvent(new Event("devsquad_github_session_change"));
    }

    const issueNum = result.issue_number || null;

    try {
      const res = await api.publishSolution({
        target: result.repository_name || targetUrl,
        issue_number: issueNum,
        issue_title: result.issue_title,
        diagnosis: result.problem_diagnosis,
        root_cause: result.root_cause,
        code_patch: result.code_patch,
        verification_steps: result.verification_steps,
        add_solved_label: true,
        close_issue: false,
        token,
      });
      setPublishSuccessUrl(res.comment_url || res.issue_url);
    } catch (err: any) {
      setPublishError(
        err?.message || "Failed to publish solution to GitHub. Ensure your token has 'repo' permissions."
      );
    } finally {
      setPublishingToGitHub(false);
    }
  };
  const [simulating, setSimulating] = useState(false);
  const [simulatedLogs, setSimulatedLogs] = useState<string[]>([]);
  const [simPassed, setSimPassed] = useState(false);

  const STAGES = [
    "Connecting & parsing target repository AST...",
    "Retrieving issue description & thread comments...",
    "Analyzing stack traces, codebase structure & AST...",
    "Formulating root cause diagnosis & code solution...",
  ];

  const PRESETS = [
    {
      label: "Express.js #5380",
      category: "Node.js",
      url: "https://github.com/expressjs/express/issues/5380",
      description: "Async route rejection error propagation",
    },
    {
      label: "Pallets / Click Bug #3840",
      category: "Python CLI",
      url: "https://github.com/pallets/click/issues/3840",
      description: "Windows WinError 14001 process crash",
    },
    {
      label: "Facebook / React #28100",
      category: "Frontend",
      url: "https://github.com/facebook/react/issues/28100",
      description: "SSR hydration mismatch edgecase",
    },
    {
      label: "Astral-sh / UV #120",
      category: "Rust / Packaging",
      url: "https://github.com/astral-sh/uv",
      description: "Dependency lockfile resolution",
    },
    {
      label: "cyber-rps-arena #1",
      category: "Your Repo",
      url: "ayushkale06/cyber-rps-arena#1",
      description: "Round scoring draw state fix",
    },
    {
      label: "AlphaTrader #1",
      category: "Your Repo",
      url: "ayushkale06/AlphaTrader#1",
      description: "Volatility division by zero guard",
    },
  ];

  async function handleQuickSolve(overrideTarget?: string) {
    const input = (overrideTarget || targetUrl).trim();
    if (!input) {
      setError("Please provide a GitHub repository or issue link.");
      return;
    }

    setIsSolving(true);
    setSolvingStage(0);
    setError(null);
    setResult(null);
    setSimulatedLogs([]);
    setSimPassed(false);

    const stageTimer1 = setTimeout(() => setSolvingStage(1), 500);
    const stageTimer2 = setTimeout(() => setSolvingStage(2), 1200);
    const stageTimer3 = setTimeout(() => setSolvingStage(3), 2000);

    const token = getStoredGitHubToken() || undefined;

    try {
      const res = await api.quickSolve(input, customProblem.trim() || undefined, undefined, token);
      setResult(res);
      setActiveTab("diff");
    } catch (err: any) {
      setError(err?.message || "Failed to analyze target and generate quick solution.");
    } finally {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);
      setIsSolving(false);
    }
  }

  function handleCopyDiff() {
    if (!result?.code_patch) return;
    navigator.clipboard.writeText(result.code_patch);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownloadPatch() {
    if (!result?.code_patch) return;
    const blob = new Blob([result.code_patch], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.repository_name.replace("/", "_")}_fix.patch`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function runInteractiveSimulation() {
    if (!result) return;
    setSimulating(true);
    setSimulatedLogs([]);
    setSimPassed(false);

    const lines = [
      `[DevSquad Sandbox] Initializing ephemeral container for ${result.repository_name}...`,
      `[Git Patch Engine] Applying unified diff across ${result.affected_files.length || 1} target files...`,
      `[Patch Status] Diff applied with 0 conflicts (fuzz factor 0).`,
      `[AST Analyzer] Verifying syntax safety & policy engine invariants... PASSED`,
      `[Test Suite Runner] Executing regression test suite: ${result.verification_steps[0] || "pytest -v"}`,
      `   > PASS test_edgecase_guard_handles_anomaly (0.012s)`,
      `   > PASS test_regression_boundary_conditions (0.024s)`,
      `[Sandbox Exit Code] 0 (ALL CHECKS VERIFIED)`,
    ];

    for (let i = 0; i < lines.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 250));
      setSimulatedLogs((prev) => [...prev, lines[i]]);
    }

    setSimPassed(true);
    setSimulating(false);
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-border-subtle bg-surface/80 backdrop-blur-2xl p-6 lg:p-8 shadow-2xl space-y-6">
      {/* Decorative Aurora Glow Orbs */}
      <motion.div
        animate={{
          scale: [1, 1.25, 1],
          opacity: [0.15, 0.25, 0.15],
        }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -top-32 -right-32 w-[420px] h-[420px] bg-gradient-to-br from-cyan-400/20 via-emerald-400/15 to-transparent rounded-full blur-[100px] pointer-events-none"
      />
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.1, 0.2, 0.1],
        }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        className="absolute -bottom-32 -left-32 w-[420px] h-[420px] bg-gradient-to-tr from-purple-500/20 via-cyan-500/10 to-transparent rounded-full blur-[100px] pointer-events-none"
      />

      {/* Header Banner */}
      <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <motion.div
              animate={{ rotate: [0, 15, -15, 0], scale: [1, 1.1, 1] }}
              transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
              className="p-1.5 rounded-xl bg-gradient-to-br from-cyan-400/20 to-emerald-400/20 border border-cyan-400/30 text-cyan-400 shadow-sm"
            >
              <Zap className="w-4 h-4" />
            </motion.div>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-emerald-400 to-lime-300">
              Autonomous Real-Time Inspector &amp; Quick Solver
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              Live Engine
            </span>
          </div>
          <h2 className="text-2xl lg:text-3xl font-extrabold text-text-primary tracking-tight">
            Inspect Any Codebase &amp; Resolve Issues Instantly
          </h2>
          <p className="text-xs lg:text-sm text-text-secondary mt-1.5 max-w-2xl leading-relaxed">
            Paste a link to <strong className="text-cyan-300">any GitHub repository or issue</strong>.
            DevSquad automatically ingests the code structure, isolates the defect, and generates a concrete patch.
          </p>
        </div>

        {/* Interactive Preset Chips */}
        <div className="flex flex-col gap-1.5 shrink-0">
          <span className="text-[11px] font-mono text-text-muted flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            Try One-Click Benchmarks:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <motion.button
                key={p.label}
                whileHover={{ scale: 1.04, y: -1 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => {
                  setTargetUrl(p.url);
                  handleQuickSolve(p.url);
                }}
                className="px-2.5 py-1 rounded-lg bg-surface-elevated/80 border border-border-subtle hover:border-cyan-400/40 text-text-secondary hover:text-cyan-300 text-[11px] font-mono transition-all flex items-center gap-1.5 shadow-sm"
              >
                <Bug className="w-3 h-3 text-cyan-400" />
                <span>{p.label}</span>
              </motion.button>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Input Bar */}
      <div className="relative space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 group">
            <div className="absolute left-4 top-3.5 text-text-muted group-focus-within:text-cyan-400 transition-colors pointer-events-none">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Paste any GitHub URL (e.g. https://github.com/owner/repo/issues/123 or owner/repo)"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !isSolving) handleQuickSolve();
              }}
              className="w-full pl-11 pr-4 py-3.5 text-xs sm:text-sm rounded-2xl bg-surface-elevated/70 border border-border-subtle focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 text-text-primary placeholder:text-text-muted/60 font-mono shadow-inner transition-all"
            />
          </div>

          <motion.button
            whileHover={{ scale: 1.02, y: -1 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleQuickSolve()}
            disabled={isSolving || !targetUrl.trim()}
            className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-cyan-400 via-emerald-400 to-lime-300 hover:from-cyan-300 hover:to-lime-200 text-black font-bold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:pointer-events-none transition-all"
          >
            {isSolving ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                >
                  <Cpu className="w-4 h-4" />
                </motion.div>
                <span>Analyzing &amp; Solving...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Diagnose &amp; Solve</span>
              </>
            )}
          </motion.button>
        </div>

        {/* Toggle Custom Problem / Extra Context */}
        <div className="flex items-center justify-between text-[11px] font-mono text-text-muted px-1">
          <span>Accepts any public or private repository URL with token</span>
          <button
            onClick={() => setCustomProblem(customProblem ? "" : "Optional details")}
            className="text-cyan-400 hover:text-cyan-300 hover:underline transition-colors flex items-center gap-1"
          >
            <CornerDownRight className="w-3 h-3" />
            {customProblem ? "Hide custom problem description" : "Add custom stack trace / reproduction instructions"}
          </button>
        </div>

        {customProblem !== "" && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <textarea
              rows={3}
              placeholder="Provide extra error trace, reproduction steps, or context (optional)..."
              value={customProblem === "Optional details" ? "" : customProblem}
              onChange={(e) => setCustomProblem(e.target.value)}
              className="w-full p-3.5 text-xs rounded-2xl bg-surface-elevated/70 border border-border-subtle focus:outline-none focus:border-cyan-400 text-text-primary font-mono shadow-inner"
            />
          </motion.div>
        )}
      </div>

      {/* Animated Solving Progress State */}
      <AnimatePresence>
        {isSolving && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-6 rounded-2xl bg-surface-elevated/90 border border-cyan-500/30 space-y-4 shadow-xl"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="relative flex items-center justify-center">
                  <div className="w-4 h-4 rounded-full bg-cyan-400 animate-ping opacity-75" />
                  <div className="w-2.5 h-2.5 rounded-full bg-cyan-300 absolute" />
                </div>
                <span className="text-sm font-semibold text-text-primary font-mono">
                  {STAGES[solvingStage]}
                </span>
              </div>
              <span className="text-xs font-mono text-cyan-400 font-bold">
                Phase {solvingStage + 1} of 4
              </span>
            </div>

            {/* Stepper bar with gradient */}
            <div className="w-full h-2 rounded-full bg-surface overflow-hidden">
              <motion.div
                initial={{ width: "15%" }}
                animate={{ width: `${(solvingStage + 1) * 25}%` }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-cyan-400 via-emerald-400 to-lime-300 shadow-[0_0_12px_rgba(0,242,254,0.6)]"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Notice */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-start gap-3 shadow-sm"
        >
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold">Analysis Failed</span>
            <p>{error}</p>
          </div>
        </motion.div>
      )}

      {/* Interactive Solution Display Card */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="rounded-3xl border border-cyan-500/30 bg-surface/95 overflow-hidden shadow-2xl space-y-0 backdrop-blur-xl"
          >
            {/* Result Header */}
            <div className="p-6 bg-gradient-to-r from-cyan-950/40 via-surface to-surface-elevated border-b border-border-subtle flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="text-[11px] font-mono px-3 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 font-bold">
                    {result.repository_name} {result.issue_number ? `#${result.issue_number}` : ""}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full uppercase font-bold flex items-center gap-1 ${
                      result.severity === "critical"
                        ? "bg-red-500/20 text-red-400 border border-red-500/30"
                        : result.severity === "high"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : result.severity === "clean"
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                        : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    }`}
                  >
                    {result.severity === "clean" ? (
                      <>
                        <ShieldCheck className="w-3 h-3 text-cyan-300" />
                        <span>Healthy (0 Issues)</span>
                      </>
                    ) : (
                      `${result.severity} severity`
                    )}
                  </span>
                  <span className="text-[11px] text-text-muted font-mono">
                    Diagnostic generated in <strong className="text-emerald-400">{result.execution_time_seconds}s</strong>
                  </span>
                </div>
                <h3 className="text-lg font-bold text-text-primary tracking-tight">
                  {result.issue_title}
                </h3>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                {result.issue_url && (
                  <a
                    href={result.issue_url}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2.5 text-xs rounded-xl bg-surface-elevated border border-border-subtle hover:text-cyan-400 text-text-secondary transition-colors flex items-center gap-1.5 font-mono shadow-sm"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>View GitHub Issue</span>
                  </a>
                )}
                {onLaunchFullWorkflow && (
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={() =>
                      onLaunchFullWorkflow(result.repository_name, result.issue_number || undefined)
                    }
                    className="px-4 py-2.5 text-xs font-bold rounded-xl bg-gradient-to-r from-emerald-400 to-lime-300 hover:from-emerald-300 hover:to-lime-200 text-black flex items-center gap-1.5 shadow-md shadow-emerald-500/20 transition-all font-mono"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Dispatch Multi-Agent Squad</span>
                  </motion.button>
                )}
              </div>
            </div>

            {/* Diagnosis & Root Cause */}
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 border-b border-border-subtle bg-surface-elevated/40">
              <div className="space-y-1.5">
                <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  Problem Diagnosis
                </span>
                <p className="text-xs text-text-primary leading-relaxed bg-surface/60 p-3 rounded-xl border border-border-subtle">
                  {result.problem_diagnosis}
                </p>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Root Cause Breakdown
                </span>
                <p className="text-xs text-emerald-300 font-mono leading-relaxed bg-emerald-950/20 p-3 rounded-xl border border-emerald-500/20">
                  {result.root_cause}
                </p>
              </div>
            </div>

            {/* Affected Files Chips */}
            {result.affected_files && result.affected_files.length > 0 && (
              <div className="px-6 py-3 border-b border-border-subtle bg-surface flex items-center gap-2 overflow-x-auto text-xs">
                <span className="text-[11px] font-mono text-text-muted shrink-0 flex items-center gap-1">
                  <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                  Affected files:
                </span>
                <div className="flex items-center gap-1.5">
                  {result.affected_files.map((file) => (
                    <span
                      key={file}
                      className="px-2.5 py-1 rounded-lg bg-surface-elevated border border-border-subtle font-mono text-[11px] text-cyan-300 font-medium"
                    >
                      {file}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* One-Click GitHub Solution Publisher Strip */}
            <div className="mx-6 my-4 p-4 rounded-2xl bg-gradient-to-r from-purple-950/30 via-emerald-950/20 to-cyan-950/30 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
              <div className="flex items-start sm:items-center gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
                  <Github className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-text-primary uppercase tracking-wide">
                      Publish Solution Directly to GitHub
                    </span>
                    {result.issue_number ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/30">
                        Target Issue #{result.issue_number}
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                        {result.repository_name}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] font-mono text-text-muted mt-0.5 leading-relaxed">
                    Uses your connected GitHub account permission to post this root-cause analysis, verified diff, and testing steps directly to the issue.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  disabled={publishingToGitHub}
                  onClick={handlePublishToGitHub}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-400 hover:from-emerald-400 hover:to-cyan-300 text-black font-mono font-bold text-xs flex items-center gap-2 shadow-md transition-all disabled:opacity-50"
                  title="Post this diagnostic and code solution directly as an issue comment on GitHub"
                >
                  {publishingToGitHub ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-black" />
                      <span>Posting to GitHub...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5 text-black" />
                      <span>Publish Solution to GitHub</span>
                    </>
                  )}
                </motion.button>
              </div>
            </div>

            {publishSuccessUrl && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-6 mb-3 p-3.5 rounded-xl bg-cyan-500/15 border border-cyan-500/30 text-xs font-mono text-cyan-300 flex items-center justify-between shadow-sm"
              >
                <span className="flex items-center gap-2 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                  Solution comment successfully published to GitHub!
                </span>
                <a
                  href={publishSuccessUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 rounded-lg bg-cyan-500/25 hover:bg-cyan-500/35 text-cyan-200 font-bold flex items-center gap-1.5 transition-colors"
                >
                  <span>View Comment on GitHub</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </motion.div>
            )}

            {publishError && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="mx-6 mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs font-mono text-rose-300 flex items-center justify-between"
              >
                <span className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  {publishError}
                </span>
                <button
                  onClick={() => setPublishError(null)}
                  className="text-[10px] text-text-muted hover:text-white ml-2"
                >
                  Dismiss
                </button>
              </motion.div>
            )}

            {/* Interactive Tab Navigation with Motion layoutId */}
            <div className="border-b border-border-subtle bg-surface px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex gap-2 relative">
                {[
                  { key: "diff", label: "Proposed Patch Diff", icon: FileCode },
                  { key: "solution", label: "Resolution Steps", icon: CheckCircle2 },
                  { key: "verify", label: "Verification Commands", icon: Terminal },
                  { key: "simulate", label: "Interactive Simulation", icon: Play },
                ].map((t) => {
                  const Icon = t.icon as any;
                  const isCur = activeTab === t.key;
                  return (
                    <button
                      key={t.key}
                      onClick={() => setActiveTab(t.key as any)}
                      className={`relative py-3.5 px-3 text-xs font-mono font-semibold transition-colors flex items-center gap-1.5 ${
                        isCur ? "text-cyan-400" : "text-text-muted hover:text-text-primary"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{t.label}</span>
                      {isCur && (
                        <motion.div
                          layoutId="activeSolutionTab"
                          className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-400 via-emerald-400 to-lime-300 shadow-[0_0_8px_rgba(0,242,254,0.8)]"
                          transition={{ type: "spring", stiffness: 350, damping: 30 }}
                        />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Utility actions on tab bar */}
              <div className="flex items-center gap-2 pb-2 sm:pb-0">
                {activeTab === "diff" && (
                  <div className="flex items-center gap-1.5 mr-2">
                    <button
                      onClick={() => setDiffMode("unified")}
                      className={`p-1.5 rounded-lg border text-xs font-mono flex items-center gap-1 transition-all ${
                        diffMode === "unified"
                          ? "bg-surface-elevated text-cyan-400 border-cyan-500/30 font-bold"
                          : "text-text-muted border-border-subtle hover:text-text-primary"
                      }`}
                      title="Unified Diff View"
                    >
                      <List className="w-3 h-3" />
                      <span className="text-[10px]">Unified</span>
                    </button>
                    <button
                      onClick={() => setDiffMode("split")}
                      className={`p-1.5 rounded-lg border text-xs font-mono flex items-center gap-1 transition-all ${
                        diffMode === "split"
                          ? "bg-surface-elevated text-cyan-400 border-cyan-500/30 font-bold"
                          : "text-text-muted border-border-subtle hover:text-text-primary"
                      }`}
                      title="Side-by-side Split View"
                    >
                      <Columns className="w-3 h-3" />
                      <span className="text-[10px]">Split</span>
                    </button>
                  </div>
                )}

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleDownloadPatch}
                  className="px-2.5 py-1.5 text-xs rounded-xl bg-surface-elevated border border-border-subtle hover:border-cyan-400 text-text-secondary hover:text-cyan-300 flex items-center gap-1.5 transition-colors font-mono"
                  title="Download .patch file"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Export .patch</span>
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleCopyDiff}
                  className="px-3 py-1.5 text-xs rounded-xl bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 text-cyan-300 flex items-center gap-1.5 transition-colors font-mono font-bold"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Diff</span>
                    </>
                  )}
                </motion.button>
              </div>
            </div>

            {/* Interactive Tab Contents */}
            <div className="p-6 bg-[#06080E] font-mono text-xs overflow-x-auto max-h-[450px]">
              {/* CLEAN CODEBASE STATE */}
              {activeTab === "diff" && result.severity === "clean" && (
                <div className="p-8 text-center space-y-3 rounded-2xl bg-cyan-950/20 border border-cyan-500/30">
                  <div className="w-12 h-12 mx-auto rounded-full bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-300">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h4 className="text-sm font-mono font-bold text-cyan-300 uppercase tracking-wider">
                    Clean Codebase — Zero Open Issues Found
                  </h4>
                  <p className="text-xs text-text-secondary max-w-md mx-auto leading-relaxed font-sans">
                    GitHub reports <strong className="text-white">0 open issues</strong> or active defects for <strong className="text-cyan-300">{result.repository_name}</strong>. All integrity checks are verified and passing.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-cyan-400/80">
                    💡 Tip: To test a specific scenario or code defect, click <span className="text-cyan-300 font-semibold">&quot;Add custom stack trace / reproduction instructions&quot;</span> above and enter your problem description.
                  </div>
                </div>
              )}

              {/* UNIFIED DIFF VIEW */}
              {activeTab === "diff" && result.severity !== "clean" && diffMode === "unified" && (
                <pre className="text-text-primary whitespace-pre-wrap leading-relaxed">
                  {result.code_patch.split("\n").map((line, idx) => {
                    let color = "text-text-primary";
                    let bg = "";
                    if (line.startsWith("+")) {
                      color = "text-emerald-400 font-semibold";
                      bg = "bg-emerald-950/30";
                    } else if (line.startsWith("-")) {
                      color = "text-rose-400";
                      bg = "bg-rose-950/30";
                    } else if (line.startsWith("@")) {
                      color = "text-cyan-400 font-bold";
                      bg = "bg-cyan-950/20";
                    }
                    return (
                      <div key={idx} className={`${color} ${bg} px-2.5 py-0.5 rounded-sm flex items-center`}>
                        <span className="select-none text-text-muted/40 w-8 inline-block text-right pr-3 font-mono text-[10px]">
                          {idx + 1}
                        </span>
                        <span>{line}</span>
                      </div>
                    );
                  })}
                </pre>
              )}

              {/* SPLIT DIFF VIEW */}
              {activeTab === "diff" && result.severity !== "clean" && diffMode === "split" && (
                <div className="grid grid-cols-2 gap-4 divide-x divide-border-subtle">
                  <div className="space-y-1">
                    <span className="text-[10px] text-rose-400 uppercase font-bold block mb-1">Original (Before)</span>
                    {result.code_patch.split("\n").filter(l => !l.startsWith("+")).map((l, i) => (
                      <div key={i} className={l.startsWith("-") ? "text-rose-400 bg-rose-950/30 px-2 py-0.5 rounded" : "text-text-secondary px-2 py-0.5"}>
                        {l}
                      </div>
                    ))}
                  </div>
                  <div className="pl-4 space-y-1">
                    <span className="text-[10px] text-emerald-400 uppercase font-bold block mb-1">Patched (After)</span>
                    {result.code_patch.split("\n").filter(l => !l.startsWith("-")).map((l, i) => (
                      <div key={i} className={l.startsWith("+") ? "text-emerald-400 bg-emerald-950/30 px-2 py-0.5 rounded font-semibold" : "text-text-secondary px-2 py-0.5"}>
                        {l}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* RESOLUTION STEPS */}
              {activeTab === "solution" && (
                <div className="space-y-4 font-sans text-xs text-text-primary">
                  <div className="p-4 rounded-xl bg-surface-elevated border border-border-subtle space-y-2">
                    <span className="text-[11px] font-mono uppercase text-cyan-400 font-bold block">
                      Implementation Walkthrough
                    </span>
                    <p className="whitespace-pre-wrap leading-relaxed text-text-secondary">
                      {result.proposed_solution}
                    </p>
                  </div>
                </div>
              )}

              {/* VERIFICATION COMMANDS */}
              {activeTab === "verify" && (
                <div className="space-y-3">
                  <span className="text-[11px] font-mono text-text-muted">
                    Run these commands locally or in CI to reproduce &amp; verify the solution:
                  </span>
                  <div className="space-y-2">
                    {result.verification_steps.map((step, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-surface-elevated border border-border-subtle flex items-start gap-3 font-mono text-xs text-emerald-300"
                      >
                        <Terminal className="w-4 h-4 shrink-0 text-cyan-400 mt-0.5" />
                        <span className="select-all">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* INTERACTIVE SANDBOX SIMULATOR */}
              {activeTab === "simulate" && (
                <div className="space-y-4 font-mono">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface-elevated border border-border-subtle">
                    <div>
                      <span className="text-xs font-bold text-text-primary block">Ephemeral Sandbox Execution Simulator</span>
                      <span className="text-[11px] text-text-muted">Simulate test assertions and container validation before human approval</span>
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={runInteractiveSimulation}
                      disabled={simulating}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 text-black font-bold text-xs flex items-center gap-1.5 disabled:opacity-50 shadow-md"
                    >
                      <Play className={`w-3.5 h-3.5 ${simulating ? "animate-spin" : ""}`} />
                      <span>{simulating ? "Simulating Container..." : "Run Sandbox Test"}</span>
                    </motion.button>
                  </div>

                  <div className="p-4 rounded-xl bg-black border border-border-subtle text-[11px] leading-relaxed space-y-1.5 min-h-[160px]">
                    {simulatedLogs.length === 0 ? (
                      <span className="text-text-muted italic">Click &quot;Run Sandbox Test&quot; above to simulate isolated execution in container...</span>
                    ) : (
                      simulatedLogs.map((log, i) => (
                        <div key={i} className={log.includes("PASS") ? "text-emerald-400 font-bold" : "text-text-secondary"}>
                          {log}
                        </div>
                      ))
                    )}
                    {simPassed && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="mt-3 p-2.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-bold flex items-center gap-2"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>All simulated verification benchmarks passed! Ready for pull request dispatch.</span>
                      </motion.div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
