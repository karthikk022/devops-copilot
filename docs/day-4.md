# Day 4 — RAG Pipeline

## What was built

### Components
| File | Purpose |
|------|---------|
| `app/embeddings.py` | fastembed client (`BAAI/bge-small-en-v1.5`, 384-dim, ONNX runtime, no PyTorch) |
| `app/chunker.py` | Markdown-aware chunker (splits on H2 sections, sliding window with overlap) |
| `app/vectorstore.py` | asyncpg + pgvector wrapper with HNSW index, cosine distance |
| `app/rag.py` | RAG orchestration: embed → search → format context |
| `app/api/ingest.py` | `POST /api/ingest` + `GET /api/ingest/sources` |
| `copilot-backend/scripts/ingest_runbooks.py` | CLI to ingest runbooks on demand |

### Pipeline flow
```
User query
   ↓
embed (fastembed, local)
   ↓
pgvector cosine search (top-k=4, threshold=0.35)
   ↓
format as "Retrieved runbook context" block
   ↓
inject into LLM system prompt
   ↓
LLM generates grounded answer with citations
```

### Infrastructure
- `infra/k8s/manifests/postgres.yaml` — `pgvector/pgvector:pg16` Deployment + PVC + Service
- `infra/k8s/manifests/postgres-init.yaml` — init SQL to create the `vector` extension
- `infra/k8s/manifests/runbooks-configmap.yaml` — runbook content baked into a ConfigMap, mounted at `/app/runbooks` in the backend pod
- Updated `copilot-backend.yaml` — mounts runbook ConfigMap, sets `DATABASE_URL` and RAG env vars, bumped to 1Gi memory for fastembed

### Frontend
- Citation chips appear under bot messages when RAG was used
- New suggestion prompts target the runbook ("What should I do if sample-api is returning 500s…")

## Why these choices
- **fastembed + bge-small-en-v1.5** — 80MB model, no PyTorch, runs in-process, ~50ms per embed. Perfect for a portfolio project that needs to be free and offline.
- **pgvector** — Postgres extension. One fewer service to operate. HNSW index for fast ANN search.
- **Cosine distance** — standard for normalized embeddings.
- **HNSW over IVFFLAT** — works well at any dataset size, no training step.
- **Markdown-aware chunking** — preserves section context for better retrieval than naive char splits.
- **Auto-ingest on startup** — zero ops burden; backend reads `/app/runbooks` and upserts on boot.

## Run locally (without K8s)

You need Postgres+pgvector. Easiest path: docker compose or local install.

```bash
docker run -d --name pgvector \
  -e POSTGRES_USER=copilot -e POSTGRES_PASSWORD=copilot -e POSTGRES_DB=copilot \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

Then:
```powershell
cd copilot-backend
copy .env.example .env
# edit .env: OPENROUTER_API_KEY=...
# edit DATABASE_URL=postgresql://copilot:copilot@localhost:5432/copilot

.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
# On startup: logs "auto_ingest_complete {ingested: N, files: [...]}"
```

## Ingest more docs

### Via CLI
```powershell
python -m scripts.ingest_runbooks path/to/more-docs/
```

### Via API
```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/runbooks"}'
```

### Via the UI
Coming in a later iteration (Day 7 polish).

## Test the RAG

Ask the copilot:
- **"What should I do if sample-api is returning 500s?"** → expects a citation to the runbook's "Intermittent 500s" section
- **"How do I mitigate the memory leak?"** → expects citation to the memory leak section
- **"What is Kubernetes?"** → no citations (out of corpus), pure LLM knowledge

You should see:
- **Source chips** under the response showing `sample-api.md › Intermittent 500s` etc.
- The LLM's answer directly references the runbook procedures

## Day 4 → Day 5 handoff

The LLM can now **read** the runbook but cannot **act** on the cluster. Day 5 adds:
- **K8s tools** (kubectl wrapper): get pods, logs, describe, scale, restart, exec
- **Prometheus tools** (HTTP client): instant queries, range queries
- **Loki tools** (HTTP client): LogQL queries
- **Tool-calling loop** in the chat endpoint: LLM decides which tool to call, backend executes, result returned to LLM, LLM synthesizes answer

This is where the copilot goes from "chatbot that knows docs" to "agent that runs the cluster."

## Next: Day 5

Wire up **5 K8s/Prom/Loki tools** the LLM can call via OpenRouter's tool-calling API. End state: user asks "why is the pod crashing?" → copilot calls `k8s_get_pod` → calls `loki_query_logs` → calls `k8s_get_pod_logs` → synthesizes diagnosis.
