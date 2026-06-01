import json
import logging
import time
from typing import Any, Optional

import httpx

from .base import Tool

logger = logging.getLogger(__name__)


class LokiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(20.0, connect=5.0))
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def query_range(self, query: str, start: int, end: int, limit: int = 200) -> dict:
        client = await self._ensure()
        r = await client.get(
            "/loki/api/v1/query_range",
            params={"query": query, "start": start, "end": end, "limit": limit},
        )
        r.raise_for_status()
        return r.json()


class LokiQuery(Tool):
    name = "loki_query"
    description = (
        "Run a LogQL query against Loki and return log lines from the last N minutes. "
        "Use this to search logs by label selector and/or text filter. "
        "Examples: {namespace=\"devops-copilot\",app=\"sample-api\"} |= \"error\" |~ \"(?i)memory leak|database\""
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "LogQL query string"},
            "minutes": {"type": "integer", "default": 15, "minimum": 1, "maximum": 1440},
            "limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 1000},
        },
        "required": ["query"],
    }

    def __init__(self, client: LokiClient):
        self.client = client

    async def execute(self, query: str, minutes: int = 15, limit: int = 100) -> str:
        end = int(time.time() * 1e9)
        start = end - minutes * 60 * 1_000_000_000
        try:
            data = await self.client.query_range(query, start=start, end=end, limit=limit)
        except httpx.HTTPStatusError as e:
            body = e.response.text[:1500] if e.response else str(e)
            return json.dumps({"error": f"Loki returned {e.response.status_code}", "body": body})
        except Exception as e:
            return json.dumps({"error": str(e)})

        streams = data.get("data", {}).get("result", [])
        lines: list[dict] = []
        for stream in streams:
            labels = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                lines.append({"ts": ts, "labels": labels, "line": line})

        if not lines:
            return json.dumps({"query": query, "range_minutes": minutes, "result": "no matching logs"})

        text_lines = []
        for ln in lines[:limit]:
            ts = ln["ts"]
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(int(ts) / 1e9).strftime("%H:%M:%S")
            except Exception:
                dt = str(ts)
            text_lines.append(f"[{dt}] {ln['line']}")

        return json.dumps({
            "query": query,
            "range_minutes": minutes,
            "stream_count": len(streams),
            "line_count": len(lines),
            "logs": "\n".join(text_lines),
        }, indent=2)


def build_loki_tools(base_url: str) -> tuple[list[Tool], LokiClient]:
    client = LokiClient(base_url)
    return [LokiQuery(client)], client
