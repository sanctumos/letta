"""Unit and integration coverage for the Sanctum API fixes on venice-openai-proxy."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pydantic import ValidationError

from letta.errors import ConcurrentUpdateError
from letta.functions.mcp_client.types import MCPTool, MCPToolHealth
from letta.orm.tool import Tool as ToolModel
from letta.orm.tool import list_all_for_organization
from letta.schemas.block import CreateBlock
from letta.schemas.enums import MessageRole
from letta.schemas.message import Message, ToolReturn
from letta.schemas.providers.openai import OpenAIProvider
from letta.schemas.tool_execution_result import ToolExecutionResult
from letta.schemas.user import User
from letta.server.rest_api.routers.v1.agents import (
    attach_block_to_agent,
    detach_block_from_agent,
    modify_block_for_agent,
    retrieve_block_for_agent,
)
from letta.server.rest_api.routers.v1.internal_agents import modify_block_for_agent as internal_modify_block
from letta.server.rest_api.utils import (
    create_letta_messages_from_llm_response,
    create_parallel_tool_messages_from_llm_response,
)
from letta.services.mcp_manager import MCPManager
from letta.services.mcp_server_manager import MCPServerManager


def test_create_block_rejects_slash_and_accepts_plain_label():
    try:
        CreateBlock(label="songs/fourth_of_july", value="x")
        raise AssertionError("slash label should be rejected")
    except ValidationError as exc:
        assert "slash" in str(exc).lower()
    block = CreateBlock(label="persona", value="hello")
    assert block.label == "persona"


def test_venice_embedding_models_omit_ada_002():
    async def run():
        venice = OpenAIProvider(name="venice", base_url="https://api.venice.ai/api/v1")
        openai = OpenAIProvider(name="openai", base_url="https://api.openai.com/v1")
        venice_models = await venice.list_embedding_models_async()
        openai_models = await openai.list_embedding_models_async()
        assert [model.embedding_model for model in venice_models] == [
            "text-embedding-3-small",
            "text-embedding-3-large",
        ]
        assert [model.embedding_dim for model in venice_models] == [1536, 3072]
        assert all("venice.ai" in model.embedding_endpoint for model in venice_models)
        openai_names = [model.embedding_model for model in openai_models]
        assert "text-embedding-ada-002" in openai_names
        assert "text-embedding-ada-002" not in [model.embedding_model for model in venice_models]

    asyncio.run(run())


def test_tool_result_sets_anthropic_is_error():
    failed = Message(
        role=MessageRole.tool,
        tool_call_id="call-1",
        is_err=True,
        tool_returns=[ToolReturn(tool_call_id="call-1", status="error", func_response='{"status":"Failed"}')],
    )
    ok = Message(
        role=MessageRole.tool,
        tool_call_id="call-2",
        is_err=False,
        tool_returns=[ToolReturn(tool_call_id="call-2", status="success", func_response='{"status":"OK"}')],
    )
    failed_content = failed.to_anthropic_dict("claude")["content"][0]
    ok_content = ok.to_anthropic_dict("claude")["content"][0]
    assert failed_content["is_error"] is True
    assert "is_error" not in ok_content


def test_llm_response_helpers_flag_failed_tools():
    failed = ToolExecutionResult(status="error", func_return="nope", stdout=[], stderr=[])
    success = ToolExecutionResult(status="success", func_return="ok", stdout=[], stderr=[])
    messages = create_letta_messages_from_llm_response(
        agent_id="agent-1",
        model="openai-proxy/test",
        function_name="lookup",
        function_arguments={},
        tool_execution_result=failed,
        tool_call_id="call-err",
        function_response='{"status":"Failed"}',
        timezone="UTC",
        force_set_request_heartbeat=False,
        add_heartbeat_on_continue=False,
    )
    tool_messages = [message for message in messages if message.role == MessageRole.tool]
    assert tool_messages and tool_messages[0].is_err is True

    parallel = create_parallel_tool_messages_from_llm_response(
        agent_id="agent-1",
        model="openai-proxy/test",
        tool_call_specs=[
            {"name": "a", "arguments": {}, "id": "c1"},
            {"name": "b", "arguments": {}, "id": "c2"},
        ],
        tool_execution_results=[success, failed],
        function_responses=['{"status":"OK"}', '{"status":"Failed"}'],
        timezone="UTC",
        tool_returns=[],
    )
    parallel_tool = [message for message in parallel if message.role == MessageRole.tool]
    assert parallel_tool and parallel_tool[0].is_err is True


def test_list_all_for_organization_empty_page_stops():
    async def fake_list(cls, db_session, organization_id, limit, ascending, after=None, **kwargs):
        return []

    async def run():
        original = ToolModel.list_async
        ToolModel.list_async = classmethod(fake_list)
        try:
            rows = await list_all_for_organization(db_session=object(), organization_id="org-1", page_size=2)
        finally:
            ToolModel.list_async = original
        assert rows == []

    asyncio.run(run())


def test_list_all_for_organization_pages_until_short_page():
    pages = {
        None: [SimpleNamespace(id="a"), SimpleNamespace(id="b")],
        "b": [SimpleNamespace(id="c")],
    }

    async def fake_list(cls, db_session, organization_id, limit, ascending, after=None, **kwargs):
        assert organization_id == "org-1"
        assert ascending is True
        assert limit == 2
        return pages.get(after, [])

    async def run():
        original = ToolModel.list_async
        ToolModel.list_async = classmethod(fake_list)
        try:
            rows = await list_all_for_organization(db_session=object(), organization_id="org-1", page_size=2)
        finally:
            ToolModel.list_async = original
        assert [row.id for row in rows] == ["a", "b", "c"]

    asyncio.run(run())


def test_list_all_for_organization_stops_on_repeated_cursor():
    calls = {"n": 0}

    async def fake_list(cls, db_session, organization_id, limit, ascending, after=None, **kwargs):
        calls["n"] += 1
        if calls["n"] > 2:
            raise AssertionError("paging did not stop when the cursor repeated")
        return [SimpleNamespace(id="same"), SimpleNamespace(id="same")]

    async def run():
        original = ToolModel.list_async
        ToolModel.list_async = classmethod(fake_list)
        try:
            rows = await list_all_for_organization(db_session=object(), organization_id="org-1", page_size=2)
        finally:
            ToolModel.list_async = original
        assert calls["n"] == 2
        assert [row.id for row in rows] == ["same", "same", "same", "same"]

    asyncio.run(run())


def test_concurrent_update_handler_logs_warning_and_returns_409():
    async def run():
        from letta.server.rest_api.app import create_application

        app = create_application()
        handler = app.exception_handlers[ConcurrentUpdateError]
        response = await handler(MagicMock(), ConcurrentUpdateError("Block", "block-1"))
        body = json.loads(response.body)
        assert response.status_code == 409
        assert body["error_code"] == "CONCURRENT_UPDATE"
        assert "block-1" in body["detail"]

        plain = ConcurrentUpdateError("Block", "block-2")
        plain.details = "not-a-dict"
        fallback = await handler(MagicMock(), plain)
        fallback_body = json.loads(fallback.body)
        assert fallback.status_code == 409
        assert "error_code" not in fallback_body
        assert "block-2" in fallback_body["detail"]

    asyncio.run(run())


def test_block_label_routes_unquote_before_lookup():
    async def run():
        headers = SimpleNamespace(actor_id="user-1")
        server = MagicMock()
        server.user_manager.get_actor_or_default_async = AsyncMock(return_value=SimpleNamespace(id="user-1"))
        server.agent_manager.get_block_with_label_async = AsyncMock(return_value={"label": "songs/fourth_of_july"})
        server.agent_manager.modify_block_by_label_async = AsyncMock(return_value={"label": "songs/fourth_of_july"})
        server.agent_manager.rebuild_system_prompt_async = AsyncMock()
        server.agent_manager.attach_block_async = AsyncMock(return_value={"id": "agent-1"})
        server.agent_manager.detach_block_async = AsyncMock(return_value={"id": "agent-1"})

        await retrieve_block_for_agent(
            block_label="songs%2Ffourth_of_july",
            agent_id="agent-1",
            server=server,
            headers=headers,
        )
        await modify_block_for_agent(
            block_label="songs%2Ffourth_of_july",
            agent_id="agent-1",
            block_update=SimpleNamespace(),
            server=server,
            headers=headers,
        )
        await internal_modify_block(
            block_label="songs%2Ffourth_of_july",
            agent_id="agent-1",
            block_update=SimpleNamespace(),
            server=server,
            headers=headers,
        )
        await attach_block_to_agent(block_id="block-1", agent_id="agent-1", server=server, headers=headers)
        await detach_block_from_agent(block_id="block-1", agent_id="agent-1", server=server, headers=headers)

        looked_up = [
            call.kwargs["block_label"]
            for call in server.agent_manager.get_block_with_label_async.await_args_list
            + server.agent_manager.modify_block_by_label_async.await_args_list
        ]
        assert looked_up == ["songs/fourth_of_july", "songs/fourth_of_july", "songs/fourth_of_july"]

    asyncio.run(run())


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_resync_pages_tools_and_reports_skipped():
    actor = User(name="qc", organization_id="org-1")
    valid = MCPTool(
        name="lookup",
        description="look",
        inputSchema={"type": "object", "properties": {}},
        health=MCPToolHealth(status="STRICT_COMPLIANT", reasons=[]),
    )
    fresh = MCPTool(
        name="fresh",
        description="new",
        inputSchema={"type": "object", "properties": {}},
        health=MCPToolHealth(status="STRICT_COMPLIANT", reasons=[]),
    )
    broken = MCPTool(
        name="broken",
        description="bad",
        inputSchema={},
        health=MCPToolHealth(status="INVALID", reasons=["schema empty"]),
    )
    healed = MCPTool(
        name="healed",
        description="recovered",
        inputSchema={"heal": True},
        health=MCPToolHealth(status="INVALID", reasons=["was bad"]),
    )
    meta = {"mcp": {"server_id": "mcp-server-1"}}
    stale = SimpleNamespace(
        id="tool-stale",
        name="stale",
        metadata_=meta,
        json_schema={"name": "stale"},
        hard_delete_async=AsyncMock(),
    )
    existing = SimpleNamespace(
        id="tool-lookup",
        name="lookup",
        metadata_=meta,
        json_schema={"name": "lookup"},
        hard_delete_async=AsyncMock(),
    )

    async def run(manager_cls):
        manager = manager_cls()
        manager.get_mcp_server_by_id_async = AsyncMock(return_value=SimpleNamespace(server_name="demo"))
        manager.get_mcp_server_id_by_name = AsyncMock(return_value="mcp-server-1")
        manager.list_mcp_server_tools = AsyncMock(return_value=[valid, fresh, broken, healed])
        manager.tool_manager.update_tool_by_id_async = AsyncMock()
        manager.tool_manager.create_mcp_tool_async = AsyncMock(return_value=SimpleNamespace(id="tool-new"))
        manager.create_mcp_tool_mapping = AsyncMock()

        async def fake_list_all(db_session, organization_id, page_size=200):
            assert organization_id == "org-1"
            return [stale, existing]

        from letta.services import mcp_manager as mcp_manager_mod
        from letta.services import mcp_server_manager as mcp_server_manager_mod

        module = mcp_server_manager_mod if manager_cls is MCPServerManager else mcp_manager_mod

        def explode(schema):
            if schema == {"heal": True}:
                return {"type": "object", "properties": {}}
            raise RuntimeError("normalize failed")

        original_list = module.list_all_for_organization
        original_session = module.db_registry.async_session
        original_normalize = module.normalize_mcp_schema
        module.list_all_for_organization = fake_list_all
        module.db_registry.async_session = lambda: _Session()
        module.normalize_mcp_schema = explode
        try:
            result = await manager.resync_mcp_server_tools("mcp-server-1", actor)
        finally:
            module.list_all_for_organization = original_list
            module.db_registry.async_session = original_session
            module.normalize_mcp_schema = original_normalize

        assert [item.name for item in result.skipped] == ["broken"]
        assert result.skipped[0].reasons == ["schema empty"]
        assert "stale" in result.deleted
        assert "fresh" in result.added
        assert "healed" in result.added

    asyncio.run(run(MCPServerManager))
    asyncio.run(run(MCPManager))
