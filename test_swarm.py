import pytest
import yaml
from google.adk.runners import InMemoryRunner
from google.adk.artifacts import InMemoryArtifactService
from swarm_registry import SwarmRegistry
from swarm_tools import create_swarm_tools

@pytest.fixture
def sample_config(tmp_path):
    config_content = """
version: "1.0"
swarm:
  name: "test_swarm"
  default_model: "gemini-2.5-flash"

agents:
  - name: "coordinator"
    role: "Orchestrator"
    is_root: true
    instruction: "You coordinate agents."
    tools:
      - "spawn_agent"
      - "list_swarm_agents"
      - "save_file_as_artifact"
      - "load_file_artifact"
      - "list_session_artifacts"

  - name: "researcher"
    role: "Researcher"
    instruction: "You research topics."
    tools:
      - "test_tool"
      - "save_file_as_artifact"
"""
    config_file = tmp_path / "test_swarm.yaml"
    config_file.write_text(config_content, encoding="utf-8")
    return str(config_file)

def test_load_from_config(sample_config):
    registry = SwarmRegistry()
    registry.register_tool("test_tool", lambda x: x)
    tools = create_swarm_tools(registry)
    for t in tools:
        registry.register_tool(t.__name__, t)

    root_agent = registry.load_from_config(sample_config)

    assert root_agent is not None
    assert root_agent.name == "coordinator"
    assert registry.root_agent_name == "coordinator"
    assert len(registry.agents) == 2
    assert "researcher" in registry.agents
    assert len(root_agent.sub_agents) == 1
    assert root_agent.sub_agents[0].name == "researcher"

def test_spawn_runtime_agent_permanent_persistence(sample_config):
    registry = SwarmRegistry()
    tools = create_swarm_tools(registry)
    for t in tools:
        registry.register_tool(t.__name__, t)

    registry.load_from_config(sample_config)

    # 1. Spawn with persist=True
    new_agent = registry.spawn_runtime_agent(
        name="crypto_analyst",
        role="Crypto Market Analyst",
        instruction="Analyze cryptographic tokens and protocols.",
        tool_names=["save_file_as_artifact"],
        persist=True
    )
    assert new_agent.name == "crypto_analyst"

    # 2. Inspect YAML file on disk directly
    with open(sample_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    persisted_names = [a["name"] for a in data["agents"]]
    assert "crypto_analyst" in persisted_names

    # 3. Load a completely fresh registry from the modified YAML
    fresh_registry = SwarmRegistry()
    fresh_registry.register_tool("test_tool", lambda x: x)
    for t in tools:
        fresh_registry.register_tool(t.__name__, t)
    fresh_registry.load_from_config(sample_config)

    assert "crypto_analyst" in fresh_registry.agents
    loaded_crypto = fresh_registry.get_agent("crypto_analyst")
    assert loaded_crypto.description == "Crypto Market Analyst"

def test_spawn_runtime_agent_ephemeral(sample_config):
    registry = SwarmRegistry()
    tools = create_swarm_tools(registry)
    for t in tools:
        registry.register_tool(t.__name__, t)

    registry.load_from_config(sample_config)

    # Spawn with persist=False
    new_agent = registry.spawn_runtime_agent(
        name="ephemeral_agent",
        role="Temporary Specialist",
        instruction="One-time tasks.",
        persist=False
    )
    assert new_agent.name == "ephemeral_agent"

    # YAML should NOT contain ephemeral_agent
    with open(sample_config, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    names = [a["name"] for a in data["agents"]]
    assert "ephemeral_agent" not in names

@pytest.mark.asyncio
async def test_artifact_tools():
    from google.adk.tools import ToolContext
    from google.adk.events import EventActions
    from google.adk.sessions import Session
    from google.genai import types

    registry = SwarmRegistry()
    tools = {t.__name__: t for t in create_swarm_tools(registry)}
    save_tool = tools["save_file_as_artifact"]
    load_tool = tools["load_file_artifact"]
    list_tool = tools["list_session_artifacts"]

    artifact_service = InMemoryArtifactService()
    session = Session(id="test_session", app_name="test_app", user_id="test_user")

    # Mock InvocationContext for ToolContext
    class MockInvocationContext:
        def __init__(self, s, a):
            self.app_name = "test_app"
            self.user_id = "test_user"
            self.session = s
            self.artifact_service = a

    ctx = ToolContext(
        invocation_context=MockInvocationContext(session, artifact_service),
        event_actions=EventActions()
    )

    # Test saving artifact
    save_res = await save_tool(
        filename="report.txt",
        content="Hello Artifact World",
        mime_type="text/plain",
        tool_context=ctx
    )
    assert save_res["status"] == "success"
    assert save_res["filename"] == "report.txt"

    # Test listing artifacts
    list_res = await list_tool(tool_context=ctx)
    assert list_res["status"] == "success"
    assert "report.txt" in list_res["artifacts"]

    # Test loading artifact
    load_res = await load_tool(filename="report.txt", tool_context=ctx)
    assert load_res["status"] == "success"
    assert load_res["content"] == "Hello Artifact World"
