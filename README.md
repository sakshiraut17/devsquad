# DevSquad

**An AI-assisted software engineering platform for structured issue analysis, code patch synthesis, automated validation, and controlled repository automation.**

[![Project Status](https://img.shields.io/badge/Status-Foundation%20Operational-blue.svg)](PROJECT_STATUS.md)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](backend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?logo=fastapi&logoColor=white)](backend/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-000000.svg?logo=next.js&logoColor=white)](frontend/)
[![Tests](https://img.shields.io/badge/Tests-6%2F6%20Passing-brightgreen.svg)](backend/tests/)

DevSquad is an AI-assisted software engineering platform designed to evolve toward a controlled issue-to-PR workflow. It combines structured AI orchestration, repository context ingestion, automated code patch synthesis, sandboxed test execution, code review, and human-in-the-loop approval into a unified engineering pipeline.

---

## Overview & Current Status

DevSquad currently provides the foundational architecture, asynchronous backend API services, reactive frontend dashboard, structured AI provider abstraction, database datastore foundation, and automated testing suite required for the larger platform.

The architecture is intentionally designed to support future repository-aware issue planning, code patch synthesis, containerized sandbox execution, automated test verification, code review, and pull request workflows.

---

## Problem & Product Vision

Resolving software issues in legacy codebases requires significant cognitive overhead: contextual file lookup, implementation design, code patch creation, unit testing, and code review. Modern developer assistants often act as isolated one-shot text prompt generators without understanding full codebase context or verifying if generated code compiles and passes tests.

DevSquad is designed to address this gap by establishing a controlled, sandboxed software engineering pipeline:
- **Context Awareness**: Deep inspection of repository file structures and issue descriptions.
- **Deterministic Orchestration**: Stateful graph management with bounded auto-repair retry loops.
- **Execution Safety**: Isolation of generated code changes inside rootless Docker containers before human review and merging.

---

## System Architecture

```
                    +----------------------------------+
                    |          USER DEVELOPER          |
                    +----------------------------------+
                                     |
                                     v
                    +----------------------------------+
                    |        NEXT.JS 14 FRONTEND       |
                    |  (TypeScript, Tailwind, shadcn)  |
                    +----------------------------------+
                                     |
                      HTTP REST / WebSockets Connection
                                     |
                                     v
                    +----------------------------------+
                    |       FASTAPI BACKEND API        |
                    |   (Async ASGI, CORS, Security)   |
                    +----------------------------------+
                                     |
           +-------------------------+-------------------------+
           |                                                   |
           v                                                   v
+-----------------------+                           +-----------------------+
|  APPLICATION SERVICES |                           |  DATABASE (PostgreSQL)|
|  Config, Auth, Logging|                           |  SQLAlchemy 2.0 ORM   |
+-----------------------+                           +-----------------------+
           |
           v
+---------------------------------------------------------------------------+
|                      LANGGRAPH ORCHESTRATION ENGINE                       |
|                     (Stateful Cyclic Execution Graph)                     |
+---------------------------------------------------------------------------+
           |
     +-----+-----+-----+-----+
     |           |           |           |
     v           v           v           v
+---------+ +---------+ +---------+ +----------+
| PLANNER | |  CODER  | | TESTER  | | REVIEWER |
| SUBSYS  | | SUBSYS  | | SUBSYS  | | SUBSYS   |
| (PLANNED| | (PLANNED| | (PLANNED| | (PLANNED |
| FEATURE)| | FEATURE)| | FEATURE)| | FEATURE) |
+---------+ +---------+ +---------+ +----------+
     |           |           |           |
     +-----------+-----+-----+-----------+
                       |
                       v
         +---------------------------+
         |   LLM PROVIDER LAYER      |
         |  (Gemini 1.5 Pro / GPT-4o)|
         +---------------------------+
                       |
         +-------------+-------------+
         |                           |
         v                           v
+------------------+       +-------------------+
|  GITHUB API      |       |  DOCKER SANDBOX   |
| (REST / App API) |       | (Resource Capped  |
| [PLANNED FEATURE]|       |  Ephemeral Cont.) |
+------------------+       | [PLANNED FEATURE] |
                           +-------------------+
```

For full architectural blueprints, see [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md).

---

## AI Engineering Approach

For an in-depth breakdown of AI, Deep Learning, and Agentic AI concepts, see [docs/ai-architecture.md](docs/ai-architecture.md).

### 1. Artificial Intelligence
DevSquad uses AI to assist with software engineering tasks including issue context reasoning, implementation planning, code patch synthesis, test generation, failure analysis, and code quality review.

### 2. Deep Learning & Foundation Models
Software engineering reasoning relies on transformer-based language models (such as Gemini 1.5 Pro or GPT-4o) for understanding natural language issue bodies, source code structure, and module dependencies.

### 3. Agentic AI & State Machine Orchestration
DevSquad employs a stateful cyclic execution engine (powered by LangGraph) designed to coordinate specialized functional components (Planner, Coder, Tester, Reviewer) through structured state transitions and bounded auto-repair loops.

---

## Current Capabilities vs Product Direction

### Current Capabilities (Implemented & Verified)
- **FastAPI Asynchronous Backend**: High-performance REST API with structured logging and CORS middleware.
- **System Health Diagnostics**: Real-time diagnostic endpoint (`GET /api/v1/system/status`) reporting datastore connection, LLM provider, and container runner availability.
- **SQLAlchemy 2.0 ORM Datastore**: Async session manager with 8 core schema models (`User`, `Repository`, `Issue`, `Run`, `AgentLog`, `Patch`, `TestResult`, `PullRequest`).
- **Configuration Engine**: Environment-driven secret parsing using `pydantic-settings` without hardcoded credentials.
- **Next.js 14 Dashboard**: Reactive client dashboard with responsive navigation, system status polling widget, and architecture overview cards.
- **Automated Backend Testing**: Pytest suite verifying API endpoints, configuration loading, and database model relationships (100% pass rate).

### Planned Product Direction
DevSquad is actively being developed toward a complete software engineering workflow:
- **Repository Context Ingestion**: Deep file tree parsing and dependency index creation.
- **Issue Analysis & Planning**: Synthesizing structured task lists and acceptance criteria.
- **Code Patch Synthesis**: Generating unified code diffs and unit tests tailored to codebase style.
- **Docker Sandbox Execution**: Safely running test suites inside isolated, resource-capped containers.
- **Automated Code Review & Human Gateway**: Providing diff visualizers and human approval gates before opening GitHub Pull Requests.

---

## Tech Stack

- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.11+, FastAPI (Async ASGI), Pydantic V2, Pydantic-Settings
- **Datastore**: SQLAlchemy 2.0 (Async), PostgreSQL / SQLite async engine (`aiosqlite`)
- **AI Orchestration**: LangGraph, LangChain Core
- **Testing & Tooling**: Pytest, Pytest-Asyncio, HTTPX, Docker Engine API

---

## Repository Structure

```
devsquad/
├── .github/
│   └── workflows/          # CI/CD pipelines (Pytest, Next.js build)
├── backend/
│   ├── app/
│   │   ├── api/            # API v1 routes (/health, /api/v1/system/status)
│   │   ├── core/           # Config, database session, logging
│   │   ├── db/             # SQLAlchemy ORM models
│   │   └── schemas/        # Pydantic validation schemas
│   ├── tests/              # Pytest automated test suite
│   ├── pyproject.toml      # Package & tool configuration
│   └── requirements.txt    # Production dependencies
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js 14 pages and layout
│   │   ├── components/     # UI components (SystemHealthCard, Sidebar, Header)
│   │   └── lib/            # API client wrapper
│   └── package.json
├── docker/
│   ├── compose.yml         # Local multi-service orchestration
│   └── sandbox.Dockerfile  # Ephemeral execution container spec
├── docs/
│   ├── ai-architecture.md  # Detailed AI, ML, and LLM architecture specification
│   ├── database_schema.md  # Relational database schema specification
│   └── architecture/       # System architecture documentation
├── .env.example            # Environment configuration template
├── LICENSE                 # MIT License
├── PROJECT_STATUS.md       # Current implementation status tracking
└── README.md
```

---

## Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Environment Configuration
```bash
cp .env.example .env
```

### 2. Launch Backend API Server
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
Verify health endpoints:
- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/system/status`

### 3. Launch Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open dashboard in browser: `http://localhost:3000`

---

## Automated Testing

To run the backend test suite:
```bash
cd backend
python -m pytest -v
```

Expected result:
```bash
tests/test_config.py .                                                   [ 16%]
tests/test_health.py ...                                                 [ 66%]
tests/test_models.py ..                                                  [100%]
======================== 6 passed in 1.45s ========================
```

---

## Security & Isolation

- **Secret Management**: API keys and tokens are loaded strictly via environment variables (excluded from Git via `.gitignore`).
- **Payload Validation**: All incoming requests are validated using Pydantic schemas.
- **Sandboxed Execution**: AI-generated code will execute strictly inside rootless Docker containers with cgroup resource limits.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
