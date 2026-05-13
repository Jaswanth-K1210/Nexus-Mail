"""
Nexus Mail — Agent Registry

Dynamic agent registration, discovery, and dependency injection.
Manages agent lifecycle and provides tools/memory to agents.

Usage:
    registry = AgentRegistry()
    registry.register(TriageAgent)
    registry.inject_tools({"gmail": gmail_tool, "calendar": calendar_tool})
    registry.inject_memory(memory_store)

    agent = registry.get("triage_agent")
    result = await agent.run(state)
"""

from typing import Type, Any

from app.agents.base import BaseAgent

import structlog

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """
    Central registry for all agents in the system.

    Responsibilities:
    - Register agent classes
    - Create agent instances with dependency injection
    - Provide tools and memory to agents
    - Track agent availability and health
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._agent_classes: dict[str, Type[BaseAgent]] = {}
        self._tools: dict[str, Any] = {}
        self._memory: Any = None

    # ─── Registration ─────────────────────────────────────────────────────

    def register(self, agent_class: Type[BaseAgent]) -> None:
        """Register an agent class. Instantiates it and injects dependencies."""
        agent = agent_class()
        name = agent.name

        # Inject tools
        if self._tools:
            agent.register_tools(self._tools)

        # Inject memory
        if self._memory:
            agent.set_memory(self._memory)

        self._agents[name] = agent
        self._agent_classes[name] = agent_class
        logger.info("Agent registered", agent=name, description=agent.description)

    def register_all(self, agent_classes: list[Type[BaseAgent]]) -> None:
        """Register multiple agent classes at once."""
        for cls in agent_classes:
            self.register(cls)

    # ─── Dependency Injection ─────────────────────────────────────────────

    def inject_tools(self, tools: dict[str, Any]) -> None:
        """Inject tools into all registered agents."""
        self._tools.update(tools)
        for agent in self._agents.values():
            agent.register_tools(tools)
        logger.info("Tools injected into agents", tools=list(tools.keys()), agents=list(self._agents.keys()))

    def inject_memory(self, memory: Any) -> None:
        """Inject memory store into all registered agents."""
        self._memory = memory
        for agent in self._agents.values():
            agent.set_memory(memory)
        logger.info("Memory injected into agents", agents=list(self._agents.keys()))

    # ─── Retrieval ────────────────────────────────────────────────────────

    def get(self, name: str) -> BaseAgent:
        """Get a registered agent by name."""
        agent = self._agents.get(name)
        if not agent:
            available = list(self._agents.keys())
            raise ValueError(f"Agent '{name}' not registered. Available: {available}")
        return agent

    def get_all(self) -> dict[str, BaseAgent]:
        """Get all registered agents."""
        return dict(self._agents)

    def list_agents(self) -> list[dict]:
        """List all registered agents with their metadata."""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "max_retries": agent.max_retries,
                "tools": list(agent._tools.keys()),
                "has_memory": agent._memory is not None,
            }
            for agent in self._agents.values()
        ]

    @property
    def agent_names(self) -> list[str]:
        """Get names of all registered agents."""
        return list(self._agents.keys())


# ─── Singleton Registry ──────────────────────────────────────────────────────

_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get or create the global agent registry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
