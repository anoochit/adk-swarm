"""
Main entry point and runnable demonstration of ADK Swarm.
Demonstrates:
1. Loading pre-defined agents from swarm_config.yaml.
2. Spawning a dynamic agent at runtime with permanent YAML persistence.
3. Reloading from config to verify persistence.
"""
import asyncio
from swarm_registry import SwarmRegistry
from swarm_tools import create_swarm_tools

# Sample domain tool
def dummy_web_search(query: str) -> dict:
    """Mock web search tool for research agents."""
    return {
        "status": "success",
        "query": query,
        "results": [
            {"title": f"Recent insights on {query}", "snippet": f"Detailed technical breakdown regarding {query}."}
        ]
    }

def build_swarm(config_path: str = "swarm_config.yaml") -> SwarmRegistry:
    registry = SwarmRegistry()
    registry.register_tool("dummy_web_search", dummy_web_search)

    swarm_tools = create_swarm_tools(registry)
    for tool_fn in swarm_tools:
        registry.register_tool(tool_fn.__name__, tool_fn)

    registry.load_from_config(config_path)
    return registry

async def main():
    print("=== Initializing ADK Swarm ===")
    registry = build_swarm("swarm_config.yaml")

    print("\nInitial Roster of Swarm Agents:")
    for a in registry.list_agents():
        print(f" - [{a['name']}] Role: {a['role']} | Root: {a['is_root']} | Tools: {a['tools']}")

    print("\n=== Spawning Dynamic Agent (Persisted=True) ===")
    test_agent_name = "security_auditor"
    if test_agent_name not in registry.agents:
        new_agent = registry.spawn_runtime_agent(
            name=test_agent_name,
            role="Application Security Auditor",
            instruction="Audit code and configurations for CVEs, injection, and security vulnerabilities.",
            tool_names=["dummy_web_search", "save_file_as_artifact"],
            persist=True
        )
        print(f"Spawned & Persisted: {new_agent.name} (Description: {new_agent.description})")
    else:
        print(f"Agent '{test_agent_name}' already exists in config.")

    print("\n=== Verifying Reload from swarm_config.yaml ===")
    fresh_registry = build_swarm("swarm_config.yaml")
    print(f"Total agents in fresh registry: {len(fresh_registry.agents)}")
    assert test_agent_name in fresh_registry.agents, f"{test_agent_name} should be persisted!"
    print(f"SUCCESS: '{test_agent_name}' was permanently loaded from swarm_config.yaml!")

if __name__ == "__main__":
    asyncio.run(main())
