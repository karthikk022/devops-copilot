# 🚀 Pre-Launch Checklist

Complete this in order before posting the project anywhere.

## Phase 1: Repo hygiene (30 min)

- [ ] **Replace all `karthikk022` references** with your GitHub username:
  - `.github/workflows/build-images.yml` (line with `IMAGE_PREFIX`)
  - `helm/devops-copilot/values.yaml` (backend.image.repository, frontend.image.repository)
  - `gitops/argocd/application.yaml` (repoURL)
  - `README.md` (links and badges)

- [ ] **Replace `security@example.com`** in `SECURITY.md` and `CONTRIBUTING.md`

- [ ] **Replace `maintainers@example.com`** in `helm/devops-copilot/Chart.yaml`

- [ ] **Update OpenRouter key in `copilot-backend/.env`** (the original was shared in chat — rotate it)

- [ ] **Verify .env is gitignored**: `git check-ignore -v copilot-backend/.env` should print a rule

- [ ] **Run pre-commit install**: `pip install pre-commit && pre-commit install`

- [ ] **Run pre-commit run --all-files** — fix anything it flags

## Phase 2: Test the whole flow (45 min)

- [ ] **kind cluster**: `kind create cluster --config infra/k8s/kind-config.yaml`
- [ ] **Deploy sample-api**: `.\scripts\setup-local.ps1`
- [ ] **Install observability**: `.\scripts\install-observability.ps1`
- [ ] **Start backend**: `uvicorn app.main:app --reload --port 8000` → check `/api/health` returns ok
- [ ] **Start frontend**: `npm run dev` → open http://localhost:3000
- [ ] **Ask "List all pods"** → should see 2 sample-api pods
- [ ] **Ask "Why is sample-api returning 500s?"** → should see tool call cards
- [ ] **Ask "What is the current memory usage?"** → should see PromQL + result
- [ ] **Open Grafana** → http://localhost:3000 (port-forward 9090 if needed) → dashboard should show data
- [ ] **Check health endpoint**: `curl http://localhost:8000/api/health`

## Phase 3: Test the Helm chart (30 min)

- [ ] **Lint**: `helm lint helm/devops-copilot`
- [ ] **Render locally**: `helm template devops-copilot helm/devops-copilot --set openrouter.apiKey=test`
- [ ] **kubeconform**: `helm template ... | kubeconform -strict -summary`
- [ ] **Install in kind**: `helm install dc helm/devops-copilot --set openrouter.apiKey=$KEY`
- [ ] **Verify all pods running**: `kubectl get pods -n devops-copilot`
- [ ] **Port-forward and test**: `kubectl port-forward svc/dc-frontend 8080:80`

## Phase 4: Record the demo (45 min)

- [ ] **Follow `docs/RECORDING-THE-DEMO.md`** exactly
- [ ] **Save the GIF** to `docs/screenshots/demo.gif`
- [ ] **Record a 30-second Loom** for the LinkedIn post (optional but powerful)
- [ ] **Take 2-3 static screenshots** of: chat UI, Grafana dashboard, terminal showing tool calls

## Phase 5: Publish (15 min)

- [ ] **Create GitHub repo** (public):
  ```bash
  cd devops-copilot
  git init
  git add .
  git commit -m "feat: initial commit - DevOps Copilot MVP

  LLM-powered SRE agent for Kubernetes clusters.
  - RAG over runbooks (pgvector + fastembed)
  - 7 read-only tools (K8s, PromQL, LogQL)
  - Helm chart, ArgoCD, GitHub Actions
  - Trivy, gitleaks, CodeQL
  "
  gh repo create devops-copilot --public --source=. --push
  ```
- [ ] **Wait for first CI run to pass** (5-10 min)
- [ ] **Add topics** to the repo: `kubernetes`, `llm`, `devops`, `ai-agent`, `rag`, `openrouter`, `helm`, `argocd`
- [ ] **Star your own repo** (yes really, it boosts visibility)
- [ ] **Pin the repo** to your GitHub profile

## Phase 6: Apply to jobs (ongoing)

- [ ] **LinkedIn post** — pick a template from `docs/LINKEDIN-POST.md`
- [ ] **Apply to 10 jobs** with a custom note:
  > "I built an open-source LLM agent for Kubernetes troubleshooting (RAG + tool-calling + Helm + ArgoCD). I'd love to show you the live demo and walk through the architecture. Here's the repo: github.com/YOU/devops-copilot"
- [ ] **Update your resume** with this project under "Projects":
  > **DevOps Copilot** — github.com/YOU/devops-copilot
  > LLM-powered SRE agent. FastAPI + Next.js + pgvector + Helm + ArgoCD + GitHub Actions.
  > • Built multi-turn tool-calling agent over 7 read-only K8s/PromQL/LogQL tools
  > • Implemented RAG pipeline with pgvector (HNSW) and fastembed embeddings
  > • Packaged the whole stack as a parameterized Helm chart with RBAC + NetworkPolicies
  > • Set up full GitOps loop with ArgoCD + multi-arch GitHub Actions builds
- [ ] **Send 5 cold DMs** to recruiters at your target companies (not "hi please hire me" — lead with the project)

## Phase 7: Maintenance (1 hr/week)

- [ ] **Triage issues** weekly
- [ ] **Merge Dependabot/Renovate PRs**
- [ ] **Add a feature**: maybe a `k8s_scale` tool with a confirmation UI? Or Slack integration?
- [ ] **Write a blog post** about the build (Dev.to, Hashnode, or your own blog)
- [ ] **Speak at a meetup** — even a 5-min lightning talk is recruiter gold
