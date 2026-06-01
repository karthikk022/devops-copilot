# copilot-backend

FastAPI backend for the DevOps Copilot. Streams chat completions from OpenRouter.

## Quickstart (local dev)

```powershell
cd copilot-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env and set OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the OpenAPI explorer.

## Endpoints

- `GET  /` — service info
- `GET  /api/health` — health + LLM config status
- `POST /api/chat` — chat (SSE stream)
- `GET  /docs` — Swagger UI
- `GET  /redoc` — ReDoc

## Request example

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the p95 latency for sample-api?"}
    ]
  }'
```

## Container

```bash
docker build -t copilot-backend:dev copilot-backend
docker run --rm -p 8000:8000 --env-file copilot-backend/.env copilot-backend:dev
```

## Day 3 scope
- ✅ FastAPI + SSE streaming
- ✅ OpenRouter client with model fallback
- ✅ System prompt with cluster context
- ❌ Tool calling (Day 5)
- ❌ RAG over runbook (Day 4)
