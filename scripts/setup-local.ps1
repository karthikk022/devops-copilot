#requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "==> DevOps Copilot — local setup" -ForegroundColor Cyan

$missing = @()
foreach ($cmd in @("docker", "kind", "kubectl", "helm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        $missing += $cmd
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing tools: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Install with winget:"
    foreach ($cmd in $missing) {
        switch ($cmd) {
            "docker"  { Write-Host "  winget install Docker.DockerDesktop" }
            "kind"    { Write-Host "  winget install Kubernetes.kind" }
            "kubectl" { Write-Host "  winget install Kubernetes.kubectl" }
            "helm"    { Write-Host "  winget install Helm.Helm" }
        }
    }
    exit 1
}

Write-Host "==> Creating kind cluster" -ForegroundColor Cyan
kind create cluster --config infra/k8s/kind-config.yaml

Write-Host "==> Building sample-api image" -ForegroundColor Cyan
docker build -t sample-api:1.0.0 apps/sample-api

Write-Host "==> Loading image into kind" -ForegroundColor Cyan
kind load docker-image sample-api:1.0.0 --name devops-copilot

Write-Host "==> Deploying manifests" -ForegroundColor Cyan
kubectl apply -f infra/k8s/manifests/

Write-Host "==> Waiting for rollout" -ForegroundColor Cyan
kubectl rollout status deployment/sample-api -n devops-copilot --timeout=60s

Write-Host ""
Write-Host "Done. Try:" -ForegroundColor Green
Write-Host "  kubectl get pods -n devops-copilot"
Write-Host "  kubectl port-forward -n devops-copilot svc/sample-api 3000:80"
Write-Host "  curl http://localhost:3000/"
