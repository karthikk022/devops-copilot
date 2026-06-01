# Day 1 — Foundation

## What was built

- **Repo structure** with `apps/`, `copilot-backend/`, `infra/`, `helm/`, `docs/`, `scripts/`
- **Sample buggy app** (`apps/sample-api/`) — Node.js Express with 5 intentional issues the copilot will later diagnose:
  1. `GET /api/users/:id` → 500 every 7th call (simulated DB timeout)
  2. `GET /api/slow` → 2-8s random delay
  3. `GET /api/error` → unhandled exception
  4. `GET /api/leak` → heap memory grows ~5MB per call
  5. `GET /api/crash` → unhandled promise rejection (not fatal, but logged)
  6. **Bonus:** no SIGTERM handler (K8s graceful shutdown is broken)
- **Terraform** to provision a k3s cluster on Hetzner Cloud (`infra/terraform/`)
- **kind config** for zero-cost local K8s (`infra/k8s/kind-config.yaml`)
- **K8s manifests** for namespace, deployment, service, ingress

## Try it locally

### Prereqs (install once)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [helm](https://helm.sh/docs/intro/install/)

Windows (winget):
```powershell
winget install Docker.DockerDesktop
winget install Kubernetes.kind
winget install Kubernetes.kubectl
winget install Helm.Helm
```

### Run
```powershell
kind create cluster --config infra/k8s/kind-config.yaml
docker build -t sample-api:1.0.0 apps/sample-api
kind load docker-image sample-api:1.0.0 --name devops-copilot
kubectl apply -f infra/k8s/manifests/
kubectl get pods -n devops-copilot -w
```

Port-forward and test:
```powershell
kubectl port-forward -n devops-copilot svc/sample-api 3000:80
curl http://localhost:3000/
curl http://localhost:3000/api/users/1
```

### Generate "interesting" data for the copilot
```powershell
1..20 | ForEach-Object { curl -s http://localhost:3000/api/users/1 > $null }
curl http://localhost:3000/api/slow
curl http://localhost:3000/api/error
1..5 | ForEach-Object { curl -s http://localhost:3000/api/leak > $null }
```

You should see:
- ~3 of the `/api/users/1` calls return 500
- `/api/error` returns 500
- `/api/leak` heap grows each call
- `/metrics` shows non-zero request counts

## Next: Day 2

Install **Prometheus + Loki + Grafana** via Helm and start scraping the sample app.
