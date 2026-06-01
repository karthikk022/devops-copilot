# GitOps with ArgoCD

This directory contains the ArgoCD manifests for **declarative, GitOps-driven** deploys of the DevOps Copilot.

## Files

| File | Purpose |
|------|---------|
| `application.yaml` | The `Application` CR pointing ArgoCD at the Helm chart in this repo |
| `appproject.yaml` | The `AppProject` CR scoping which repos/namespaces/resources the app can manage |

## Install

### 1. Install ArgoCD (one-time per cluster)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 2. Apply the AppProject + Application

```bash
kubectl apply -f gitops/argocd/appproject.yaml
kubectl apply -f gitops/argocd/application.yaml
```

### 3. Watch the magic

```bash
# Get the ArgoCD CLI
brew install argocd   # or scoop install argocd-cli on Windows

# Login (initial admin password is the name of the pod)
argocd login <argocd-server>

# Watch the app
argocd app watch devops-copilot
argocd app sync devops-copilot --prune
```

## How deploys work

```
git push origin main
       ↓
GitHub Actions:
  - CI: lint, test, typecheck
  - build-images.yml: build & push to ghcr.io
  - security.yml: gitleaks, trivy, codeql
       ↓
CI opens a PR: "chore(images): bump to <sha>"
       ↓
You merge the PR
       ↓
ArgoCD detects the change in helm/devops-copilot/values.yaml
       ↓
ArgoCD syncs the cluster (auto, every 3 min)
       ↓
kubectl rollout deployment/devops-copilot-backend
```

**No `kubectl apply` from your laptop. No SSH. No imperative commands.** The cluster reconciles itself from Git.

## Disaster recovery

If the cluster is wiped:
```bash
# ArgoCD is already gone too. Reinstall:
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f gitops/argocd/appproject.yaml
kubectl apply -f gitops/argocd/application.yaml
# ArgoCD reads from Git → cluster converges to the desired state.
```

That's it. **The whole system rebuilds itself from a single git repo.**
