# Day 5 — Tool-Calling Agent

## What was built

The copilot is now a **read-only agent**. The LLM decides which tools to call, the backend executes them, results flow back into the conversation, and the LLM synthesizes a final answer — streamed to the UI in real time with tool call cards.

### 7 tools, 1 agent loop

| Tool | What it does |
|------|--------------|
| `k8s_list_pods` | List pods in a namespace, filter by label |
| `k8s_get_pod_logs` | Tail logs from a specific pod/container |
| `k8s_describe_pod` | Pod status, conditions, container states, recent events |
| `k8s_list_deployments` | Deployments with replica status |
| `prom_query` | PromQL instant query (current value) |
| `prom_query_range` | PromQL range query (time series) |
| `loki_query` | LogQL query against Loki |

All tools are **read-only** — no scale, no exec, no delete. Safety first.

### The agent loop

```
User: "Why is sample-api returning 500s?"
  ↓
Backend: build messages [system_prompt, RAG context, user_query]
Backend: stream LLM with tools=[all 7 schemas]
  ↓
LLM: emits tool_calls [k8s_list_pods(namespace="devops-copilot", label_selector="app=sample-api")]
  ↓
Backend: emits "tool_call" SSE event → frontend shows card
Backend: executes k8s_list_pods → emits "tool_result" SSE event → frontend updates card
Backend: appends tool message to conversation, loops back
  ↓
LLM: emits tool_calls [k8s_get_pod_logs(pod="sample-api-abc", tail_lines=50)]
  ↓ (repeat)
LLM: emit tool_calls [loki_query(query='{app="sample-api"} |= "error"')]
  ↓ (repeat)
LLM: no more tool_calls → stream final answer
  ↓
Frontend: renders markdown answer + tool call history + RAG citations
```

### File map

```
copilot-backend/app/tools/
├─ base.py              # Tool ABC, ToolRegistry, truncate helper
├─ k8s.py              # K8sClient + 4 K8s tools
├─ prometheus.py       # PromClient + 2 Prom tools
├─ loki.py             # LokiClient + 1 Loki tool
└─ registry.py         # build_registry() factory

copilot-backend/app/
├─ llm.py              # +tool-calling support, +tool_call_delta events
├─ api/chat.py         # rewritten: full agent loop with SSE tool events
└─ main.py             # lifespan now builds the tool registry
```

### Frontend
- `components/tool-call.tsx` — collapsible amber card with args, result preview, char count
- `lib/api.ts` — handles `tool_call` and `tool_result` events
- `lib/types.ts` — `ToolCallRecord` type
- New demo prompts that trigger tool use (e.g. *"List all pods in the devops-copilot namespace"*)

### K8s
- `infra/k8s/manifests/copilot-backend-rbac.yaml` — ServiceAccount + ClusterRole + ClusterRoleBinding (read-only access to pods, deployments, events, etc.)

## K8s API access — in-cluster vs local

The `K8sClient` tries, in order:
1. **`K8S_API_URL` env var** (set in `copilot-backend.yaml` ConfigMap)
2. **In-cluster service account** (auto-detected at `/var/run/secrets/kubernetes.io/serviceaccount/token`)
3. **Local fallback** (no auth — only works if the API server is on `https://kubernetes.default.svc.cluster.local`)

For **local dev with kind**: you need to forward the K8s API. Easiest:
```bash
kubectl proxy --port=8001
# Then in copilot-backend/.env:
# K8S_API_URL=http://localhost:8001
```

For **in-cluster** (the usual case): set `serviceAccountName: copilot-backend` on the Deployment (already done in `copilot-backend.yaml`) and apply `copilot-backend-rbac.yaml`. The SA token is auto-mounted; the K8sClient reads it from `/var/run/secrets/kubernetes.io/serviceaccount/`.

## Try it

**End-to-end demo questions** that exercise the agent loop:

| Question | Tools the LLM will call |
|----------|-------------------------|
| "List all pods in devops-copilot" | `k8s_list_pods` |
| "Why is sample-api returning 500s?" | `k8s_list_pods` → `k8s_get_pod_logs` (probably twice) → `loki_query` |
| "What is the current error rate?" | `prom_query` |
| "Show memory trend over 30 min" | `prom_query_range` |
| "Search for 'memory leak' in logs" | `loki_query` |

You should see:
1. A streaming answer start forming
2. Then a `tool_call` card appears (amber) showing which tool is being called
3. Card updates with the result preview
4. Multiple tool calls in sequence
5. Final answer with `## Diagnosis` and `## Recommended action` sections
6. RAG citation chips if the runbook matched

## Day 5 → Day 6 handoff

The agent works against your live cluster. Day 6 hardens it for production:
- **GitHub Actions CI**: lint, test, build, push images, security scan
- **ArgoCD GitOps**: declarative K8s deploys from Git
- **gitleaks pre-commit**: prevent the OpenRouter key from ever being committed
- **Helm chart**: package the whole app for one-command deploys
- **Trivy image scan**: block vulnerable images

## Next: Day 6

Production hardening — CI/CD, GitOps, security. The boring stuff that recruiters LOVE seeing.
