# Day 3 — Chat Layer

## What was built

### Backend (`copilot-backend/`)
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app with CORS, lifespan, route wiring |
| `app/config.py` | Pydantic-settings, reads `.env` |
| `app/llm.py` | OpenRouter client (OpenAI-compatible) with streaming + **model fallback** |
| `app/models.py` | Pydantic v2 request/response models |
| `app/api/chat.py` | `POST /api/chat` with Server-Sent Events streaming |
| `app/api/health.py` | `GET /api/health` for the UI to show model + status |
| `Dockerfile` | Multi-stage, non-root, healthcheck |
| `requirements.txt` | Pinned deps (fastapi 0.115, openai 1.51, sse-starlette 2.1) |

**Key features:**
- Streams tokens via SSE as the model generates them
- Falls back to smaller models if the primary 70B is rate-limited
- Sends OpenRouter attribution headers (`HTTP-Referer`, `X-Title`)
- Engineered system prompt with cluster context, response style, and the 5 known bugs

### Frontend (`apps/frontend/`)
| File | Purpose |
|------|---------|
| `app/page.tsx` + `app/layout.tsx` | Next.js 14 App Router |
| `components/chat.tsx` | Main chat container with auto-scroll, abort, suggestions |
| `components/message.tsx` | Markdown + syntax-highlighted code (PromQL, LogQL, yaml) |
| `components/typing-indicator.tsx` | Animated 3-dot pulse |
| `components/suggestions.tsx` | 6 clickable demo prompts on empty state |
| `components/ui/button.tsx` | shadcn-style button (CVA) |
| `lib/api.ts` | SSE consumer using ReadableStream |
| `lib/types.ts`, `lib/utils.ts`, `lib/prompts.ts` | Shared types + tailwind-merge |
| `Dockerfile` | Standalone Next.js output, non-root |

**UI highlights:**
- Dark theme, glassmorphic header, gradient background
- Auto-scroll with "jump to bottom" pill when scrolled up
- Health indicator in header (green/yellow/red dot + model name)
- Stop button replaces Send while streaming
- Clear chat (trash icon) in header
- Mobile-responsive textarea with Shift+Enter for newline
- Code blocks highlighted via `rehype-highlight` (GitHub Dark)

### K8s manifests
- `copilot-backend.yaml` — Deployment + Service + ConfigMap + Secret + **NetworkPolicy** (egress to OpenRouter/Prom/Loki only)
- `copilot-frontend.yaml` — Deployment + Service + Ingress

## Run locally (dev mode, 2 terminals)

**Terminal 1 — backend:**
```powershell
cd copilot-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set OPENROUTER_API_KEY=sk-or-v1-...
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```powershell
cd apps/frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000

## Run in K8s

```powershell
# 1. Edit the secret first
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
kubectl create secret generic copilot-backend-secrets `
  -n devops-copilot `
  --from-literal=OPENROUTER_API_KEY=$env:OPENROUTER_API_KEY `
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Build & load images
docker build -t copilot-backend:0.1.0  copilot-backend
docker build -t copilot-frontend:0.1.0 apps/frontend
kind load docker-image copilot-backend:0.1.0  --name devops-copilot
kind load docker-image copilot-frontend:0.1.0 --name devops-copilot

# 3. Deploy
kubectl apply -f infra/k8s/manifests/copilot-backend.yaml
kubectl apply -f infra/k8s/manifests/copilot-frontend.yaml

# 4. Access
kubectl port-forward -n devops-copilot svc/copilot-frontend 8080:80
# http://localhost:8080
```

## Try the demo prompts

The Suggestions page offers 6 prompts. Try these in order:
1. **"What is this project..."** — sanity check LLM works
2. **"What are the 5 intentional bugs..."** — tests the system prompt knowledge
3. **"Show me a PromQL query..."** — checks response style guidance
4. **"Explain the architecture in 3 sentences"** — model reasoning

You should see markdown with code blocks formatted properly, model name in the footer, and no streaming issues.

## What's NOT here yet (by design)

- ❌ **RAG over runbook** — Day 4
- ❌ **Tool calling** (k8s exec, PromQL runner) — Day 5
- The LLM today can describe the system and write queries, but cannot actually execute them or read real logs.

## Next: Day 4

Add **pgvector + RAG pipeline**: chunk the runbook, embed with a free embedding model, store in Postgres with pgvector, retrieve top-k on every query, inject into the LLM context. The copilot then becomes runbook-aware and answers "what do I do when X?" using your actual docs.
