# Day 2 — Observability

## What was built

| Component | Tool | Purpose |
|-----------|------|---------|
| Metrics | **Prometheus** (kube-prometheus-stack) | Scrapes `/metrics` from sample-api, 7d retention |
| Logs | **Loki** + **Promtail** (DaemonSet) | Aggregates all pod logs in `devops-copilot` namespace |
| Visualization | **Grafana** (kube-prometheus-stack) | Pre-built dashboard for sample-api |
| Discovery | **ServiceMonitor** CRD | Auto-discovers sample-api endpoints |
| Alerting | **PrometheusRule** CRD | 5 alert rules for known failure modes |
| Knowledge | **Runbook** (`runbooks/sample-api.md`) | Plain-English remediation steps — this is what the copilot will RAG over later |

## Alert rules (in Prometheus)
- `SampleApiHighErrorRate` — 5xx > 10% for 5min
- `SampleApiHighLatency` — p95 > 3s for 5min
- `SampleApiHighMemory` — RSS > 200MB for 5min
- `SampleApiPodCrashLooping` — restart rate > 0
- `SampleApiOOMKilled` — OOM kill in last 15min

## Install

```powershell
# Make sure Day 1 is done (cluster running, sample-api deployed)
.\scripts\install-observability.ps1
```

Takes ~5 minutes (Helm pulls several charts).

## Verify

```powershell
# Wait for all monitoring pods
kubectl get pods -n monitoring -w

# Open Grafana (admin / copilot-admin)
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000 → "DevOps Copilot — sample-api" dashboard

# Open Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# http://localhost:9090 → Status > Targets (should see "serviceMonitor/monitoring/sample-api/0")

# Open Loki (verify logs flow)
kubectl port-forward -n monitoring svc/loki-gateway 3100:80
# http://localhost:3100/ready should return "ready"
```

## Generate data for the dashboard

```powershell
# Normal traffic
1..30 | ForEach-Object -Parallel { curl -s http://localhost:3000/api/users/1 > $null } -ThrottleLimit 5

# Slow traffic
curl http://localhost:3000/api/slow

# Errors
1..10 | ForEach-Object { curl -s http://localhost:3000/api/users/1 > $null }

# Memory leak
1..5 | ForEach-Object { curl -s http://localhost:3000/api/leak > $null }
```

You should see:
- Request rate, error %, latency panels populate
- Memory panel climbs
- Live logs panel streams JSON logs with parsed `level` label

## Day 2 → Day 3 handoff

The LLM will need:
- **Metrics URL** → `http://kube-prometheus-stack-prometheus.monitoring:9090` (in-cluster)
- **Logs URL** → `http://loki-gateway.monitoring:80` (in-cluster)
- **LogQL queries** (documented in runbook)
- **Runbook** → `runbooks/sample-api.md` (this is the RAG corpus)
- **Sample questions** (the 5 failure modes)

## Next: Day 3

Build the **FastAPI backend** + **Next.js chat UI** + **OpenRouter LLM integration** — a chatbot that talks first, RAG comes on Day 4.
