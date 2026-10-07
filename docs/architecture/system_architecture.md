# DevSquad System Architecture Blueprint

> **System Blueprint**: DevSquad Platform Architecture  
> **Document Status**: Active Technical Specification  

---

## 1. System Context & Overview

**DevSquad** is designed as a modular, event-driven platform for automated software engineering workflows. The platform combines a modern reactive web dashboard, an asynchronous REST API, a relational datastore, and a stateful AI orchestration engine.

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

---

## 2. Component Implementation Status Matrix

```mermaid
graph TD
    subgraph Layer 1: Client Dashboard - IMPLEMENTED
        F1["Next.js 14 Dashboard Shell"]
        F2["System Health Diagnostics Card"]
        F3["Responsive Navigation Layout"]
    end

    subgraph Layer 2: API Gateway - IMPLEMENTED
        A1["FastAPI Async App"]
        A2["GET /health"]
        A3["GET /api/v1/system/status"]
        A4["Pydantic Configuration Engine"]
    end

    subgraph Layer 3: Datastore - IMPLEMENTED
        D1["PostgreSQL / SQLite Async Engine"]
        D2["8 SQLAlchemy Core ORM Models"]
    end

    subgraph Layer 4: Orchestrator - PLANNED
        O1["Planner Subsystem"]
        O2["Coder Subsystem"]
        O3["Tester Subsystem"]
        O4["Reviewer Subsystem"]
    end

    subgraph Layer 5: Sandbox & Integrations - PLANNED
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
