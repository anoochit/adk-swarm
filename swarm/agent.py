"""
ADK Agent entry point for `adk run` and `adk web`.
Exports `root_agent` and `app` discovered automatically by the ADK CLI.
"""
from pathlib import Path

from google.adk.apps import App
from google.adk.tools import google_search

from swarm_registry import SwarmRegistry
from swarm_tools import create_swarm_tools, get_current_datetime, get_weather_forecast


def dummy_web_search(query: str) -> dict:
    """Mock web search tool for research agents (fallback)."""
    return {
        "status": "success",
        "query": query,
        "results": [
            {"title": f"Insights on {query}", "snippet": f"Technical breakdown regarding {query}."}
        ],
    }


def _build() -> App:
    registry = SwarmRegistry()
    registry.register_tool("google_search", google_search)
    registry.register_tool("dummy_web_search", dummy_web_search)
    registry.register_tool("get_weather_forecast", get_weather_forecast)
    registry.register_tool("get_current_datetime", get_current_datetime)

    for fn in create_swarm_tools(registry):
        registry.register_tool(fn.__name__, fn)

    # Resolve swarm_config.yaml from project root (parent of swarm/)
    config = Path(__file__).parent.parent / "swarm_config.yaml"
    registry.load_from_config(str(config))

    return App(name="swarm", root_agent=registry.agents[registry.root_agent_name])


# Global instances discovered by ADK CLI (adk run / adk web / adk api_server)
app = _build()
root_agent = app.root_agent
