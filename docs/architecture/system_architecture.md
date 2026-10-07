# DevSquad Complete System Architecture Diagram

> **Document Version**: 1.0 (Sprint 1 Checkpoint)  
> **Location**: `docs/architecture/system_architecture.md`  

---

## 1. End-to-End System Architecture

```
                    +----------------------------------+
                    |           USER / DEVELOPER       |
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
|  AGENT  | |  AGENT  | |  AGENT  | |  AGENT   |
| (PLANNED| | (PLANNED| | (PLANNED| | (PLANNED |
| Sprint3)| | Sprint4)| | Sprint6)| | Sprint6) |
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
| [PLANNED SPRINT2]|       |  Ephemeral Cont.) |
+------------------+       | [PLANNED SPRINT5] |
                           +-------------------+
```

---

## 2. Component Implementation Status Matrix

```mermaid
graph TD
    subgraph Layer 1: Frontend - IMPLEMENTED
        F1["Next.js 14 Dashboard Shell"]
        F2["System Health Status Card"]
        F3["Responsive Navigation & Layout"]
    end

    subgraph Layer 2: API Gateway - IMPLEMENTED
        A1["FastAPI Async App"]
        A2["GET /health"]
        A3["GET /api/v1/system/status"]
        A4["Pydantic Configuration Engine"]
    end

    subgraph Layer 3: Persistence - IMPLEMENTED
        D1["PostgreSQL / SQLite Async Engine"]
        D2["8 SQLAlchemy Core ORM Models"]
    end

    subgraph Layer 4: Multi-Agent Orchestrator - PLANNED (Sprints 3-6)
        O1["Planner Agent Node"]
        O2["Coder Agent Node"]
        O3["Tester Agent Node"]
        O4["Reviewer Agent Node"]
    end

    subgraph Layer 5: Sandbox & Integrations - PLANNED (Sprints 2 & 5)
        I1["GitHub OAuth & Issue API"]
        I2["Docker Ephemeral Sandbox"]
        I3["GitHub PR Workflow Engine"]
    end

    F1 <--> A1
    A1 <--> D1
    A1 -.-> O1
    O1 -.-> I1
    O3 -.-> I2
```
