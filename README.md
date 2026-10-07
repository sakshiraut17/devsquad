# DevSquad — Autonomous AI Software Engineering Team

[![Sprint Progress](https://img.shields.io/badge/Sprint%201-COMPLETED-emerald.svg)](PROJECT_STATUS.md)
[![Release Tag](https://img.shields.io/badge/Release-v0.1.0--foundation-blue.svg)](docs/sprints/sprint_1_report.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](backend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?logo=fastapi&logoColor=white)](backend/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg?logo=next.js&logoColor=white)](frontend/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful%20Orchestrator-FF6F00.svg)](docs/ai-architecture.md)
[![Tests](https://img.shields.io/badge/Tests-6%2F6%20Passing-brightgreen.svg)](backend/tests/)

> **DevSquad** is an industry-grade AI-assisted software engineering platform designed to automate GitHub repository issue resolution using specialized **Agentic AI** workflows. Orchestrated via **LangGraph**, DevSquad deploys a cooperative multi-agent workflow (`Planner` $\rightarrow$ `Coder` $\rightarrow$ `Tester` $\rightarrow$ `Reviewer`) to inspect codebases, synthesize code patches and unit tests, verify execution in isolated **Docker Sandboxes**, and issue human-approvable Pull Requests.

---

## 🎓 Quick Evaluation Guide for Professor Review (Sprint 1 Checkpoint)

> [!IMPORTANT]
> **Evaluation Deadline**: 10 October 2026 | **Current Status**: **Sprint 1 (Foundation & Architecture) COMPLETED**

- 📋 **Project Status**: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- 🧠 **AI / ML / DL Academic Foundation**: [docs/ai-architecture.md](docs/ai-architecture.md)
- 🏗️ **System Architecture Blueprint**: [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md)
- 🗄️ **Database Schema Specification**: [docs/database_schema.md](docs/database_schema.md)
- 📄 **Sprint 1 Release Report**: [docs/sprints/sprint_1_report.md](docs/sprints/sprint_1_report.md)

### Verification Summary at Sprint 1
- **Backend API**: Python FastAPI server with `/health` and `/api/v1/system/status` endpoints (**VERIFIED & OPERATIONAL**).
- **Datastore Layer**: SQLAlchemy 2.0 Async session with 8 core entity ORM models (**VERIFIED**).
- **Frontend Dashboard**: Next.js 14 App Router UI connected to backend status diagnostics (**VERIFIED**).
- **Automated Tests**: Pytest test suite with **100% Pass Rate** (6/6 unit tests passing).

---

## 📌 Problem Statement & Motivation

Resolving software issues in legacy codebases requires significant cognitive overhead: contextual file lookup, implementation design, code patch creation, unit testing, and code review. Modern developer assistants often act as isolated one-shot text prompt generators without understanding full codebase context or verifying if generated code compiles and passes tests.

**DevSquad** bridges this gap by introducing a **controlled, sandboxed multi-agent autonomous engineering pipeline**:
1. **Context Awareness**: Deep inspection of GitHub issue descriptions and codebase repository trees.
2. **Deterministic Orchestration**: State graph management with bounded auto-repair loops (max 3 retries).
3. **Execution Safety**: Strict isolation of AI-generated code inside rootless Docker containers before merging.

---

## 🤖 AI, Machine Learning & Deep Learning Foundation

DevSquad integrates modern Artificial Intelligence concepts across multiple software engineering layers:

```
                                AI & ML ARCHITECTURE PIPELINE
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [Artificial Intelligence]  --> Multi-Agent Autonomous Software Engineering Workflow    |
|  [Deep Learning]           --> Transformer-based LLMs (Gemini / OpenAI Foundation)      |
|  [Agentic Orchestration]   --> LangGraph Stateful Cyclic Graphs & Auto-Repair Loops      |
|  [Machine Learning (ML)]   --> Task Complexity Classifier & Failure Predictor [PLANNED] |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

For full mathematical and architectural details, refer to the [AI Architecture Documentation](docs/ai-architecture.md).

### Implemented vs. Planned AI Features

| Technical Component | Description | Implementation Status | Target Sprint |
| :--- | :--- | :--- | :--- |
| **Agentic State Engine** | LangGraph cyclic graph & state schemas | **IMPLEMENTED** | Sprint 1 |
| **LLM Provider Gateway** | Config abstraction for Gemini & OpenAI | **IMPLEMENTED** | Sprint 1 |
| **Pydantic Schema Output**| Structured JSON validation for LLM responses | **IMPLEMENTED** | Sprint 1 |
| **GitHub REST Integration**| Repository metadata & issue context extraction | **PLANNED** | Sprint 2 |
| **Planner Agent Node** | Issue context breakdown & acceptance criteria | **PLANNED** | Sprint 3 |
| **Coder Agent Node** | Unified code diff generation & test synthesis | **PLANNED** | Sprint 4 |
| **Docker Execution Sandbox**| Ephemeral resource-capped code runner | **PLANNED** | Sprint 5 |
| **Tester & Reviewer Nodes**| Traceback parsing & bounded auto-repair loop | **PLANNED** | Sprint 6 |
| **ML Task Difficulty Predictor**| XGBoost classifier for task estimation | **PLANNED** | Sprint 9 |

---

## 🏗️ System Architecture

```mermaid
graph TD
    UI["Next.js 14 Dashboard Shell"] <-->|HTTP REST / WS| API["FastAPI Backend API"]
    API <--> DB[(PostgreSQL Datastore)]
    API -.-> LG["LangGraph Agent Engine"]
    
    subgraph Multi-Agent Core Pipeline (Planned Sprints 3-6)
        LG -.-> PA["Planner Agent Node"]
        LG -.-> CA["Coder Agent Node"]
        LG -.-> TA["Tester Agent Node"]
        LG -.-> RA["Reviewer Agent Node"]
    end
    
    TA -.-> SDK["Isolated Docker Execution Sandbox (Planned Sprint 5)"]
    PA & CA -.-> GH["GitHub API Engine (Planned Sprint 2)"]
    PA & CA & TA & RA <--> LLM["LLM Provider (Gemini / OpenAI API)"]
```

---

## 💻 Tech Stack & Dependencies

### Frontend (`frontend/`)
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS, Lucide Icons

### Backend (`backend/`)
- **Framework**: FastAPI (Async ASGI)
- **Database ORM**: SQLAlchemy 2.0 (Async) + Alembic
- **Database Engine**: PostgreSQL (SQLite async fallback for local dev)
- **Orchestration**: LangGraph, LangChain Core
- **Validation**: Pydantic V2, Pydantic-Settings
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

### Infrastructure & Security (`docker/`, `.github/`)
- **Containers**: Docker Desktop, Docker Engine API
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`)

---

## 📂 Repository Layout

```
devsquad/
├── .github/
│   └── workflows/          # GitHub Actions CI pipeline
├── backend/
│   ├── app/
│   │   ├── api/            # API v1 routes (/health, /api/v1/system/status)
│   │   ├── core/           # Pydantic Settings, DB connection, logging
│   │   ├── db/             # SQLAlchemy ORM models (User, Repo, Issue, Run, etc.)
│   │   └── schemas/        # Pydantic request/response validation schemas
│   ├── tests/              # Pytest automated test suite (100% pass rate)
│   ├── pyproject.toml      # Python package & tool configuration
│   └── requirements.txt    # Production dependencies
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js 14 App Router layout & pages
│   │   ├── components/     # UI components (SystemHealthCard, Sidebar, Header)
│   │   └── lib/            # API client wrapper & utility functions
│   └── package.json
├── docker/
│   ├── compose.yml         # PostgreSQL & Backend service docker-compose
│   └── sandbox.Dockerfile  # Ephemeral code execution container spec
├── docs/
│   ├── ai-architecture.md  # Detailed AI / ML / DL / LLM academic documentation
│   ├── database_schema.md  # PostgreSQL Entity-Relationship specification
│   ├── architecture/       # System architecture diagrams
│   └── sprints/            # Sprint release reports (Sprint 1 report)
├── .env.example            # Environment configuration template
├── LICENSE                 # MIT License
├── PROJECT_STATUS.md       # 60-Day Sprint Progress Log
└── README.md
```

---

## ⚡ Quickstart & Local Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Configure Environment File
```bash
cp .env.example .env
```

### 2. Set Up & Launch Backend API
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Verify backend health in browser or curl:
- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/system/status`

### 3. Set Up & Launch Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open dashboard in browser: `http://localhost:3000`

---

## 🧪 Automated Testing

To run the backend test suite:
```bash
cd backend
python -m pytest -v
```

Expected output:
```bash
tests/test_config.py .                                                   [ 16%]
tests/test_health.py ...                                                 [ 66%]
tests/test_models.py ..                                                  [100%]
======================== 6 passed in 1.49s ========================
```

---

## 📅 60-Day / 10-Sprint Execution Schedule

- **Sprint 1 (Days 1–6)**: System Architecture, Monorepo Layout, FastAPI Core & DB Models 🟢 **COMPLETED** (`v0.1.0-foundation`)
- **Sprint 2 (Days 7–12)**: GitHub Integration Engine (OAuth, Issues, Repo Metadata) 🟡 **NEXT**
- **Sprint 3 (Days 13–18)**: Planner Agent & LangGraph Orchestration Engine
- **Sprint 4 (Days 19–24)**: Coder Agent & Visual Diff Viewer Component
- **Sprint 5 (Days 25–30)**: Isolated Docker Execution Sandbox
- **Sprint 6 (Days 31–36)**: Tester Agent, Reviewer Agent & Auto-Repair Execution Loop
- **Sprint 7 (Days 37–42)**: GitHub Pull Request Workflow & Human Approval Gateway
- **Sprint 8 (Days 43–48)**: Premium Dashboard, Live Timeline & Token/Cost Analytics
- **Sprint 9 (Days 49–54)**: Security Audit, Benchmarking & E2E Testing Suite
- **Sprint 10 (Days 55–60)**: Production Deployment, CI/CD & Final Presentation

---

## 🛡️ Security & Environment Safety

- **Zero Hardcoded Secrets**: Secrets and tokens are managed via `.env` files (excluded from Git via `.gitignore`).
- **Input Validation**: All incoming API request bodies are validated using Pydantic V2 schemas.
- **Sandboxed Execution**: AI-generated code will execute strictly inside rootless Docker containers with cgroup resource limits.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
