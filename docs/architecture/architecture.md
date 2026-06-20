# Architecture

Expense Tracker API v1 — component and deployment views for release candidate `1.0.0-rc.1`.

---

## System context

```mermaid
flowchart TB
    Client[Web / Mobile Client]
    Nginx[Nginx Reverse Proxy]
    API[FastAPI API]
    Worker[Celery Worker]
    Beat[Celery Beat]
    PG[(PostgreSQL)]
    Redis[(Redis)]
    Jaeger[Jaeger OTLP]
    SMTP[SMTP Provider]

    Client --> Nginx
    Nginx --> API
    API --> PG
    API --> Redis
    API -->|enqueue tasks| Redis
    Worker --> Redis
    Worker --> PG
    Beat --> Redis
    Worker --> SMTP
    API --> Jaeger
    Worker --> Jaeger
```

---

## Application layers

```mermaid
flowchart LR
    subgraph Presentation
        Routes[API v1 Endpoints]
    end
    subgraph Application
        Services[Services]
        Events[Event Bus]
        Tasks[Celery Tasks]
    end
    subgraph Domain
        Specs[Specifications]
        Models[SQLAlchemy Models]
    end
    subgraph Infrastructure
        UoW[Unit of Work]
        Repos[Repositories]
        DB[(PostgreSQL)]
    end

    Routes --> Services
    Services --> UoW
    UoW --> Repos
    Repos --> DB
    Services --> Events
    Events --> Tasks
    Services --> Specs
    Repos --> Models
```

---

## Request lifecycle (authenticated)

```mermaid
sequenceDiagram
    participant C as Client
    participant N as Nginx
    participant A as FastAPI
    participant S as Service
    participant D as Database
    participant E as Event Bus
    participant W as Celery Worker

    C->>N: HTTP request + JWT
    N->>A: Proxy + headers
    A->>A: Auth middleware / deps
    A->>S: Business logic
    S->>D: UoW commit
    S->>E: publish domain event
    E->>W: task.delay (async)
    A->>C: JSON response
    W->>D: background read/write
    W->>C: email / file export (side effect)
```

---

## Background jobs

```mermaid
flowchart LR
    subgraph Triggers
        Reg[UserRegistered]
        Budget[BudgetExceeded]
        Upload[Receipt Upload]
        Report[Report API]
        Beat[Beat Schedule]
    end
    subgraph Celery Tasks
        Email[email_tasks]
        Receipt[receipt_tasks]
        Reports[report_tasks]
        Alerts[budget_alerts]
        Maint[maintenance_tasks]
    end

    Reg --> Email
    Budget --> Email
    Upload --> Receipt
    Report --> Reports
    Beat --> Alerts
    Beat --> Maint
```

---

## Data model (core entities)

```mermaid
erDiagram
    USERS ||--o{ TRANSACTIONS : owns
    USERS ||--o{ BUDGETS : sets
    USERS ||--o{ CATEGORIES : custom
    CATEGORIES ||--o{ TRANSACTIONS : classifies
    CATEGORIES ||--o{ BUDGETS : limits
    USERS ||--o{ REFRESH_TOKENS : sessions
    USERS ||--o{ AUDIT_LOGS : actor

    USERS {
        uuid id PK
        string email
        string role
    }
    TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        string transaction_type
        numeric amount
        date transaction_date
    }
    BUDGETS {
        uuid id PK
        uuid user_id FK
        uuid category_id FK
        int month
        int year
    }
    AUDIT_LOGS {
        uuid id PK
        timestamptz created_at
        string action
    }
```

---

## Deployment topology (production)

```mermaid
flowchart TB
    subgraph Host / Orchestrator
        subgraph Compose Stack
            NG[Nginx :80]
            AP[API x4 workers]
            CW[Celery Worker]
            CB[Celery Beat]
            PG[(Postgres volume)]
            RD[(Redis volume)]
            UV[(uploads volume)]
            EV[(exports volume)]
        end
        subgraph Observability profile
            J[Jaeger]
            P[Prometheus]
            G[Grafana]
            F[Flower]
        end
    end

    Internet --> NG
    NG --> AP
    AP --> PG
    AP --> RD
    CW --> PG
    CW --> RD
    AP --> UV
    CW --> UV
    CW --> EV
    AP --> J
    CW --> J
```

---

## Export diagram (PNG/SVG)

To export diagrams for Confluence/wiki:

1. Open [Mermaid Live Editor](https://mermaid.live)
2. Paste a diagram block from this document
3. Export as PNG or SVG

Alternatively, use `@mermaid-js/mermaid-cli`:

```bash
npx @mermaid-js/mermaid-cli -i docs/architecture/architecture.md -o docs/assets/
```

---

## Related documents

- [README.md](../README.md)
- [SECURITY.md](SECURITY.md)
- [deployment/staging-deployment.md](../deployment/staging-deployment.md)
- [deployment/production-readiness.md](../deployment/production-readiness.md)
