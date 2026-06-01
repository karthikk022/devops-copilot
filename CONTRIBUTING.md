# Contributing

Thanks for your interest in the DevOps Copilot! 🎉

## Quick start

```bash
# 1. Clone
git clone https://github.com/karthikk022/devops-copilot.git
cd devops-copilot

# 2. Install pre-commit hooks (REQUIRED)
pip install pre-commit
pre-commit install

# 3. Backend dev
cd copilot-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # or: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # then edit, set OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000

# 4. Frontend dev (in another terminal)
cd apps/frontend
npm install
copy .env.example .env.local
npm run dev

# 5. K8s dev (in a third terminal)
kind create cluster --config infra/k8s/kind-config.yaml
.\scripts\setup-local.ps1
.\scripts\install-observability.ps1
```

## Architecture in 30 seconds

- **Frontend** (Next.js 14): chat UI, streams SSE from backend
- **Backend** (FastAPI): LLM client, RAG pipeline, tool registry, agent loop
- **Cluster** (k3s/k8s): sample-api (the buggy demo), postgres+pgvector (vector store), prometheus+loki (observability)
- **Tools** (Python): 4 K8s tools + 2 PromQL + 1 LogQL, all read-only
- **LLM**: OpenRouter free tier (Llama 3.3 70B → 8B → Qwen Coder fallback)

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Loki query tool
fix(chat): handle empty tool_call arguments
docs: update day-5 guide
chore(deps): bump fastembed to 0.4.2
ci: add Trivy scan to security workflow
```

## Code style

| Component | Formatter | Linter |
|-----------|-----------|--------|
| Python (backend) | `ruff format` | `ruff check` |
| TypeScript (frontend) | Prettier (default) | `eslint --max-warnings 0` |
| YAML (helm, k8s, ci) | Prettier | checkov, kubeconform |
| Terraform | `terraform fmt` | `tflint` |

## Adding a new tool

1. Create a new file in `copilot-backend/app/tools/`
2. Subclass `Tool` from `base.py`
3. Implement `name`, `description`, `parameters` (JSON schema), and `execute(**kwargs) -> str`
4. Register in `registry.py:build_registry()`
5. Add a test in `copilot-backend/tests/test_tools.py`
6. Add a friendly name mapping in `apps/frontend/components/tool-call.tsx`
7. Add a demo prompt to `apps/frontend/lib/prompts.ts`

## Adding a new runbook

1. Drop a `.md` file in `runbooks/`
2. Restart the backend (auto-ingest runs on startup)
3. Or trigger manually: `python -m scripts.ingest_runbooks`

## Reporting security issues

**Do not open public issues for security bugs.** Email karthikchinnaiyan0223@gmail.com instead.

## License

MIT — see [LICENSE](LICENSE).
