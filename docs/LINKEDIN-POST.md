# LinkedIn Post — Templates

Three versions. Pick the one that matches your style.

---

## Version A — "Shipped" (recommended)

I just shipped a project I've been working on: **DevOps Copilot** — an LLM-powered SRE assistant that talks to a live Kubernetes cluster.

Ask it "Why is this pod crashing?" and it:
🔧 Calls `k8s_list_pods` to find the pod
🔧 Calls `k8s_get_pod_logs` to read the error
🔧 Calls `loki_query` to search related logs
🔧 Retrieves the runbook via RAG (pgvector)
🔧 Streams a Markdown answer with cited sources

The whole agent loop runs on the free tier of Llama 3.3 70B (via OpenRouter), with automatic fallback to smaller models.

Tech stack:
• FastAPI + Next.js 14 + TypeScript
• pgvector + fastembed (BAAI/bge-small-en-v1.5)
• Prometheus + Loki + Grafana (kube-prometheus-stack)
• K8s + Helm + ArgoCD GitOps
• GitHub Actions: CI, multi-arch builds to GHCR, Trivy, gitleaks, CodeQL
• Terraform for Hetzner Cloud

Everything runs locally with `kind` or deploys to production with one `helm install`. The whole repo — Terraform, Helm chart, ArgoCD manifests, CI workflows — is in one place.

🔗 github.com/YOU/devops-copilot

---

## Version B — "Learning in Public" (for engagement)

Last week I was debugging a 500 error in a sample service. I thought: what if my SRE tools could answer the question for me?

So I built **DevOps Copilot**.

It's an AI agent that lives in your Kubernetes cluster. You ask in plain English. It queries Prometheus, searches Loki, inspects pods, and replies with a diagnosis — citing the actual runbook it retrieved.

The interesting part wasn't the LLM. It was the **agent loop**:

1. Stream the LLM with a list of available tools
2. When the LLM decides to call a tool, pause the stream
3. Execute the tool (K8s API / PromQL / LogQL)
4. Feed the result back to the LLM
5. Repeat up to 5 iterations
6. Stream the final synthesized answer

End-to-end: ~2 seconds for a typical diagnosis.

The whole project (Terraform, Helm chart, ArgoCD, CI/CD, 7-day build log) is on GitHub if you want to see how the pieces fit together.

🔗 github.com/YOU/devops-copilot

What would YOU add to this? I'm thinking:
- A `k8s_scale` tool (with a confirmation UI)
- Multi-cluster support
- A Slack bot wrapper

---

## Version C — "Hiring" (if you're job-hunting)

For anyone hiring AI/Cloud/DevOps engineers — I just finished a project that demonstrates everything I want to work on:

**DevOps Copilot** — an LLM-powered SRE agent.

It has:
✓ Generative AI (RAG, tool-calling agent, streaming)
✓ Cloud-native (K8s, Helm, ArgoCD, Terraform)
✓ DevOps (GitHub Actions, multi-arch builds, security scanning)
✓ Observability (Prometheus, Loki, Grafana, custom dashboards)
✓ Backend (FastAPI, asyncpg, Pydantic v2)
✓ Frontend (Next.js 14, TypeScript, Tailwind)
✓ Security (gitleaks, Trivy, CodeQL, NetworkPolicies, RBAC)

The README walks through every layer. The CI runs on every PR. The Helm chart installs the whole stack with one command.

If this is the kind of work your team does, let's talk: you@example.com

🔗 github.com/YOU/devops-copilot

---

## What to include in every post

✅ GitHub link (or your own domain)
✅ One concrete thing the project DOES (not just "uses AI")
✅ A photo of YOU using it (1-2 second selfie with the app in background works)
✅ 2-3 relevant hashtags: #kubernetes #devops #llm #ai #sre

## What to AVOID

❌ Don't say "I used AI to build this" (sounds like vibe-coding)
❌ Don't paste a wall of text — use line breaks
❌ Don't tag recruiters you don't know
❌ Don't post without a demo GIF/video
