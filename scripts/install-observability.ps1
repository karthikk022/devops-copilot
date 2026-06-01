#requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "==> DevOps Copilot — installing observability stack" -ForegroundColor Cyan

$ns = "monitoring"
kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f - | Out-Null

Write-Host "==> Adding Helm repos" -ForegroundColor Cyan
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>$null
helm repo add grafana https://grafana.github.io/helm-charts 2>$null
helm repo update | Out-Null

Write-Host "==> Installing kube-prometheus-stack" -ForegroundColor Cyan
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
    --namespace $ns `
    --values infra/helm/values/kube-prometheus-stack.yaml `
    --version 62.6.0 `
    --wait --timeout 10m

Write-Host "==> Installing Loki" -ForegroundColor Cyan
helm upgrade --install loki grafana/loki `
    --namespace $ns `
    --values infra/helm/values/loki.yaml `
    --version 6.20.0 `
    --wait --timeout 10m

Write-Host "==> Installing Promtail" -ForegroundColor Cyan
helm upgrade --install promtail grafana/promtail `
    --namespace $ns `
    --values infra/helm/values/promtail.yaml `
    --version 6.16.0 `
    --wait --timeout 5m

Write-Host "==> Loading Grafana dashboards as ConfigMaps" -ForegroundColor Cyan
kubectl -n $ns create configmap sample-api-dashboards `
    --from-file=sample-api.json=infra/helm/grafana-dashboards/sample-api.json `
    --dry-run=client -o yaml | kubectl apply -f - | Out-Null

kubectl -n $ns label configmap sample-api-dashboards grafana_dashboard=1 --overwrite | Out-Null

Write-Host "==> Applying ServiceMonitor and PrometheusRule" -ForegroundColor Cyan
kubectl apply -f infra/k8s/manifests/servicemonitor.yaml
kubectl apply -f infra/k8s/manifests/prometheus-rules.yaml

Write-Host ""
Write-Host "==> Done. Verify with:" -ForegroundColor Green
Write-Host "  kubectl get pods -n monitoring"
Write-Host "  kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80"
Write-Host "  # Login: admin / copilot-admin"
Write-Host ""
Write-Host "  kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090"
Write-Host "  kubectl port-forward -n monitoring svc/loki-gateway 3100:80"
