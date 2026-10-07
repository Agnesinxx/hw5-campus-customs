"""PydanticAI agent team for grounded Campus Customs ticket analysis."""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

try:  # Supports importing as `backend.team` and running from the backend directory.
    from .audit import append_audit_event
except ImportError:  # pragma: no cover - exercised by the assignment's launch command.
    from audit import append_audit_event


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "backend" / "prompts"
MCP_SERVER_PATH = BASE_DIR / "mcp_server" / "server.py"
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
AGENT_MODEL_SETTINGS = {"openai_reasoning_effort": "none"}
USAGE_LIMITS = UsageLimits(request_limit=12, tool_calls_limit=20, total_tokens_limit=8000)
MAX_DELEGATION_DEPTH = 3

# A cloned project uses hw5/.env. The parent fallback preserves this workspace's
# existing local key without overriding a project-specific value.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parents[1] / ".env")


@dataclass
class TeamDependencies:
    """Run-scoped controls shared by all five agents."""

    delegation_depth: int = 0


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY must be set before running the Campus Customs agents.")
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key),
    )


def _mcp_toolset() -> MCPToolset:
    """Create a fresh stdio MCP connection; the backend never opens SQLite directly."""
    return MCPToolset(MCP_SERVER_PATH)


class CampusCustomsTeam:
    """Five delegating agents grounded exclusively by the local MCP server."""

    def __init__(self) -> None:
        self.agents: dict[str, Agent[TeamDependencies, str]] = {
            "Boss": Agent(_model(), name="Boss", instructions=_load_prompt("boss"), deps_type=TeamDependencies, toolsets=[_mcp_toolset()], model_settings=AGENT_MODEL_SETTINGS),
            "Inventory": Agent(_model(), name="Inventory", instructions=_load_prompt("inventory"), deps_type=TeamDependencies, toolsets=[_mcp_toolset()], model_settings=AGENT_MODEL_SETTINGS),
            "Accounting": Agent(_model(), name="Accounting", instructions=_load_prompt("accounting"), deps_type=TeamDependencies, toolsets=[_mcp_toolset()], model_settings=AGENT_MODEL_SETTINGS),
            "Facilities": Agent(_model(), name="Facilities", instructions=_load_prompt("facilities"), deps_type=TeamDependencies, toolsets=[_mcp_toolset()], model_settings=AGENT_MODEL_SETTINGS),
            "Customer Service": Agent(_model(), name="Customer Service", instructions=_load_prompt("customer_service"), deps_type=TeamDependencies, toolsets=[_mcp_toolset()], model_settings=AGENT_MODEL_SETTINGS),
        }
        self._register_delegations()

    def _register_delegations(self) -> None:
        """Give every agent a direct delegation tool for each other team member."""
        for source in self.agents:
            for target in self.agents:
                if source != target:
                    self._add_delegate_tool(source, target)

    def _add_delegate_tool(self, source: str, target: str) -> None:
        tool_name = f"delegate_to_{target.lower().replace(' ', '_')}"

        @self.agents[source].tool(name=tool_name)
        async def delegate(ctx: RunContext[TeamDependencies], task: str) -> str:
            """Delegate a focused ticket task to the named specialist."""
            if ctx.deps.delegation_depth >= MAX_DELEGATION_DEPTH:
                return "Delegation depth limit reached; state the remaining recommendation without further delegation."
            append_audit_event(
                agent=source,
                action="delegation",
                detail=task,
                delegation_to=target,
            )
            return await self._run_agent(target, task, ctx.deps.delegation_depth + 1)

    async def _run_agent(self, agent_name: str, task: str, depth: int = 0) -> str:
        append_audit_event(agent=agent_name, action="analysis", detail=task)
        result = await self.agents[agent_name].run(
            task,
            deps=TeamDependencies(delegation_depth=depth),
            usage_limits=USAGE_LIMITS,
        )
        for message in result.all_messages():
            for part in getattr(message, "parts", []):
                if isinstance(part, ToolCallPart):
                    append_audit_event(
                        agent=agent_name,
                        action="tool_call",
                        detail="Model requested a tool.",
                        mcp_tool=part.tool_name,
                    )
        append_audit_event(agent=agent_name, action="result", detail=result.output)
        return result.output

    async def run_ticket(self, ticket_id: int) -> str:
        """Have the Boss begin a grounded analysis of one ticket."""
        task = (
            f"Analyze ticket {ticket_id}. First use get_ticket. Use MCP tools for every shop fact. "
            "Delegate to specialists when their expertise is needed. Return a recommendation only; "
            "do not approve payments, change records, or contact anyone."
        )
        return await self._run_agent("Boss", task)


def run_ticket_sync(ticket_id: int) -> str:
    """Convenience entry point for later route integration."""
    return asyncio.run(CampusCustomsTeam().run_ticket(ticket_id))
