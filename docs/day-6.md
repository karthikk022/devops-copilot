# Day 6 — Production Hardening (CI/CD · GitOps · Security)

## What was built

### CI/CD — 5 GitHub Actions workflows

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | every push + PR | ruff, pytest (with pgvector service), next lint, tsc, next build, hadolint, terraform validate |
| `build-images.yml` | every push to main + PRs touching app code | multi-arch (amd64+arm64) build & push to GHCR, cache by scope, auto-PR to bump image tags in `helm/values.yaml` |
| `security.yml` | weekly + every push + PR | gitleaks secret scan, Trivy fs scan (SARIF → Code Scanning), Trivy image scans (fail on HIGH/CRITICAL), CodeQL for Python and TS |
| `helm-lint.yml` | PRs touching helm/ | `helm lint`, `helm template` render, kubeconform with strict mode |
| `release.yml` | tag `v*.*.*` | build & push with semver tag, create GitHub release |
| `renovate.yml` | weekly | auto-PRs for dependency updates (grouped by ecosystem) |

Plus **Dependabot** as a backup: `.github/dependabot.yml` covers npm, pip, docker, github-actions.

### Helm chart — one-command deploys

`helm/devops-copilot/` is a production-grade chart with:
- `Chart.yaml` with metadata, icon, kubeVersion constraint
- `values.yaml` with 200+ lines of fully-parameterized config
- 12 templates: backend, frontend, postgres, configmap, secret, rbac, networkpolicies, ingress, autoscaling, service monitor, resource quota, PDB
- `_helpers.tpl` with naming conventions, label selectors, secret resolution
- `NOTES.txt` that warns if no OpenRouter key is set
- `.helmignore` for clean packaging

**Install in one command:**
```bash
helm install devops-copilot ./helm/devops-copilot \
  --namespace devops-copilot --create-namespace \
  --set openrouter.apiKey=$OPENROUTER_API_KEY
```

### GitOps — ArgoCD

`gitops/argocd/`:
- `application.yaml` — `Application` CR pointing at the Helm chart in this repo, with `automated: prune, selfHeal`
- `appproject.yaml` — `AppProject` CR scoping allowed repos/namespaces/resources (no cluster-admin)
- `README.md` — full GitOps loop diagram + disaster recovery

**Flow:** `git push` → CI builds images → CI opens PR to bump image tags → you merge → ArgoCD detects → cluster reconciles.

### Security — 4 layers

| Layer | Tool | Config |
|-------|------|--------|
| Pre-commit | gitleaks, ruff, prettier, checkov, no-commit-to-branch | `.pre-commit-config.yaml` |
| CI secret scan | gitleaks-action | `security.yml` |
| Filesystem CVE | Trivy SARIF → Code Scanning | `security.yml` |
| Image CVE | Trivy (fail on HIGH/CRITICAL) | `security.yml` |
| SAST | CodeQL (Python + TS) | `security.yml` |
| Helm misconfig | checkov | `.pre-commit-config.yaml` |
| K8s schema | kubeconform strict | `helm-lint.yml` |

Plus `SECURITY.md` with disclosure policy and supported versions.

### Polish
- `CONTRIBUTING.md` — quickstart, architecture 30-sec, commit conventions, "adding a tool" walkthrough
- `.github/PULL_REQUEST_TEMPLATE.md` — checklist for PRs
- `LICENSE` — MIT

## How to publish this project

```bash
cd devops-copilot
git init
git add .
git commit -m "feat: initial commit - DevOps Copilot MVP"
gh repo create devops-copilot --public --source=. --remote=origin --push
```

After pushing:
1. Replace `karthikk022` with your GitHub username everywhere (3 places: `build-images.yml`, `values.yaml`, `argocd/application.yaml`)
2. Replace `security@example.com` in `SECURITY.md` with your real email
3. Rotate the OpenRouter API key in `copilot-backend/.env` (since it was shared in chat)
4. Enable GitHub Actions
5. Wait for the first CI run to turn green

## Final Day 6 → Day 7 handoff

Everything is wired. Day 7 is **polish + ship**:
- Record a 2-min demo GIF
- Add architecture diagram to README
- Test end-to-end with the Hetzner deploy
- Write the killer LinkedIn post
- Apply to 10 jobs

## Next: Day 7

The final day. Time to make recruiters *want* to click your repo.
