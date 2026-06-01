import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from .base import Tool

logger = logging.getLogger(__name__)

SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SA_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


class K8sClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = True,
    ):
        if api_url:
            self.api_url = api_url.rstrip("/")
        else:
            self.api_url = "https://kubernetes.default.svc.cluster.local"

        if token:
            self.token = token
        elif Path(SA_TOKEN_PATH).exists():
            self.token = Path(SA_TOKEN_PATH).read_text()
        else:
            self.token = ""

        if verify and Path(SA_CA_PATH).exists():
            self.verify = SA_CA_PATH
        else:
            self.verify = verify

        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                verify=self.verify,
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                timeout=httpx.Timeout(15.0, connect=5.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        client = await self._ensure()
        r = await client.get(path, params=params or {})
        r.raise_for_status()
        return r.json()


class K8sListPods(Tool):
    name = "k8s_list_pods"
    description = "List pods in a Kubernetes namespace, optionally filtered by label selector (e.g. app=sample-api)."
    parameters = {
        "type": "object",
        "properties": {
            "namespace": {
                "type": "string",
                "description": "Kubernetes namespace (default: devops-copilot)",
            },
            "label_selector": {
                "type": "string",
                "description": "Optional label selector, e.g. 'app=sample-api'",
            },
        },
        "required": [],
    }

    def __init__(self, client: K8sClient):
        self.client = client

    async def execute(
        self, namespace: str = "devops-copilot", label_selector: Optional[str] = None
    ) -> str:
        params: dict[str, Any] = {}
        if label_selector:
            params["labelSelector"] = label_selector
        data = await self.client.get(
            f"/api/v1/namespaces/{namespace}/pods", params=params
        )
        items = data.get("items", [])
        rows = []
        for p in items:
            status = p.get("status", {})
            phase = status.get("phase", "Unknown")
            container_states = status.get("containerStatuses", [])
            ready = sum(1 for c in container_states if c.get("ready"))
            total = len(container_states)
            restarts = sum(c.get("restartCount", 0) for c in container_states)
            rows.append(
                {
                    "name": p["metadata"]["name"],
                    "phase": phase,
                    "ready": f"{ready}/{total}",
                    "restarts": restarts,
                    "node": p.get("spec", {}).get("nodeName", "—"),
                    "age": p["metadata"].get("creationTimestamp", "—"),
                }
            )
        return json.dumps(
            {"namespace": namespace, "count": len(rows), "pods": rows}, indent=2
        )


class K8sGetPodLogs(Tool):
    name = "k8s_get_pod_logs"
    description = "Fetch the last N lines of logs from a specific pod (optionally a specific container)."
    parameters = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "default": "devops-copilot"},
            "pod": {"type": "string", "description": "Pod name"},
            "container": {"type": "string", "description": "Container name (optional)"},
            "tail_lines": {
                "type": "integer",
                "default": 100,
                "minimum": 1,
                "maximum": 5000,
            },
            "previous": {
                "type": "boolean",
                "default": False,
                "description": "Get logs from previous container instance",
            },
        },
        "required": ["pod"],
    }

    def __init__(self, client: K8sClient):
        self.client = client

    async def execute(
        self,
        pod: str,
        namespace: str = "devops-copilot",
        container: Optional[str] = None,
        tail_lines: int = 100,
        previous: bool = False,
    ) -> str:
        params: dict[str, Any] = {"tailLines": tail_lines}
        if container:
            params["container"] = container
        if previous:
            params["previous"] = "true"
        data = await self.client.get(
            f"/api/v1/namespaces/{namespace}/pods/{pod}/log", params=params
        )
        return data if isinstance(data, str) else json.dumps(data)


class K8sDescribePod(Tool):
    name = "k8s_describe_pod"
    description = "Describe a pod: status, conditions, container states, recent events. Use this to diagnose crash-looping, pending, or failing pods."
    parameters = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "default": "devops-copilot"},
            "pod": {"type": "string"},
        },
        "required": ["pod"],
    }

    def __init__(self, client: K8sClient):
        self.client = client

    async def execute(self, pod: str, namespace: str = "devops-copilot") -> str:
        pod_data, events = await asyncio.gather(
            self.client.get(f"/api/v1/namespaces/{namespace}/pods/{pod}"),
            self.client.get(
                f"/api/v1/namespaces/{namespace}/events",
                params={"fieldSelector": f"involvedObject.name={pod}"},
            ),
        )
        status = pod_data.get("status", {})
        result = {
            "name": pod_data["metadata"]["name"],
            "namespace": pod_data["metadata"]["namespace"],
            "node": pod_data.get("spec", {}).get("nodeName"),
            "phase": status.get("phase"),
            "pod_ip": status.get("podIP"),
            "conditions": status.get("conditions", []),
            "container_statuses": [
                {
                    "name": cs.get("name"),
                    "ready": cs.get("ready"),
                    "restart_count": cs.get("restartCount"),
                    "image": cs.get("image"),
                    "state": cs.get("state"),
                    "last_state": cs.get("lastState"),
                }
                for cs in status.get("containerStatuses", [])
            ],
            "events": [
                {
                    "type": e.get("type"),
                    "reason": e.get("reason"),
                    "message": e.get("message"),
                    "count": e.get("count"),
                    "last_timestamp": e.get("lastTimestamp") or e.get("eventTime"),
                }
                for e in (events.get("items", []) or [])[-10:]
            ],
        }
        return json.dumps(result, indent=2, default=str)


class K8sListDeployments(Tool):
    name = "k8s_list_deployments"
    description = "List deployments in a namespace with replica status."
    parameters = {
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "default": "devops-copilot"},
        },
        "required": [],
    }

    def __init__(self, client: K8sClient):
        self.client = client

    async def execute(self, namespace: str = "devops-copilot") -> str:
        data = await self.client.get(
            f"/apis/apps/v1/namespaces/{namespace}/deployments"
        )
        rows = []
        for d in data.get("items", []):
            spec = d.get("spec", {})
            status = d.get("status", {})
            rows.append(
                {
                    "name": d["metadata"]["name"],
                    "replicas_desired": spec.get("replicas"),
                    "replicas_ready": status.get("readyReplicas"),
                    "replicas_available": status.get("availableReplicas"),
                    "image": spec.get("template", {})
                    .get("spec", {})
                    .get("containers", [{}])[0]
                    .get("image"),
                }
            )
        return json.dumps(
            {"namespace": namespace, "count": len(rows), "deployments": rows}, indent=2
        )


def build_k8s_tools(k8s_api_url: Optional[str] = None) -> tuple[list[Tool], K8sClient]:
    client = K8sClient(api_url=k8s_api_url)
    tools: list[Tool] = [
        K8sListPods(client),
        K8sGetPodLogs(client),
        K8sDescribePod(client),
        K8sListDeployments(client),
    ]
    return tools, client
