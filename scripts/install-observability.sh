#!/usr/bin/env bash
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${CYAN}==> $1${NC}"; }
ok()  { echo -e "${GREEN}==> $1${NC}"; }

NS=monitoring
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f - >/dev/null

log "Adding Helm repos"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
helm repo update >/dev/null

log "Installing kube-prometheus-stack"
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace "$NS" \
  --values infra/helm/values/kube-prometheus-stack.yaml \
  --version 62.6.0 \
  --wait --timeout 10m

log "Installing Loki"
helm upgrade --install loki grafana/loki \
  --namespace "$NS" \
  --values infra/helm/values/loki.yaml \
  --version 6.20.0 \
  --wait --timeout 10m

log "Installing Promtail"
helm upgrade --install promtail grafana/promtail \
  --namespace "$NS" \
  --values infra/helm/values/promtail.yaml \
  --version 6.16.0 \
  --wait --timeout 5m

log "Loading Grafana dashboards as ConfigMaps"
kubectl -n "$NS" create configmap sample-api-dashboards \
  --from-file=sample-api.json=infra/helm/grafana-dashboards/sample-api.json \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl -n "$NS" label configmap sample-api-dashboards grafana_dashboard=1 --overwrite >/dev/null

log "Applying ServiceMonitor and PrometheusRule"
kubectl apply -f infra/k8s/manifests/servicemonitor.yaml
kubectl apply -f infra/k8s/manifests/prometheus-rules.yaml

ok "Done. Verify with:"
echo "  kubectl get pods -n monitoring"
echo "  kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80"
echo "  # Login: admin / copilot-admin"
echo ""
echo "  kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090"
echo "  kubectl port-forward -n monitoring svc/loki-gateway 3100:80"
