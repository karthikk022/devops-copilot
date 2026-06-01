# Architecture

Detailed architecture diagrams for the DevOps Copilot. See [README.md](../README.md) for the short version.

## System overview

```mermaid
flowchart TB
    User([User in browser])
    UI[Next.js 14 Chat UI<br/>apps/frontend]
    BE[FastAPI Backend<br/>copilot-backend]

    subgraph K8s[Kubernetes Cluster]
        SA[ServiceAccount<br/>copilot-backend]
        API[K8s API Server]
        subgraph Workloads[devops-copilot namespace]
            Sample[sample-api<br/>2 replicas, buggy]
            PG[(postgres<br/>+ pgvector)]
            BE2[copilot-backend pod]
            FE[copilot-frontend pod]
        end
        subgraph Monitoring[monitoring namespace]
            Prom[Prometheus]
            Loki[Loki]
            Graf[Grafana]
        end
    end

    OR[OpenRouter<br/>free Llama 3.3 70B]
    HF[Hugging Face<br/>fastembed models]

    User -->|HTTPS| UI
    UI -->|SSE /api/chat| BE
    BE -->|HTTPS in-cluster| OR
    BE -->|load model| HF
    BE -.->|Bearer token| API
    API -->|read| Workloads
    BE <-->|pgvector| PG
    Prom -.->|scrape| Workloads
    Loki <-.->|push| Workloads
    Prom --> Graf
    Loki --> Graf
```

## Request flow (one chat message)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js UI
    participant BE as FastAPI
    participant RAG as RAG Pipeline
    participant LLM as OpenRouter
    participant Tools as Tool Registry
    participant K8s as K8s API
    participant Prom as Prometheus
    participant Loki as Loki

    User->>FE: "Why is sample-api returning 500s?"
    FE->>BE: POST /api/chat (SSE)
    BE->>RAG: retrieve(query)
    RAG-->>BE: top-4 runbook chunks
    BE->>BE: build system prompt + RAG context
    BE->>LLM: stream(messages, tools)
    LLM-->>BE: tool_call(k8s_list_pods)
    BE-->>FE: SSE tool_call event
    BE->>Tools: call(k8s_list_pods, {...})
    Tools->>K8s: GET /api/v1/namespaces/.../pods
    K8s-->>Tools: pod list
    Tools-->>BE: result
    BE-->>FE: SSE tool_result event
    Note over BE,LLM: Loop continues...

    BE->>LLM: stream(messages+tool_result, tools)
    LLM-->>BE: tool_call(k8s_get_pod_logs)
    Note over BE,LLM: ... more iterations ...

    LLM-->>BE: text tokens (no more tool_calls)
    BE-->>FE: SSE token events (streamed)
    LLM-->>BE: finish_reason=stop
    BE-->>FE: SSE done event
    FE-->>User: Markdown answer with citations
```

## RAG pipeline

```mermaid
flowchart LR
    RB[runbooks/*.md] -->|chunk_markdown| C[chunks]
    C -->|fastembed| E[embeddings 384-d]
    E -->|UPSERT| PG[(pgvector<br/>HNSW index)]
    Q[user query] -->|fastembed| QE[query embedding]
    QE -->|cosine search top-k| PG
    PG -->|chunks| CTX[formatted context]
    CTX --> SYS[system prompt]
    Q --> SYS
    SYS --> LLM
```

## Agent loop (the heart of Day 5)

```mermaid
stateDiagram-v2
    [*] --> BuildContext
    BuildContext: Build messages<br/>(system + RAG + history)
    BuildContext --> StreamLLM
    StreamLLM: Stream LLM with tools
    StreamLLM --> CheckFinish
    CheckFinish: finish_reason?
    CheckFinish --> FinalAnswer: stop
    CheckFinish --> ExecuteTools: tool_calls
    CheckFinish --> StreamMore: text tokens
    StreamMore --> StreamLLM
    ExecuteTools: Execute tool(s) in parallel
    ExecuteTools --> AppendResults
    AppendResults: Append tool messages
    AppendResults --> MaxIterCheck
    MaxIterCheck: iter < MAX?
    MaxIterCheck --> StreamLLM: yes
    MaxIterCheck --> FinalAnswer: no (give up)
    FinalAnswer: Stream final answer
    FinalAnswer --> [*]
```

## CI/CD flow

```mermaid
flowchart LR
    Dev[git push] --> CI[GitHub Actions CI<br/>lint · test · build]
    CI -->|main| Build[build-images<br/>multi-arch GHCR]
    Build --> PR[auto PR<br/>bump image tags]
    PR --> Merge[merge to main]
    Merge --> Argo[ArgoCD detects]
    Argo --> Sync[kubectl apply<br/>via Helm]
    Sync --> K8s[Cluster reconciled]
```

## Component map (files)

```
copilot-backend/app/
├── main.py              FastAPI app + lifespan (connects everything)
├── config.py            Pydantic settings
├── llm.py               OpenRouter client (streaming + tool calls)
├── embeddings.py        fastembed (BAAI/bge-small-en-v1.5)
├── vectorstore.py       asyncpg + pgvector + HNSW
├── chunker.py           markdown-aware chunker
├── rag.py               RAG orchestration
├── models.py            Pydantic request/response models
├── tools/               Tool implementations
│   ├── base.py          Tool ABC + ToolRegistry
│   ├── k8s.py           4 K8s tools (read-only)
│   ├── prometheus.py    2 PromQL tools
│   ├── loki.py          1 LogQL tool
│   └── registry.py      build_registry() factory
└── api/                 FastAPI routes
    ├── chat.py          Agent loop with SSE
    ├── health.py        Health/readiness
    └── ingest.py        Manual re-ingestion endpoint

apps/frontend/
├── app/                 Next.js App Router
│   ├── layout.tsx       Root layout
│   ├── page.tsx         Home (renders <Chat/>)
│   └── globals.css      Tailwind + custom
├── components/
│   ├── chat.tsx         Main chat container
│   ├── message.tsx      Markdown bubble + tool calls + citations
│   ├── tool-call.tsx    Amber collapsible card
│   ├── suggestions.tsx  6 demo prompts on empty state
│   ├── typing-indicator.tsx
│   └── ui/              shadcn-style primitives
└── lib/
    ├── api.ts           SSE consumer (ReadableStream)
    ├── types.ts         Shared types
    ├── utils.ts         cn() helper (clsx + twMerge)
    └── prompts.ts       Suggestion chips

helm/devops-copilot/
├── Chart.yaml           Chart metadata
├── values.yaml          200+ lines of config
└── templates/           12 templates
    ├── _helpers.tpl     Naming + labels
    ├── backend.yaml     Deployment + Service + HPA + NetPol + ServiceMonitor
    ├── frontend.yaml    Deployment + Service + Ingress
    ├── postgres.yaml    Deployment + PVC + Service
    ├── configmap.yaml   All env vars
    ├── secret.yaml      OpenRouter key + Postgres creds
    ├── runbooks-configmap.yaml
    ├── rbac.yaml        ServiceAccount + ClusterRole + Binding
    ├── serviceaccount.yaml
    ├── resources.yaml   ResourceQuota + PDB
    ├── postgres-init-configmap.yaml
    └── NOTES.txt        Post-install instructions
```

## Deployment topology (Hetzner Cloud + ArgoCD)

```mermaid
flowchart TB
    subgraph Git[GitHub]
        Repo[devops-copilot repo<br/>main branch]
        Actions[GitHub Actions<br/>5 workflows]
        GHCR[ghcr.io<br/>container images]
        Secrets[Repo secrets<br/>OPENROUTER_API_KEY]
    end

    subgraph Hetzner[Hetzner Cloud - fsn1]
        LB[Hetzner Load Balancer]
        subgraph K3s[k3s control plane]
            Argo[ArgoCD<br/>self-managing]
            K8sAPI[K8s API server]
            subgraph ns1[devops-copilot ns]
                BE[backend]
                FE[frontend]
                PG[postgres+pgvector]
            end
            subgraph ns2[monitoring ns]
                Prom[prometheus]
                Loki[loki]
                Graf[grafana]
            end
        end
    end

    Repo --> Actions
    Actions --> GHCR
    Actions --> Secrets
    Repo -.->|polls every 3min| Argo
    Argo -->|helm install/upgrade| K8sAPI
    K8sAPI --> ns1
    K8sAPI --> ns2
    GHCR -->|image pull| BE
    GHCR -->|image pull| FE
    LB --> FE
    User([User]) -->|HTTPS| LB
```
