# Prometheus Alerts Runbook

## Overview
This runbook covers the alerting rules installed with `kube-prometheus-stack` for the `devops-copilot` cluster. Alerts are evaluated every 30s by the in-cluster Prometheus and routed to Alertmanager.

## Alert rules in production

### 1. `HighErrorRate` (warning, fires at >5% 5xx for 5m)
**Symptom:** More than 5% of requests to `sample-api` return 5xx for 5+ minutes.
**PromQL:**
```promql
sum(rate(http_requests_total{job="sample-api",status=~"5.."}[5m]))
  /
sum(rate(http_requests_total{job="sample-api"}[5m])) > 0.05
```
**Runbook:**
1. Check `sample-api` logs in Loki: `{app="sample-api"} |= "error"`
2. Confirm the upstream DB pod is ready: `kubectl get pods -l app=postgres -n devops-copilot`
3. Inspect recent deployments: `kubectl rollout history deployment/sample-api -n devops-copilot`
4. **Mitigation:** roll back the last deployment if the spike correlates with a release: `kubectl rollout undo deployment/sample-api -n devops-copilot`
5. **Escalate:** page on-call if error rate stays >10% for 15m.

### 2. `HighMemoryUsage` (warning, fires at >85% for 10m)
**Symptom:** Pod memory usage exceeds 85% of its limit for 10+ minutes.
**PromQL:**
```promql
max(container_memory_working_set_bytes{pod=~"sample-api-.*"} / container_spec_memory_limit_bytes{pod=~"sample-api-.*"}) by (pod) > 0.85
```
**Runbook:**
1. Identify the leaking pod: check `kubectl top pod -n devops-copilot`
2. Hit `/api/leak` endpoint is the most common cause (memory leak in the demo app)
3. **Mitigation:** restart the affected pod: `kubectl delete pod -l app=sample-api -n devops-copilot`
4. **Long-term fix:** raise the memory limit in `infra/k8s/manifests/sample-api.yaml` and redeploy.

### 3. `PodCrashLooping` (critical, fires after 5 restarts in 10m)
**Symptom:** A pod is restarting more than 5 times in the last 10 minutes.
**PromQL:**
```promql
rate(kube_pod_container_status_restarts_total{namespace="devops-copilot"}[10m]) * 10 * 60 > 5
```
**Runbook:**
1. List crashlooping pods: `kubectl get pods -n devops-copilot --field-selector=status.phase!=Running`
2. Inspect logs from the previous instance: `kubectl logs <pod> -n devops-copilot --previous`
3. Common causes: bad image pull, missing ConfigMap, OOMKill, failed healthcheck
4. **Mitigation:** fix the root cause, then delete the pod to let the controller restart it cleanly.

### 4. `KubeAPIServerDown` (critical, fires at 0 for 2m)
**Symptom:** Prometheus cannot scrape any `apiserver` target for 2+ minutes.
**PromQL:**
```promql
up{job="apiserver"} == 0
```
**Runbook:**
1. Check control-plane node: `kubectl get nodes`
2. Inspect kubelet logs on the control-plane: `journalctl -u kubelet -n 200`
3. **Escalate:** this is a cluster-wide issue — page SRE immediately.

## Adding a new alert

1. Edit `infra/helm/values/kube-prometheus-stack.yaml` and add your `PrometheusRule` to `additionalPrometheusRules`.
2. Validate PromQL in the Prometheus UI (`/graph`) before committing.
3. Run `helm template kube-prometheus-stack prometheus-community/kube-prometheus-stack -f infra/helm/values/kube-prometheus-stack.yaml` locally to render.
4. Commit + push. ArgoCD will pick up the change and apply it.

## Silencing an alert
For short-term noise (deploys, known flakes):
```bash
amtool silence add --alertmanager.url=http://alertmanager:9093 \
  --comment "deploying sample-api" --duration 30m \
  --matchers='alertname="HighErrorRate",namespace="devops-copilot"'
```
