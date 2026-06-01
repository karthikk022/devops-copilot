"""Tests for the tool registry and OpenAI function-calling schema generation."""
import json
import pytest

from app.tools.base import Tool, ToolRegistry, truncate


class EchoTool(Tool):
    name = "echo"
    description = "Returns whatever you pass in."
    parameters = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    async def execute(self, **kwargs):
        return f"echo: {kwargs.get('message', '')}"


class FailingTool(Tool):
    name = "failing_tool"
    description = "Always raises an exception."
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        raise RuntimeError("intentional failure")


def test_tool_schema_is_openai_function_format():
    schema = EchoTool().schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"
    assert schema["function"]["description"] == "Returns whatever you pass in."
    assert schema["function"]["parameters"]["type"] == "object"
    assert "message" in schema["function"]["parameters"]["properties"]


def test_registry_register_and_contains():
    reg = ToolRegistry()
    assert "echo" not in reg
    reg.register(EchoTool())
    assert "echo" in reg
    assert "missing" not in reg


def test_registry_rejects_duplicate_registration():
    reg = ToolRegistry()
    reg.register(EchoTool())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(EchoTool())


def test_registry_schemas_returns_list_of_valid_schemas():
    reg = ToolRegistry()
    reg.register(EchoTool())
    reg.register(FailingTool())
    schemas = reg.schemas()
    assert len(schemas) == 2
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]
    # Must be JSON-serializable (OpenAI SDK requires this)
    json.dumps(schemas)


@pytest.mark.asyncio
async def test_registry_call_invokes_correct_tool():
    reg = ToolRegistry()
    reg.register(EchoTool())
    result = await reg.call("echo", {"message": "hello"})
    assert result == "echo: hello"


@pytest.mark.asyncio
async def test_registry_call_unknown_tool_returns_error_json():
    reg = ToolRegistry()
    result = await reg.call("nope", {})
    parsed = json.loads(result)
    assert "error" in parsed
    assert "Unknown tool" in parsed["error"]


@pytest.mark.asyncio
async def test_registry_call_handles_tool_exception():
    reg = ToolRegistry()
    reg.register(FailingTool())
    result = await reg.call("failing_tool", {})
    parsed = json.loads(result)
    assert parsed["tool"] == "failing_tool"
    assert "intentional failure" in parsed["error"]


def test_truncate_preserves_short_strings():
    assert truncate("short") == "short"


def test_truncate_chops_long_strings():
    long_text = "x" * 10000
    result = truncate(long_text, max_chars=100)
    assert len(result) > 100  # includes truncation marker
    assert "truncated" in result
    assert "9900 more chars" in result
