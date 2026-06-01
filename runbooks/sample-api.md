# Sample API Runbook

## Overview
`sample-api` is a Node.js Express service deployed in the `devops-copilot` namespace. It exposes a REST API and ships structured JSON logs to stdout.

## Health endpoints
- `GET /healthz` — liveness/readiness
- `GET /metrics` — Prometheus metrics

## Known failure modes (intentional for demo)

### 1. Intermittent 500s on `/api/users/:id`
**Symptom:** ~14% of `/api/users/:id` requests return 500 with `database connection timeout`.
**Log signature:** `database connection timeout` at `error` level with field `userId`.
**Runbook:**
1. Check upstream DB pod: `kubectl get pods -l app=postgres -n devops-copilot`
2. Inspect DB logs: `kubectl logs -l app=postgres -n devops-copilot --tail=200`
3. If DB is healthy, the issue is likely connection pool saturation: check `pg_stat_activity`
4. **Mitigation:** restart sample-api to clear stale pool: `kubectl rollout restart deployment/sample-api -n devops-copilot`

### 2. Slow responses on `/api/slow`
**Symptom:** p95 latency > 3s, occasional 8s+ responses.
**Log signature:** `slow endpoint hit, simulating long query` at `warn` level.
**Runbook:**
1. Check if downstream query is locking: `SELECT * FROM pg_locks WHERE NOT granted;`
2. Check connection pool wait time in DB metrics
3. **Mitigation:** scale sample-api replicas: `kubectl scale deployment/sample-api -n devops-copilot --replicas=4`

### 3. Memory leak via `/api/leak`
**Symptom:** RSS memory grows ~5MB per call, eventually triggers OOMKill.
**Log signature:** `memory leak endpoint hit` at `warn` level with growing `chunks` and `heap_mb`.
**Runbook:**
1. Check current heap: `process_resident_memory_bytes{app="sample-api"}` in Prometheus
2. Confirm leak pattern: should be monotonically increasing
3. **Mitigation:** increase memory limit temporarily AND investigate the `memoryLeak` array in `server.js`
4. **Permanent fix:** remove the global array or add a TTL/LRU eviction policy

### 4. Unhandled promise rejections on `/api/crash`
**Symptom:** `unhandledRejection` events in pod logs, potential restart depending on Node version.
**Log signature:** `unhandled promise rejection` at `fatal` level.
**Runbook:**
1. Identify source: `kubectl logs -l app=sample-api -n devops-copilot | grep "unhandled rejection"`
2. **Mitigation:** wrap async route handlers with try/catch or use express-async-errors middleware

### 5. SIGTERM not handled
**Symptom:** pod takes 30s to terminate (default `terminationGracePeriodSeconds`), in-flight requests dropped.
**Log signature:** `SIGTERM received, refusing graceful shutdown` at `info` level — then silence.
**Runbook:**
1. **Mitigation:** implement proper SIGTERM handler that:
   - Stops accepting new connections
   - Waits for in-flight requests to finish (with timeout)
   - Closes DB connections cleanly
2. Reduce `terminationGracePeriodSeconds` to 15s in deployment

## Useful queries

### Prometheus
```promql
# Request rate by status
sum by (status) (rate(http_requests_total{app="sample-api"}[5m]))

# p95 latency
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{app="sample-api"}[5m])))

# Memory growth (leak detection)
deriv(process_resident_memory_bytes{app="sample-api"}[10m])
```

### Loki
```logql
{namespace="devops-copilot",app="sample-api"} |= "error"

{namespace="devops-copilot",app="sample-api"} | json | level="error"

{namespace="devops-copilot",app="sample-api"} |~ "memory leak|database timeout"
```

## Escalation
- Slack: `#devops-copilot-alerts`
- On-call: PagerDuty `devops-copilot` service
- Dashboard: https://grafana.example.com/d/devops-copilot-sample-api
