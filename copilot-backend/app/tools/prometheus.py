import json
import logging
from typing import Any, Optional

import httpx

from .base import Tool

logger = logging.getLogger(__name__)


class PromClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(15.0, connect=5.0))
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def query(self, query: str) -> dict:
        client = await self._ensure()
        r = await client.get("/api/v1/query", params={"query": query})
        r.raise_for_status()
        return r.json()

    async def query_range(self, query: str, start: int, end: int, step: int = 30) -> dict:
        client = await self._ensure()
        r = await client.get(
            "/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "step": step},
        )
        r.raise_for_status()
        return r.json()


class PromQuery(Tool):
    name = "prom_query"
    description = (
        "Run an instant PromQL query against Prometheus and return the current value. "
        "Use this for current-state questions: error rate right now, current memory, "
        "current pod count, current request rate. For historical/time-series use prom_query_range."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "PromQL expression, e.g. 'sum(rate(http_requests_total{app=\"sample-api\"}[5m]))'"},
        },
        "required": ["query"],
    }

    def __init__(self, client: PromClient):
        self.client = client

    async def execute(self, query: str) -> str:
        try:
            data = await self.client.query(query)
        except httpx.HTTPStatusError as e:
            body = e.response.text[:1500] if e.response else str(e)
            return json.dumps({"error": f"Prometheus returned {e.response.status_code}", "body": body})
        except Exception as e:
            return json.dumps({"error": str(e)})

        result_type = data.get("data", {}).get("resultType", "—")
        results = data.get("data", {}).get("result", [])
        if not results:
            return json.dumps({"query": query, "resultType": result_type, "result": "no data (empty series)"})

        compact = []
        for r in results[:20]:
            metric = r.get("metric", {})
            value = r.get("value", [None, "0"])
            compact.append({
                "labels": {k: v for k, v in metric.items() if not k.startswith("__")},
                "value": value[1] if len(value) > 1 else value[0],
                "timestamp": value[0] if len(value) > 0 else None,
            })

        return json.dumps({
            "query": query,
            "resultType": result_type,
            "result_count": len(results),
            "result": compact,
        }, indent=2)


class PromQueryRange(Tool):
    name = "prom_query_range"
    description = (
        "Run a range PromQL query over a time window. Returns time-series data. "
        "Use this for trend analysis, latency over time, error rate over time."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "minutes": {"type": "integer", "default": 30, "minimum": 1, "maximum": 1440},
            "step_seconds": {"type": "integer", "default": 30, "minimum": 5, "maximum": 600},
        },
        "required": ["query"],
    }

    def __init__(self, client: PromClient):
        self.client = client

    async def execute(self, query: str, minutes: int = 30, step_seconds: int = 30) -> str:
        import time
        end = int(time.time())
        start = end - minutes * 60
        try:
            data = await self.client.query_range(query, start=start, end=end, step=step_seconds)
        except Exception as e:
            return json.dumps({"error": str(e)})

        results = data.get("data", {}).get("result", [])
        compact = []
        for r in results[:10]:
            metric = r.get("metric", {})
            values = r.get("values", [])
            if values:
                compact.append({
                    "labels": {k: v for k, v in metric.items() if not k.startswith("__")},
                    "points": len(values),
                    "first": values[0],
                    "last": values[-1],
                })

        return json.dumps({
            "query": query,
            "range_minutes": minutes,
            "step_seconds": step_seconds,
            "series_count": len(results),
            "result": compact,
        }, indent=2)


def build_prom_tools(base_url: str) -> tuple[list[Tool], PromClient]:
    client = PromClient(base_url)
    return [PromQuery(client), PromQueryRange(client)], client
