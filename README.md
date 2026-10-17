# DevSquad

> **Production-Grade Multi-Agent AI Software Engineering Platform**

DevSquad converts real GitHub issues into verified, reviewable software changes through a controlled multi-agent workflow:
```text
GitHub Issue → Repository Context → Planner → Coder → Sandbox Tester → Independent Reviewer → Human Approval → Pull Request or Patch Export
```

---

## Architecture & Layout

```text
Devsquard/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entrypoint with CORS & lifespan
│   │   ├── api/
│   │   │   ├── router.py        # Central API v1 router
│   │   │   └── routes/          # Health, Repositories, Issues, Runs (including Orchestration API)
│   │   ├── core/
│   │   │   ├── config.py        # Centralized Pydantic V2 settings & secret masking
│   │   │   ├── logging.py       # Structured logging with SecretRedactionFilter
│   │   │   ├── security.py      # Secret redaction, safe relative path checks, SHA-256
│   │   │   └── exceptions.py    # Core domain exception hierarchy
│   │   ├── db/
│   │   │   ├── base.py          # SQLAlchemy 2.0 Base & TimestampMixin
│   │   │   ├── session.py       # Async engine & session factory with SQLite PRAGMA
│   │   │   └── models/          # 8 core entities (User, Repo, Issue, Run, Patch, PR, Approval, AgentLog)
│   │   ├── schemas/             # Pydantic V2 typed domain contracts
│   │   ├── services/            # Core Platform Services
│   │   │   ├── health_service.py    # Subsystem connectivity checks (DB, LLM, Docker)
│   │   │   ├── github_service.py    # Read-only async GitHub client
│   │   │   ├── context_ranker.py    # Multi-signal context selection & budgeting
│   │   │   ├── llm/                 # LLM provider abstraction (Gemini, OpenAI)
│   │   │   └── agents/              # Multi-Agent Services (Planner, Coder, Tester, Reviewer)
│   │   └── orchestration/       # LangGraph Orchestrator & State Persistence
│   │       ├── state.py         # DevSquadState, WorkflowStatus & WorkflowStage enums
│   │       ├── checkpointer.py  # AsyncSqliteSaver & InMemorySaver checkpointer factory
│   │       ├── nodes.py         # Asynchronous node execution functions
│   │       ├── routing.py       # Conditional edge routing & bounded repair cycles
│   │       ├── graph.py         # StateGraph construction & compilation
│   │       ├── service.py       # DevSquadOrchestrator facade (start, resume, cancel, state)
│   │       └── exceptions.py    # Orchestration exception hierarchy
│   ├── alembic/                 # Async database migrations
│   ├── tests/                   # Pytest suite (unit, integration, security, orchestration)
│   ├── alembic.ini              # Alembic migration configuration
│   ├── pyproject.toml           # Backend dependency manifest and tooling configs
│   └── .env.example             # Environment template
├── IMPLEMENTATION_STATUS.md     # Honest progress tracking report
└── README.md
```

---

## Multi-Agent Workflow Architecture

```mermaid
flowchart TD
    START([Start / Run Initialized]) --> validate_input[validate_input_node\nVerify Repo, Issue & Run]
    validate_input -->|Valid| context_prep[context_preparation_node\nRank & Budget Repo Context]
    validate_input -->|Invalid| finalization[finalization_node\nPersist Terminal State]

    context_prep --> planner[planner_node\nGenerate Structured Plan]
    planner -->|Plan Generated| coder[coder_node\nSynthesize Minimal Diff Patch]
    planner -->|Planning Failed| finalization

    coder -->|Patch Applied| tester[sandbox_tester_node\nDocker Isolation / AST Fallback]
    coder -->|Patch Gen Failed| finalization

    tester --> reviewer[reviewer_node\nIndependent Multi-Angle Review]

    reviewer -->|Review Approved\nor Advisory Low/Med| finalization
    reviewer -->|Request Changes / Test Failed\n& attempts < max| coder
    reviewer -->|Max Attempts Reached| finalization

    finalization -->|Success / Valid Patch| WAITING_APPROVAL([WAITING_FOR_APPROVAL\nHuman Decision Gate])
    finalization -->|Failures / Errors| FAILED([FAILED])
```

---

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/runs/{run_id}/start` | Launch or queue a workflow run through LangGraph |
| `POST` | `/api/v1/runs/{run_id}/resume` | Resume an interrupted or waiting run |
| `POST` | `/api/v1/runs/{run_id}/cancel` | Cancel an in-flight run and update state |
| `POST` | `/api/v1/runs/{run_id}/approve` | Cryptographic anti-tamper human patch approval |
| `GET` | `/api/v1/runs/{run_id}/state` | Fetch current typed LangGraph state and snapshot |
| `GET` | `/api/v1/runs/{run_id}/events` | Stream or list real-time agent execution events |

All `/api/v1/runs` endpoints enforce HMAC-SHA256 Bearer token authentication and strict repository ownership authorization (rejecting unauthenticated requests with 401 and cross-user tampering with 403).

---

## Local Development Setup (Windows)

### Prerequisites

1. **Python**: Python 3.11+ (Python 3.13.1 verified).
2. **Git**: Ensure Git is installed. If missing:
   ```powershell
   winget install --id Git.Git -e --source winget
   ```
3. **Docker Desktop** *(Optional)*: If running, container-isolated tests execute in Docker; if unavailable, DevSquad falls back cleanly to AST static analysis.

### Installation

1. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install backend dependencies:
   ```powershell
   cd backend
   pip install -e .
   pip install -e ".[dev]"
   ```

3. Setup environment variables:
   ```powershell
   copy .env.example .env
   ```

4. Run database migrations:
   ```powershell
   alembic upgrade head
   ```

---

## Running Automated Tests

Run the full test suite with coverage:
```powershell
cd backend
pytest --cov=app --cov-report=term-missing
```

---

## Starting the Backend Server

Start the FastAPI application with Uvicorn:
```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API root: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Swagger documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Composite health check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
