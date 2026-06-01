<div align="center">

# DevOps Copilot

**An LLM-powered SRE assistant that talks to your live Kubernetes cluster.**

Ask in plain English. The copilot queries Prometheus, searches Loki, inspects pods, and answers with runbook-cited diagnosis — all streamed in real time.

[Demo](#demo) · [Quickstart](#quickstart) · [Architecture](#architecture) · [Tools](#tools) · [Deploy](#deploy)

</div>

---

## What it does

```
You:   "Why is sample-api returning 500s?"

Copilot:
   🔧 k8s_list_pods(namespace="devops-copilot", label_selector="app=sample-api")
        → 2 pods running, 0 restarts
   🔧 k8s_get_pod_logs(pod="sample-api-abc", tail_lines=50)
        → last log: {"level":"error","msg":"database connection timeout"}
   🔧 loki_query(query='{app="sample-api"} |= "error"')
        → 12 error lines in last 10m

   ## Diagnosis
   The sample-api is intermittently returning 500 on /api/users/:id
   (~14% of requests). The application logs a `database connection
   timeout` error. This is a known failure mode in the runbook.

   ## Recommended action
   Restart sample-api to clear the connection pool:
   ```bash
   kubectl rollout restart deployment/sample-api -n devops-copilot
   ```

   Sources: sample-api.md › Intermittent 500s
   Model: meta-llama/llama-3.3-70b-instruct:free
```

## Why this project

This is a **single, end-to-end portfolio project** for AI/Cloud/DevOps roles. It demonstrates:

| Skill | Where it lives |
|-------|----------------|
| **Generative AI** | OpenRouter (free Llama 3.3 70B) with tool-calling, model fallback, streaming |
| **RAG** | pgvector + fastembed (`BAAI/bge-small-en-v1.5`) over Markdown runbooks |
| **Agentic systems** | Multi-turn tool-use loop with 7 read-only tools |
| **Kubernetes** | k3s/Hetzner cluster, Helm chart, RBAC, NetworkPolicies, ServiceAccounts |
| **Observability** | Prometheus, Loki, Grafana, pre-built dashboards, alert rules |
| **Backend** | FastAPI, asyncpg, Pydantic v2, SSE streaming, OpenAI-compatible client |
| **Frontend** | Next.js 14, TypeScript, Tailwind, shadcn-style components, React Markdown |
| **IaC** | Terraform for Hetzner Cloud, Helm for app deploys |
| **CI/CD** | GitHub Actions (lint, test, build, push to GHCR, Trivy scan) |
| **GitOps** | ArgoCD Application with auto-sync and self-heal |
| **Security** | gitleaks pre-commit, Trivy, CodeQL, checkov, kubeconform |
| **Cost** | Runs on free tiers (OpenRouter free, GHCR free, Hetzner ~$5/mo) |

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  User's Browser (Next.js 14 / TypeScript)                        │
│  ↓ SSE streaming                                                 │
├──────────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Python 3.11)                                   │
│  ├─ LLM Client        → OpenRouter (Llama 3.3 70B free)         │
│  ├─ Agent Loop        → 7 tools, max 5 iterations               │
│  ├─ RAG Pipeline      → fastembed → pgvector cosine search      │
│  └─ Tool Registry     → K8s · Prometheus · Loki                 │
│  ↓ in-cluster (ServiceAccount token)                             │
├──────────────────────────────────────────────────────────────────┤
│  Kubernetes Cluster (k3s / Hetzner Cloud)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐             │
│  │ sample-api  │  │ postgres    │  │ prometheus   │             │
│  │ (buggy app) │  │ + pgvector  │  │ + loki       │             │
│  └─────────────┘  └─────────────┘  └──────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| LLM | OpenRouter free tier | No vendor lock-in, free, model fallback |
| Agent | LangChain-style custom loop | Minimal deps, full control over SSE |
| Embedding | fastembed + BAAI/bge-small-en-v1.5 | 80MB, no PyTorch, 384-dim |
| Vector DB | pgvector | Single Postgres, HNSW index |
| Backend | FastAPI + Pydantic v2 | Async-native, OpenAPI auto-generated |
| Frontend | Next.js 14 + Tailwind | Modern, fast, great DX |
| K8s | k3s + Helm | Lightweight, production-grade |
| Observability | kube-prometheus-stack + Loki | Industry standard, free |
| CI | GitHub Actions | Built into the repo |
| GitOps | ArgoCD | De facto standard |
| Security | gitleaks + Trivy + CodeQL | Belt and suspenders |

## Tools the agent can call

| Tool | Purpose |
|------|---------|
| `k8s_list_pods` | List pods in a namespace, filter by label |
| `k8s_get_pod_logs` | Tail logs from a pod (or specific container) |
| `k8s_describe_pod` | Pod status, conditions, container states, events |
| `k8s_list_deployments` | Deployments with replica status |
| `prom_query` | PromQL instant query (current value) |
| `prom_query_range` | PromQL range query (time series) |
| `loki_query` | LogQL query against Loki |

All **read-only by design** — no scale, no exec, no delete. RBAC enforced at the ClusterRole level.

## Quickstart

### Local (5 min)

**Prereqs:** Docker Desktop, `kind`, `kubectl`, `helm`, `node 20+`, `python 3.11+`

```powershell
# 1. Create cluster + deploy sample-api
git clone https://github.com/karthikk022/devops-copilot.git
cd devops-copilot
kind create cluster --config infra/k8s/kind-config.yaml
docker build -t sample-api:1.0.0 apps/sample-api
kind load docker-image sample-api:1.0.0 --name devops-copilot
kubectl apply -f infra/k8s/manifests/

# 2. Add observability
.\scripts\install-observability.ps1
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# open http://localhost:3000 → admin / copilot-admin

# 3. Start backend (in another terminal)
cd copilot-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env: set OPENROUTER_API_KEY=sk-or-v1-...
uvicorn app.main:app --reload --port 8000

# 4. Start frontend (in another terminal)
cd apps/frontend
npm install
copy .env.example .env.local
npm run dev
# open http://localhost:3000
```

### Production deploy (Helm + ArgoCD)

```bash
# 1. One-time per cluster
kubectl apply -f gitops/argocd/appproject.yaml
kubectl apply -f gitops/argocd/application.yaml

# 2. Set the OpenRouter key (CI does this via sealed-secret / external-secrets)
kubectl create secret generic devops-copilot-openrouter \
  -n devops-copilot \
  --from-literal=OPENROUTER_API_KEY=$OPENROUTER_API_KEY

# 3. Or one-shot Helm:
helm install devops-copilot ./helm/devops-copilot \
  --namespace devops-copilot --create-namespace \
  --set openrouter.apiKey=$OPENROUTER_API_KEY
```

ArgoCD will keep the cluster reconciled to `main` from then on.

## Demo questions

Once running, try these in the chat UI:

1. **"List all pods in the devops-copilot namespace."**
   → 1 tool call: `k8s_list_pods`

2. **"Why is sample-api returning 500 errors? Investigate."**
   → 3-5 tool calls: pods → logs → Loki search → diagnosis

3. **"Show me the p95 latency of sample-api for the last 30 minutes."**
   → 1 tool call: `prom_query_range`

4. **"Search Loki for memory-related errors in the last 10 minutes."**
   → 1 tool call: `loki_query`

5. **"What should I do about the memory leak? Look it up in the runbook."**
   → RAG retrieval + runbook-cited answer

## Repo layout

```
devops-copilot/
├── apps/
│   ├── sample-api/             # Intentionally buggy Node.js app (the demo target)
│   └── frontend/               # Next.js 14 chat UI
├── copilot-backend/            # FastAPI backend
│   ├── app/
│   │   ├── llm.py              # OpenRouter client
│   │   ├── rag.py              # RAG orchestration
│   │   ├── vectorstore.py      # pgvector client
│   │   ├── embeddings.py       # fastembed
│   │   ├── chunker.py          # markdown chunker
│   │   ├── tools/              # 7 tool implementations
│   │   └── api/                # FastAPI routes
│   └── scripts/ingest_runbooks.py
├── helm/devops-copilot/        # Production Helm chart
├── infra/
│   ├── terraform/              # Hetzner Cloud k3s cluster
│   └── k8s/                    # raw K8s manifests (educational)
├── runbooks/                   # RAG corpus (markdown)
├── gitops/argocd/              # ArgoCD Application + AppProject
├── .github/workflows/          # 5 CI workflows
├── scripts/                    # setup-local, install-observability
└── docs/                       # day-1.md through day-7.md
```

## CI/CD

5 GitHub Actions workflows run on every PR:

- `ci.yml` — ruff, pytest, next lint, tsc, build, hadolint, terraform validate
- `build-images.yml` — multi-arch build & push to GHCR, auto-PR to bump image tags
- `security.yml` — gitleaks, Trivy fs+image scan, CodeQL (Python + TS)
- `helm-lint.yml` — helm lint + render + kubeconform
- `release.yml` — semver-tagged release with multi-arch images

Plus Dependabot + Renovate for dependency updates.

## Security

- **Pre-commit**: gitleaks, ruff, prettier, checkov, no-commit-to-branch
- **CI**: gitleaks-action, Trivy SARIF → Code Scanning, Trivy image scan (fail on HIGH/CRITICAL)
- **SAST**: CodeQL for Python and TypeScript
- **K8s**: NetworkPolicies, read-only RBAC, no `latest` tags in prod
- **Secrets**: never committed, `copilot-backend/.env` is gitignored
- See [SECURITY.md](SECURITY.md) for the disclosure policy.

## License

MIT — see [LICENSE](LICENSE).

## Status

| Day | Deliverable | Status |
|-----|-------------|--------|
| 1   | Repo scaffold + buggy sample app + Terraform | ✅ done |
| 2   | Observability stack (Prom + Loki + Grafana) | ✅ done |
| 3   | FastAPI + Next.js + OpenRouter | ✅ done |
| 4   | RAG pipeline (pgvector + fastembed) | ✅ done |
| 5   | K8s tools + tool-calling agent (7 tools) | ✅ done |
| 6   | CI + GitOps + security + Helm chart | ✅ done |
| 7   | Demo GIF + final polish | 🔜 next |
