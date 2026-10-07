# DevSquad Technical Foundation Specification

> **Document Status**: Production Architectural Baseline  
> **Target System**: DevSquad AI Software Engineering Platform  

---

## 1. Executive Summary

**DevSquad** is an AI-assisted software engineering platform designed to streamline issue resolution and codebase modifications. This document outlines the technical foundation of DevSquad, detailing the system's architecture, backend REST API, async datastore, frontend dashboard, and automated testing framework.

The current implementation provides a robust engineering skeleton that enables future multi-agent orchestration, repository indexing, sandboxed code execution, and automated pull request generation.

---

## 2. Implemented Architecture

DevSquad adopts a decoupled, event-driven multi-tier architecture:
- **Client Tier**: Built with Next.js 14 App Router, TypeScript, Tailwind CSS, and shadcn/ui.
- **API Tier**: Built with Python FastAPI (Async ASGI) leveraging Pydantic V2 for payload validation.
- **Persistence Tier**: Built with SQLAlchemy 2.0 Async Session supporting PostgreSQL and an `aiosqlite` async driver for zero-dependency local development.
- **Orchestration Tier**: Structured state machine definitions designed for LangGraph compatibility.

---

## 3. Backend Implementation

The backend application is located in `backend/app/` and exposes the following endpoints:
- `GET /health`: Basic health check returning system name and version.
- `GET /api/v1/health`: API v1 health verification endpoint.
- `GET /api/v1/system/status`: Real-time system infrastructure diagnostic endpoint reporting database connectivity, LLM provider settings, and container runner availability.

### Configuration Management
System settings are managed using `pydantic-settings` in `backend/app/core/config.py`. Environment variables are loaded securely from `.env` files without hardcoding credentials into source code.

---

## 4. Datastore & ORM Models

The database schema is defined using SQLAlchemy 2.0 ORM models in `backend/app/db/models/`:
- **`User`**: Account identity and authentication records.
- **`Repository`**: Connected codebases tracked by the system.
- **`Issue`**: Cached GitHub issues submitted for resolution.
- **`Run`**: Workflow execution instances tracking execution status.
- **`AgentLog`**: Structured execution trace logs generated during workflow runs.
- **`Patch`**: Unified code diffs generated for code modifications.
- **`TestResult`**: Output logs, duration, and exit codes captured from sandbox test executions.
- **`PullRequest`**: GitHub Pull Request metadata generated upon approval.

---

## 5. Frontend Dashboard

The frontend application is located in `frontend/src/` and provides:
- **Layout System**: Navigation sidebar and application header.
- **System Health Diagnostics**: Real-time polling component fetching diagnostic data from `/api/v1/system/status`.
- **Workflow Overview**: Visual architecture overview detailing the conceptual roles of Planner, Coder, Tester, and Reviewer components.

---

## 6. Automated Testing & Verification

Automated backend unit tests are located in `backend/tests/` and built using `pytest` and `httpx.AsyncClient`:
- `test_config.py`: Validates environment configuration parsing.
- `test_health.py`: Validates API health endpoints and system status responses.
- `test_models.py`: Validates database model creation, relationships, and persistence.

---

## 7. Security Architecture

- **Credential Isolation**: All secrets are configured via `.env` files (excluded from repository tracking via `.gitignore`).
- **Schema Validation**: All request and response payloads are sanitized using Pydantic schemas.
- **Execution Isolation**: Code sandbox specifications require rootless, resource-constrained container environments.

---

## 8. Current Limitations

1. **GitHub Integration**: Repository issue fetching and OAuth token exchange are defined in the API roadmap.
2. **Agent Node Execution**: LangGraph state schemas are established; active node logic is scheduled for future development phases.
3. **Execution Sandbox**: Docker specifications exist; automated container runner invocation is queued for future integration.
