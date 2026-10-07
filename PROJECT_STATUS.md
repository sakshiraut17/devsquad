# DevSquad — Project Status & Sprint Tracker

**Current Sprint**: Sprint 1 (Foundation & Architecture)  
**Sprint Status**: 🟢 **COMPLETED** (Verified 10 October 2026 Submission Checkpoint)  
**Target Submission Date**: 10 October 2026  
**Git Release Tag**: `v0.1.0-foundation`  

---

## 🎯 60-Day / 10-Sprint Execution Progress Table

| Sprint | Days | Focus Area | Status | Deliverables / Tag |
| :--- | :--- | :--- | :--- | :--- |
| **Sprint 1** | **Days 1–6** | **Foundation & Architecture** | 🟢 **COMPLETED** | [`v0.1.0-foundation`](docs/sprints/sprint_1_report.md) |
| **Sprint 2** | **Days 7–12** | **GitHub Integration Engine** | ⚪ Planned | `v0.2.0-github-integration` |
| **Sprint 3** | **Days 13–18** | **Planner Agent (LangGraph)** | ⚪ Planned | `v0.3.0-planner-agent` |
| **Sprint 4** | **Days 19–24** | **Coder Agent & Diff Viewer** | ⚪ Planned | `v0.4.0-coder-agent` |
| **Sprint 5** | **Days 25–30** | **Docker Sandbox Execution** | ⚪ Planned | `v0.5.0-docker-sandbox` |
| **Sprint 6** | **Days 31–36** | **Tester & Reviewer Agents** | ⚪ Planned | `v0.6.0-tester-reviewer` |
| **Sprint 7** | **Days 37–42** | **PR Workflow & Human Gateway** | ⚪ Planned | `v0.7.0-pr-workflow` |
| **Sprint 8** | **Days 43–48** | **UI Timeline & Analytics** | ⚪ Planned | `v0.8.0-dashboard-ui` |
| **Sprint 9** | **Days 49–54** | **Reliability & E2E Testing** | ⚪ Planned | `v0.9.0-reliability-eval` |
| **Sprint 10** | **Days 55–60** | **Deployment & Presentation** | ⚪ Planned | `v1.0.0-production-release` |

---

## 📋 Sprint 1 Accomplishments & Verified Functionality

### 1. Monorepo Repository Architecture
- Decoupled `backend/` (FastAPI + SQLAlchemy 2.0) and `frontend/` (Next.js 14 App Router).
- Ephemeral sandbox specs in `docker/` and CI workflow in `.github/workflows/ci.yml`.

### 2. Verified Backend API Gateway
- `GET /health` -> `200 OK` -> `{"status": "healthy", "project": "DevSquad AI Engineering Platform", "version": "0.1.0"}`
- `GET /api/v1/health` -> `200 OK`
- `GET /api/v1/system/status` -> `200 OK` -> Returns live diagnostic checks (Database, LLM, Docker availability).

### 3. Verified Datastore Architecture
- SQLAlchemy 2.0 Async session with 8 core ORM models (`User`, `Repository`, `Issue`, `Run`, `AgentLog`, `Patch`, `TestResult`, `PullRequest`).
- PostgreSQL driver support with SQLite async fallback (`aiosqlite`) for zero-dependency local verification.

### 4. Verified Automated Tests
- Pytest suite (`backend/tests/`): **100% Pass Rate (6/6 tests passing)**.

### 5. Academic AI / ML / DL Documentation
- Published [docs/ai-architecture.md](docs/ai-architecture.md) detailing theoretical and practical relevance of AI, Deep Learning (Transformers/LLMs), Agentic AI (LangGraph state machine), and proposed Machine Learning models (Task difficulty classifier, failure predictor, cost regression).

---

## 🔒 Known Limitations (Sprint 1 Checkpoint)

1. **GitHub API Credentials**: Full GitHub OAuth token exchange and live issue fetching are scheduled for Sprint 2.
2. **Agent Nodes**: LangGraph state graph schemas are established; node execution bodies for Planner, Coder, Tester, and Reviewer are scheduled for Sprints 3–6.
3. **Docker Execution Sandbox**: Container Dockerfile specifications exist in `docker/`; active sandbox invocation is scheduled for Sprint 5.

---

## ➡️ Next Sprint Objectives (Sprint 2 — Days 7–12)

- GitHub OAuth authentication & secret storage.
- GitHub REST API wrapper client (`app/services/github_client.py`).
- Repository syncing & issue explorer endpoints (`GET /api/v1/repos`, `GET /api/v1/issues`).
