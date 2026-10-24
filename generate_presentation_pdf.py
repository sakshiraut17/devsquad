import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(r"C:\Users\ayush\Desktop\devsquad-main")
HTML_FILE = WORKSPACE / "presentation_guide_temp.html"
PDF_FILE = WORKSPACE / "DevSquad_Professor_Presentation_Guide.pdf"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DevSquad - Master Professor Defense &amp; Presentation Guide</title>
<style>
  @page {
    size: A4;
    margin: 18mm 14mm 18mm 14mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #64748b;
      font-family: 'Segoe UI', system-ui, sans-serif;
    }
  }

  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    background-color: #ffffff;
    line-height: 1.5;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
  }

  /* Page Break Utilities */
  .page-break {
    page-break-before: always;
  }
  .avoid-break {
    page-break-inside: avoid;
  }

  /* Header Cover Banner */
  .cover {
    background: linear-gradient(135deg, #090d16 0%, #0f172a 60%, #1e293b 100%);
    color: #ffffff;
    padding: 28px 24px;
    border-radius: 8px;
    margin-bottom: 22px;
    border-left: 6px solid #10b981;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .cover .badge {
    display: inline-block;
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.4);
    padding: 3px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-radius: 9999px;
    margin-bottom: 10px;
  }

  .cover h1 {
    margin: 0 0 6px 0;
    font-size: 23pt;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #f8fafc;
  }

  .cover h2 {
    margin: 0 0 14px 0;
    font-size: 11pt;
    font-weight: 400;
    color: #94a3b8;
  }

  .cover-meta {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding-top: 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
    font-size: 8pt;
  }

  .cover-meta div strong {
    display: block;
    color: #38bdf8;
    text-transform: uppercase;
    font-size: 7pt;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }

  /* Typography */
  h2.section-title {
    font-size: 13.5pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 5px;
    margin-top: 20px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  h2.section-title span.num {
    background: #0f172a;
    color: #ffffff;
    font-size: 9pt;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 700;
  }

  h3 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 12px;
    margin-bottom: 6px;
  }

  p {
    margin: 0 0 8px 0;
    color: #334155;
  }

  /* Callout boxes */
  .callout {
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    margin: 10px 0;
    font-size: 9pt;
  }
  .callout-green {
    border-left-color: #10b981;
    background: #f0fdf4;
  }
  .callout-amber {
    border-left-color: #f59e0b;
    background: #fffbeb;
  }
  .callout-purple {
    border-left-color: #8b5cf6;
    background: #f5f3ff;
  }
  .callout-title {
    font-weight: 700;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }
  .callout-green .callout-title { color: #047857; }
  .callout-amber .callout-title { color: #b45309; }
  .callout-purple .callout-title { color: #6d28d9; }
  .callout-blue .callout-title { color: #1d4ed8; }

  /* Flow diagrams */
  .pipeline-flow {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    background: #090d16;
    border-radius: 8px;
    padding: 12px;
    margin: 12px 0;
    gap: 6px;
  }

  .step-node {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    text-align: center;
    flex: 1;
    min-width: 80px;
  }
  .step-node .node-role {
    font-size: 6.5pt;
    font-weight: 700;
    text-transform: uppercase;
    color: #38bdf8;
    letter-spacing: 0.5px;
  }
  .step-node .node-name {
    font-size: 8pt;
    font-weight: 700;
    color: #f1f5f9;
  }
  .step-node.green { border-color: #10b981; }
  .step-node.green .node-role { color: #34d399; }
  .step-node.amber { border-color: #f59e0b; }
  .step-node.amber .node-role { color: #fbbf24; }
  .step-node.purple { border-color: #a855f7; }
  .step-node.purple .node-role { color: #c084fc; }
  .step-node.red { border-color: #ef4444; }
  .step-node.red .node-role { color: #f87171; }

  .step-arrow {
    color: #64748b;
    font-weight: 800;
    font-size: 10pt;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 8.5pt;
  }
  th {
    background: #0f172a;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 6px 10px;
    border: 1px solid #1e293b;
    font-size: 8pt;
  }
  td {
    padding: 6px 10px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background: #f8fafc;
  }

  /* Grid layout cards */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 10px 0;
  }

  .card {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 12px;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .card-header {
    font-weight: 700;
    font-size: 9pt;
    color: #0f172a;
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .pill {
    font-size: 6.5pt;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
  }
  .pill-green { background: #d1fae5; color: #065f46; }
  .pill-blue { background: #dbeafe; color: #1e40af; }
  .pill-purple { background: #f3e8ff; color: #6b21a8; }
  .pill-amber { background: #fef3c7; color: #92400e; }

  /* Q&A Items */
  .qa-block {
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    overflow: hidden;
  }
  .qa-q {
    background: #f1f5f9;
    padding: 8px 12px;
    font-weight: 700;
    font-size: 9pt;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }
  .qa-q-badge {
    background: #2563eb;
    color: #ffffff;
    font-size: 7pt;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .qa-a {
    padding: 10px 12px;
    background: #ffffff;
    font-size: 8.8pt;
    color: #334155;
    line-height: 1.45;
  }
  .qa-a strong {
    color: #0f172a;
  }
  .key-phrase {
    background: #fef9c3;
    padding: 1px 4px;
    border-radius: 2px;
    font-weight: 600;
    color: #854d0e;
  }

  /* Code snippet inline */
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8pt;
    background: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    color: #be185d;
  }

  .script-step {
    border-left: 3px solid #10b981;
    padding-left: 10px;
    margin-bottom: 10px;
  }
  .script-step .step-time {
    font-weight: 800;
    color: #059669;
    font-size: 8pt;
    text-transform: uppercase;
  }
  .script-step .step-action {
    font-weight: 700;
    color: #0f172a;
    font-size: 9pt;
  }
  .script-step .step-say {
    font-style: italic;
    color: #475569;
    font-size: 8.5pt;
    margin-top: 3px;
  }
</style>
</head>
<body>

  <!-- COVER / HEADER -->
  <div class="cover">
    <span class="badge">Master Oral Defense &amp; Evaluation Dossier</span>
    <h1>DEVSQUAD</h1>
    <h2>Production-Grade Multi-Agent AI Software Engineering Platform</h2>
    <div class="cover-meta">
      <div>
        <strong>System Architecture</strong>
        LangGraph Multi-Agent Engine
      </div>
      <div>
        <strong>Primary Stack</strong>
        FastAPI &bull; Next.js 14 &bull; Python AST
      </div>
      <div>
        <strong>Verification Status</strong>
        132 Unit Tests &bull; 19 Frontend Tests
      </div>
      <div>
        <strong>Target Audience</strong>
        Academic Professor / Viva Committee
      </div>
    </div>
  </div>

  <!-- SECTION 1 -->
  <h2 class="section-title"><span class="num">01</span> Executive Elevator Pitch (How to Open with Confidence)</h2>
  <div class="grid-2">
    <div class="card">
      <div class="card-header">
        <span>30-Second Rapid Pitch</span>
        <span class="pill pill-green">Opening Hook</span>
      </div>
      <p style="font-size: 8.8pt;">
        <em>"Good morning, Professor. <strong>DevSquad</strong> is an autonomous, production-grade multi-agent software engineering system that transforms real GitHub issues into verified, production-ready code changes. Unlike naive single-prompt tools that guess code blindly, DevSquad deploys a synchronized squad of specialized agents—Planner, Coder, AI Security Guardian, Sandbox Tester, and Reviewer—orchestrated via a resilient state graph with a cryptographic human approval gate."</em>
      </p>
    </div>
    <div class="card">
      <div class="card-header">
        <span>The Problem We Solve</span>
        <span class="pill pill-amber">Industry Context</span>
      </div>
      <p style="font-size: 8.8pt;">
        Commercial LLMs generate code, but fail in software engineering because they:
      </p>
      <ul style="margin: 0; padding-left: 16px; font-size: 8.5pt; color: #475569;">
        <li><strong>Hallucinate non-existent APIs</strong> without repo context grounding.</li>
        <li><strong>Introduce silent security vulnerabilities</strong> (SQLi, command injection, secret leakage).</li>
        <li><strong>Lack testing &amp; iterative self-repair</strong> before code hits git.</li>
        <li><strong>Execute without audit trails or cryptographic boundaries</strong>.</li>
      </ul>
    </div>
  </div>

  <!-- SECTION 2 -->
  <h2 class="section-title"><span class="num">02</span> End-to-End Multi-Agent Architecture</h2>
  <p>DevSquad implements a directed acyclic state graph built on <strong>LangGraph</strong>, featuring persistent SQLite/Postgres checkpointers, bounded repair cycles, and strict separation of concerns:</p>

  <div class="pipeline-flow">
    <div class="step-node">
      <div class="node-role">Step 1</div>
      <div class="node-name">Repo Ingest</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node purple">
      <div class="node-role">Agent 1</div>
      <div class="node-name">Planner</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node blue">
      <div class="node-role">Agent 2</div>
      <div class="node-name">Coder</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node red">
      <div class="node-role">Security Gate</div>
      <div class="node-name">Guardian</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node amber">
      <div class="node-role">Agent 3</div>
      <div class="node-name">Sandbox Tester</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node purple">
      <div class="node-role">Agent 4</div>
      <div class="node-name">Reviewer</div>
    </div>
    <div class="step-arrow">&rarr;</div>
    <div class="step-node green">
      <div class="node-role">Human Gate</div>
      <div class="node-name">Approval</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 15%;">Agent / Node</th>
        <th style="width: 25%;">Primary Responsibility</th>
        <th style="width: 32%;">Defensive Controls &amp; Engineering Rigor</th>
        <th style="width: 28%;">Failure Handling</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Context Ranker</strong></td>
        <td>Ranks and budgets repository files relevant to the issue.</td>
        <td>Deterministic TF-IDF token budgeting; strict exclusion of binary, vendor, and secret files.</td>
        <td>Truncates context deterministically to prevent token context blowout.</td>
      </tr>
      <tr>
        <td><strong>Planner Agent</strong></td>
        <td>Generates a structured, evidence-backed implementation plan.</td>
        <td><strong>Line-Span Evidence Verification:</strong> Validates file hashes and line spans against base commit SHA.</td>
        <td>Rejects plans referencing hallucinated files before coding begins.</td>
      </tr>
      <tr>
        <td><strong>Coder Agent</strong></td>
        <td>Synthesizes minimal unified diff patches.</td>
        <td>Rejects path traversal (<code>../</code>), absolute paths, and invalid hunk boundary line offsets.</td>
        <td>Receives structured repair feedback from Reviewer and Sandbox Tester.</td>
      </tr>
      <tr>
        <td><strong>AI Security Guardian</strong></td>
        <td>Automated pre-sandbox and pre-approval vulnerability scanner.</td>
        <td>Deterministic secret scanner (SHA-256 redaction); AST scanners for SQLi, <code>shell=True</code>, <code>eval()</code>, insecure yaml.</td>
        <td><strong>Fail-Closed Gate:</strong> Blocks approval if critical or high vulnerabilities are detected.</td>
      </tr>
      <tr>
        <td><strong>Sandbox Tester</strong></td>
        <td>Executes test suites and syntax validations.</td>
        <td>Runs in isolated Docker container with execution timeouts; clean fallback to Python AST static syntax validation.</td>
        <td>Captures stack traces and injects structured error logs into state for Coder repair.</td>
      </tr>
      <tr>
        <td><strong>Reviewer Agent</strong></td>
        <td>Multi-perspective code review (correctness, safety, style).</td>
        <td>Scores patches across 4 dimensions; enforces bounded repair loops (max 3 revision attempts).</td>
        <td>Triggers automated iterative repair cycle if issues are fixable.</td>
      </tr>
      <tr>
        <td><strong>Human Approval Gate</strong></td>
        <td>Final human maintainer decision before publication.</td>
        <td><strong>Cryptographic Patch Verification:</strong> Computes SHA-256 patch hash to guarantee zero in-flight tampering.</td>
        <td>Rejection terminates workflow; approved patch publishes directly to GitHub.</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 3 -->
  <div class="page-break"></div>
  <h2 class="section-title"><span class="num">03</span> Key Technical Innovations (What Impresses Professors)</h2>

  <div class="callout callout-green avoid-break">
    <div class="callout-title">Innovation #1: Grounded Planning with Cryptographic Line-Span Evidence</div>
    <p>
      Standard generative AI systems hallucinate nonexistent files or functions. DevSquad enforces a <strong>Grounded Evidence Model</strong>: before the Coder Agent writes a single line of code, the Planner Agent must cite exact line spans from the target repository, verified against the repository's base commit SHA-256 hash. If an agent claims a bug is at line 45 of a file that only has 30 lines, the execution engine rejects the plan at the schema layer.
    </p>
  </div>

  <div class="callout callout-purple avoid-break">
    <div class="callout-title">Innovation #2: Multi-Layer AI Security Guardian Pipeline</div>
    <p>
      Every generated patch passes through a deterministic security verification suite before execution or review:
    </p>
    <ul style="margin: 0; padding-left: 18px; font-size: 8.5pt;">
      <li><strong>Deterministic Secret Redaction:</strong> Intercepts API keys, AWS credentials, and PAT tokens using regex heuristics and hashes them (<code>[REDACTED_SECRET:&lt;sha256&gt;]</code>). No secrets enter the database.</li>
      <li><strong>AST Semantic Code Inspection:</strong> Parses abstract syntax trees to catch unparameterized SQL execution, arbitrary command injection (<code>subprocess.Popen(..., shell=True)</code>), <code>eval()</code>, and deprecated crypto.</li>
      <li><strong>Dependency Risk Auditor:</strong> Blocks wildcard version pinning (<code>*</code>) and flags known vulnerable packages.</li>
    </ul>
  </div>

  <div class="callout callout-amber avoid-break">
    <div class="callout-title">Innovation #3: Resilient GitHub API Integration &amp; Auto-Issue Resolution</div>
    <p>
      DevSquad supports both read-only repository inspection and full write-back issue resolution:
    </p>
    <ul style="margin: 0; padding-left: 18px; font-size: 8.5pt;">
      <li><strong>OAuth Scope Negotiation:</strong> Inspects GitHub <code>X-OAuth-Scopes</code> header to automatically toggle between <em>Read-Only Mode</em> and <em>Write &amp; Solve Mode</em>.</li>
      <li><strong>Auto-Creation Fallback:</strong> When solving issues on newly linked repositories that have 0 open issues, DevSquad dynamically generates the issue on GitHub via REST API and automatically attaches the verified solution and patch.</li>
    </ul>
  </div>

  <!-- SECTION 4 -->
  <h2 class="section-title"><span class="num">04</span> Production Tech Stack &amp; Architectural Rationale</h2>
  <table>
    <thead>
      <tr>
        <th>Layer</th>
        <th>Technologies</th>
        <th>Engineering Justification (Why this over alternatives?)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Backend Engine</strong></td>
        <td>Python 3.11+, FastAPI, Uvicorn, Pydantic V2</td>
        <td>FastAPI provides asynchronous request concurrency, native OpenAPI documentation, and high-throughput serialization with Pydantic V2 compiled C-extensions.</td>
      </tr>
      <tr>
        <td><strong>Agent Orchestration</strong></td>
        <td>LangGraph, LangChain Core, SQLite Async Checkpointer</td>
        <td>LangGraph enables cyclic graphs (necessary for self-repair loops), deterministic state transitions, and persistent checkpoints so runs can be paused and resumed.</td>
      </tr>
      <tr>
        <td><strong>Frontend Architecture</strong></td>
        <td>Next.js 14 (App Router), React, Tailwind CSS, TypeScript</td>
        <td>Server components for instant load, full TypeScript safety across shared API interfaces, and custom responsive cyber-command aesthetic with zero UI lag.</td>
      </tr>
      <tr>
        <td><strong>Real-Time Streaming</strong></td>
        <td>Server-Sent Events (SSE) + Short-Lived HMAC Stream Tickets</td>
        <td>Enables lightweight, firewall-friendly unidirectional streaming of agent thinking steps without the operational complexity or reconnection overhead of WebSockets.</td>
      </tr>
      <tr>
        <td><strong>Sandbox &amp; Testing</strong></td>
        <td>Docker Containers + Python AST Syntax Parsing</td>
        <td>Docker guarantees kernel-level process isolation for test execution, while AST fallback guarantees deterministic syntax evaluation even in lightweight local environments.</td>
      </tr>
    </tbody>
  </table>

  <!-- SECTION 5 -->
  <div class="page-break"></div>
  <h2 class="section-title"><span class="num">05</span> Live Demonstration Walkthrough (Step-by-Step Script)</h2>
  <p>Follow this exact chronological script during your live presentation for maximum impact:</p>

  <div class="script-step avoid-break">
    <div class="step-time">00:00 - 01:00 | System Overview &amp; Health Probe</div>
    <div class="step-action">Action: Open Browser at <code>http://localhost:3000</code>. Point to Navbar status badges.</div>
    <div class="step-say">
      "Here is the DevSquad Command Center. Notice the real-time health indicator showing FastAPI backend connectivity, database readiness, and the active LLM provider. The system is designed with enterprise-grade observability from the ground up."
    </div>
  </div>

  <div class="script-step avoid-break">
    <div class="step-time">01:00 - 02:30 | Repository Linking &amp; Scope Verification</div>
    <div class="step-action">Action: Navigate to <strong>Repositories</strong>. Click <strong>Connect GitHub Account</strong>.</div>
    <div class="step-say">
      "DevSquad connects to GitHub repositories via secure Personal Access Tokens. Notice the live OAuth scope detector: it analyzes the token's GitHub permissions and highlights whether we have full issue-solving write permissions or read-only mode."
    </div>
  </div>

  <div class="script-step avoid-break">
    <div class="step-time">02:30 - 04:30 | Triggering an Issue &amp; Real-Time Agent Execution</div>
    <div class="step-action">Action: Select an issue or enter a repository in the Quick Solver on the Dashboard. Click <strong>Solve Issue with DevSquad</strong>.</div>
    <div class="step-say">
      "When we dispatch a run, LangGraph initializes our multi-agent workflow. Watch the live execution stepper: First, the Planner identifies root cause files with cryptographic line-span evidence. Next, the Coder writes a surgical unified diff. The AI Security Guardian scans the patch for secrets and AST syntax risks. The Tester verifies syntax, and the Reviewer scores code quality."
    </div>
  </div>

  <div class="script-step avoid-break">
    <div class="step-time">04:30 - 06:00 | Unified Diff Inspection &amp; Cryptographic Human Approval</div>
    <div class="step-action">Action: View the generated patch in the <strong>Unified Diff Viewer</strong>. Show the Approval Modal.</div>
    <div class="step-say">
      "DevSquad never commits autonomously without human sign-off. The maintainer can inspect additions and deletions in the unified diff viewer. When I click 'Approve Patch', the system validates the SHA-256 hash of the patch to guarantee it hasn't been altered in transit."
    </div>
  </div>

  <div class="script-step avoid-break">
    <div class="step-time">06:00 - 07:00 | Publishing Directly to GitHub</div>
    <div class="step-action">Action: Click <strong>Publish Solution to GitHub</strong>. Open the generated GitHub URL.</div>
    <div class="step-say">
      "Finally, with one click, DevSquad publishes the full diagnostic report, root cause analysis, code diff, and verification logs directly to the user's GitHub repository. If the issue didn't exist yet, it automatically creates it and links the solution."
    </div>
  </div>

  <!-- SECTION 6 -->
  <div class="page-break"></div>
  <h2 class="section-title"><span class="num">06</span> Professor Viva Q&amp;A: Top 15 Toughest Technical Questions &amp; Winning Answers</h2>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q1</span>
      <span>Why did you use LangGraph instead of a standard LangChain pipeline or raw sequential API calls?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> Standard LangChain sequential chains (and simple prompt scripts) are strictly linear (DAGs) and cannot handle <span class="key-phrase">cyclic state transitions</span>. Software engineering is inherently iterative: when a test fails or a reviewer requests changes, the system must loop back from Reviewer &rarr; Coder &rarr; Tester. LangGraph provides <strong>first-class cyclic graph support</strong>, explicit typed state transitions, and checkpointing persistence, allowing runs to be paused, audited, and safely resumed.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q2</span>
      <span>How does your system guarantee that the LLM doesn't hallucinate non-existent files or functions?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> We enforce our <span class="key-phrase">Grounded Planning &amp; Evidence Protocol</span>. Before any code is synthesized, the Planner Agent must produce structured evidence linking every proposed change to exact file paths and line ranges present in the repository at a specific base commit SHA. If the referenced path does not exist or line boundaries exceed the actual file length, Pydantic schema validation rejects the plan immediately.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q3</span>
      <span>What prevents the AI Coder from generating malicious code or prompt injection payloads?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> We employ a defense-in-depth model through the <span class="key-phrase">AI Security Guardian Gate</span>. Patches are inspected before sandbox execution using deterministic Python AST parsers that detect dangerous function calls like <code>eval()</code>, <code>os.system()</code>, unparameterized SQL strings, and path traversal strings (<code>../</code>). Any patch failing security heuristics is automatically blocked under our <strong>fail-closed policy</strong>.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q4</span>
      <span>How do you protect sensitive credentials and API tokens from being logged or leaked?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> DevSquad implements a <span class="key-phrase">Deterministic Secret Redaction Engine</span> in <code>core/security.py</code>. All raw text, LLM prompts, and API responses pass through regex redaction patterns targeting GitHub PATs (<code>ghp_</code>, <code>github_pat_</code>), OpenAI keys (<code>sk-</code>), AWS access keys, and Bearer tokens. Detected secrets are masked and cryptographically salted with SHA-256 hashes, ensuring zero plaintext secrets are written to logs or SQLite databases.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q5</span>
      <span>What happens if the generated patch fails sandbox tests or introduces syntax errors?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> This triggers our <span class="key-phrase">Bounded Self-Repair Cycle</span>. The Sandbox Tester captures the exact compilation error, traceback, or test failure output. This diagnostic report is injected into the LangGraph state. The graph routes back to the Coder Agent with explicit repair guidance. To prevent infinite spending or loops, we enforce a strict <code>max_repair_attempts = 3</code> limit; if unfixable, the run terminates safely with an audit trail.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q6</span>
      <span>Why is a Human-in-the-Loop approval gate required instead of committing directly to main?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> Autonomous software generation in production carries high liability. The Human-in-the-Loop gate ensures <span class="key-phrase">maintainer accountability and zero hallucination risk</span>. Furthermore, our approval system is <strong>cryptographically signed</strong>: when the maintainer approves a diff, the backend verifies that the SHA-256 hash of the displayed diff matches the patch on disk, preventing man-in-the-middle or state tampering.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q7</span>
      <span>How does the system scale if a repository has 10,000 files and exceeds LLM context windows?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> We built an intelligent <span class="key-phrase">Context Ranker &amp; Budgeting Subsystem</span>. Instead of stuffing entire repos into the prompt, the Context Ranker performs deterministic relevance scoring using BM25/TF-IDF token matching, AST import graph analysis, and path heuristics. It excludes binaries, <code>node_modules</code>, and vendors, packing only the most relevant files within a strict, configurable token budget (e.g., 16k tokens).
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q8</span>
      <span>How do you handle real-time streaming to the frontend without WebSocket overhead?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> We use <span class="key-phrase">Server-Sent Events (SSE) secured by short-lived HMAC tickets</span>. When the frontend loads a run, it requests a 60-second cryptographically signed stream ticket from <code>/api/v1/runs/{id}/stream-ticket</code>. The browser then opens an SSE stream. This provides clean, unidirectional event streaming that works seamlessly across enterprise firewalls, avoids WebSocket proxy issues, and prevents unauthorized stream snooping.
    </div>
  </div>

  <!-- SECTION 7 -->
  <div class="page-break"></div>
  <h2 class="section-title"><span class="num">07</span> Additional Viva In-Depth Defense Questions</h2>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q9</span>
      <span>How do you defend against Docker container escape attacks during sandbox test execution?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> Container tests run in an ephemeral Docker environment with <span class="key-phrase">strict resource constraints</span>: non-root user execution, read-only root filesystems where possible, disabled networking flags, tight memory caps, and a hard execution timeout (e.g., 30 seconds). If Docker is unavailable or untrusted, the system gracefully degrades to safe, in-process Python AST syntax inspection.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q10</span>
      <span>How is the database designed, and how do you ensure data integrity across migrations?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> We use <span class="key-phrase">SQLAlchemy 2.0 Async ORM with Alembic</span> for versioned database migrations. Our schema comprises 8 normalized core tables: <code>repositories</code>, <code>issues</code>, <code>agent_runs</code>, <code>plans</code>, <code>patches</code>, <code>test_results</code>, <code>reviews</code>, and <code>security_scans</code>. Foreign keys, cascading constraints, and indexes on repository and run IDs ensure referential integrity and sub-millisecond query performance.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q11</span>
      <span>What happens if the user links a repository that has zero existing issues on GitHub?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> Previously, standard API clients would fail with <code>HTTP 404 Not Found</code>. We implemented an <span class="key-phrase">Auto-Issue Creation Fallback</span> in <code>github_service.py</code>. If an issue number does not exist on GitHub, DevSquad catches the 404, dynamically creates a new issue via <code>POST /repos/{owner}/{repo}/issues</code> containing the problem description, and attaches the complete AI solution, unified diff, and verification logs.
    </div>
  </div>

  <div class="qa-block avoid-break">
    <div class="qa-q">
      <span class="qa-q-badge">Q12</span>
      <span>How does DevSquad compare to commercial tools like GitHub Copilot or Devin?</span>
    </div>
    <div class="qa-a">
      <strong>Winning Answer:</strong> Copilot operates as an inline auto-complete tool inside the IDE without whole-repository issue synthesis or multi-agent validation. Devin is a closed-source proprietary agent. DevSquad is an <span class="key-phrase">open, enterprise-auditable multi-agent platform</span> that provides full transparency into each reasoning step (Planner &rarr; Coder &rarr; Security &rarr; Tester &rarr; Reviewer) with explicit human gating and zero lock-in.
    </div>
  </div>

  <!-- SECTION 8 -->
  <h2 class="section-title"><span class="num">08</span> Verification, Test Coverage &amp; Code Quality Metrics</h2>
  <div class="grid-2">
    <div class="card avoid-break">
      <div class="card-header">
        <span>Backend Pytest Test Suite</span>
        <span class="pill pill-green">132 / 132 Passing (100%)</span>
      </div>
      <table style="font-size: 7.8pt; margin: 4px 0;">
        <tr><td><code>test_checkpointer.py</code></td><td>StateGraph persistence &amp; SQLite recovery</td></tr>
        <tr><td><code>test_coder_agent.py</code></td><td>Diff validity, traversal &amp; hunk safety</td></tr>
        <tr><td><code>test_context_ranker.py</code></td><td>File scoring, secret exclusions, token budget</td></tr>
        <tr><td><code>test_diff_utils.py</code></td><td>Unified diff parsing, patch safety validation</td></tr>
        <tr><td><code>test_github_service.py</code></td><td>OAuth permissions, issue creation, comment API</td></tr>
        <tr><td><code>test_grounded_planner.py</code></td><td>Line-span verification, file hash checks</td></tr>
        <tr><td><code>test_security.py</code></td><td>Secret masking, canonical SHA-256, path traversal</td></tr>
        <tr><td><code>test_security_stream_ticket.py</code></td><td>HMAC replay protection, expiration checks</td></tr>
      </table>
    </div>

    <div class="card avoid-break">
      <div class="card-header">
        <span>Frontend Test Suite &amp; Build</span>
        <span class="pill pill-green">19 / 19 Passing &bull; Next.js Clean</span>
      </div>
      <table style="font-size: 7.8pt; margin: 4px 0;">
        <tr><td>Route &amp; Navigation Suite</td><td>8 core navigation routes &amp; active sidebar state</td></tr>
        <tr><td>Diff Viewer HTML Escaping</td><td>Zero XSS execution in patch preview window</td></tr>
        <tr><td>Human Approval Gate</td><td>Enforces <code>is_verified</code> &amp; SHA-256 confirmation check</td></tr>
        <tr><td>Stream Ticket Security</td><td>Short-lived ticket injection &amp; SSE closure</td></tr>
        <tr><td>Reviewer Gating</td><td>Blocking finding rejection &amp; advisory badges</td></tr>
        <tr><td>Next.js Production Build</td><td>Zero TypeScript errors, 12 static/dynamic routes</td></tr>
      </table>
    </div>
  </div>

  <!-- SECTION 9 -->
  <h2 class="section-title"><span class="num">09</span> Presentation Day Checklist &amp; Backup Plan</h2>
  <div class="callout callout-purple avoid-break">
    <div class="callout-title">Master Checklist Before Entering the Room</div>
    <ul style="margin: 0; padding-left: 18px; font-size: 8.5pt;">
      <li><strong>Start Services Early:</strong> Ensure FastAPI is running on <code>http://127.0.0.1:8000</code> and Next.js is running on <code>http://localhost:3000</code>.</li>
      <li><strong>Pre-link GitHub Token:</strong> Generate a classic PAT with <code>repo</code> scope beforehand so the badge shows <code>&check; Write &amp; Solve Authorized</code>.</li>
      <li><strong>Keep 1 Solved Issue Ready in Tab:</strong> In case campus Wi-Fi drops, keep a completed run open in a browser tab showing the full agent trace, unified diff, and approval modal.</li>
      <li><strong>Emphasize Engineering Over Hype:</strong> Speak about state graphs, AST parsing, Pydantic contracts, and fail-closed security—professors respect robust system design much more than generic "AI magic".</li>
    </ul>
  </div>

</body>
</html>
"""

def generate_pdf():
    print("Writing HTML presentation guide...")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"HTML written to {HTML_FILE}")
    print("Converting HTML to PDF via Microsoft Edge Headless...")
    
    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_FILE}",
        str(HTML_FILE)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("Process return code:", result.returncode)
    if result.stdout:
        print("Stdout:", result.stdout)
    if result.stderr:
        print("Stderr:", result.stderr)
        
    if PDF_FILE.exists():
        size_kb = PDF_FILE.stat().st_size / 1024
        print(f"SUCCESS: Generated PDF at {PDF_FILE} ({size_kb:.1f} KB)")
    else:
        print("ERROR: PDF was not created.")

if __name__ == "__main__":
    generate_pdf()
