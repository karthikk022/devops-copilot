import logging
import os
from typing import Optional

from .base import ToolRegistry
from .k8s import K8sClient, build_k8s_tools
from .loki import build_loki_tools
from .prometheus import build_prom_tools

logger = logging.getLogger(__name__)


async def build_registry(
    prometheus_url: str,
    loki_url: str,
    k8s_api_url: Optional[str] = None,
) -> ToolRegistry:
    registry = ToolRegistry()

    k8s_tools, k8s_client = build_k8s_tools(k8s_api_url=k8s_api_url or os.getenv("K8S_API_URL"))
    for t in k8s_tools:
        registry.register(t)

    prom_tools, prom_client = build_prom_tools(prometheus_url)
    for t in prom_tools:
        registry.register(t)

    loki_tools, loki_client = build_loki_tools(loki_url)
    for t in loki_tools:
        registry.register(t)

    logger.info(
        "tool_registry_built",
        extra={"tools": [t.name for t in registry._tools.values()]},
    )
    return registry, (k8s_client, prom_client, loki_client)


async def shutdown_registry(registry: ToolRegistry, *clients) -> None:
    for c in clients:
        if c is not None:
            try:
                await c.close()
            except Exception:
                pass
