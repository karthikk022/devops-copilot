#!/usr/bin/env bash
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${CYAN}==> $1${NC}"; }
ok()  { echo -e "${GREEN}==> $1${NC}"; }
err() { echo -e "${RED}==> $1${NC}"; }

missing=()
for cmd in docker kind kubectl helm; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    missing+=("$cmd")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  err "Missing tools: ${missing[*]}"
  exit 1
fi

log "Creating kind cluster"
kind create cluster --config infra/k8s/kind-config.yaml

log "Building sample-api image"
docker build -t sample-api:1.0.0 apps/sample-api

log "Loading image into kind"
kind load docker-image sample-api:1.0.0 --name devops-copilot

log "Deploying manifests"
kubectl apply -f infra/k8s/manifests/

log "Waiting for rollout"
kubectl rollout status deployment/sample-api -n devops-copilot --timeout=60s

ok "Done. Try:"
echo "  kubectl get pods -n devops-copilot"
echo "  kubectl port-forward -n devops-copilot svc/sample-api 3000:80"
echo "  curl http://localhost:3000/"
