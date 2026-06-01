import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List


logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 6000


class Tool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    requires_confirmation: bool = False
    dangerous: bool = False

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str: ...

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def truncate(text: str, max_chars: int = MAX_RESULT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n... [truncated, {len(text) - max_chars} more chars]"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} already registered")
        self._tools[tool.name] = tool
        logger.info("tool_registered", extra={"name": tool.name})

    def schemas(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    async def call(self, name: str, arguments: Dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            logger.info("tool_invocation", extra={"name": name, "args": arguments})
            result = await tool.execute(**arguments)
            return truncate(
                result
                if isinstance(result, str)
                else json.dumps(result, indent=2, default=str)
            )
        except Exception as e:
            logger.exception("tool_execution_failed", extra={"name": name})
            return json.dumps({"error": str(e), "tool": name})

    def __contains__(self, name: str) -> bool:
        return name in self._tools
