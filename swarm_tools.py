"""
Tools for runtime swarm orchestration and artifact file handling:
- spawn_agent: Create and register a new agent at runtime (with optional permanent YAML persistence)
- list_swarm_agents: Query the current active swarm roster
- delegate_to_agent: Directly dispatch subtasks to any agent in the swarm
- save_file_as_artifact: Save content/files as versioned session artifacts
- load_file_artifact: Load an existing artifact from the session
- list_session_artifacts: List all artifacts stored in the current session
"""
from collections.abc import Callable
from typing import Any

from google.adk.runners import InMemoryRunner
from google.adk.tools import ToolContext
from google.genai import types as genai_types

from swarm_registry import SwarmRegistry


def create_swarm_tools(registry: SwarmRegistry) -> list[Callable]:
    """Factory to create swarm management and artifact tools bound to a SwarmRegistry instance."""

    def spawn_agent(
        name: str,
        role: str,
        instruction: str,
        tool_names: list[str] | None = None,
        persist: bool = True,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Creates a new specialist agent in the swarm dynamically at runtime.

        Args:
            name: Unique identifier for the agent (lowercase, e.g. 'security_auditor').
            role: Brief description of the agent's role and purpose.
            instruction: Detailed system instruction defining behaviors and expertise.
            tool_names: List of tool names from the catalog to equip this agent with.
            persist: If True, writes this agent config permanently to swarm_config.yaml.
        """
        try:
            agent = registry.spawn_runtime_agent(
                name=name,
                role=role,
                instruction=instruction,
                tool_names=tool_names or [],
                persist=persist,
            )
            # Update shared session state if context is present
            if tool_context and tool_context.session:
                workers = tool_context.session.state.get("swarm:workers", [])
                workers.append({"name": name, "role": role, "persisted": persist})
                tool_context.session.state["swarm:workers"] = workers

            return {
                "status": "success",
                "message": f"Successfully spawned agent '{name}' (persisted={persist}).",
                "agent": {
                    "name": agent.name,
                    "role": agent.description,
                    "tools": [getattr(t, "name", getattr(t, "__name__", str(t))) for t in agent.tools],
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_swarm_agents(tool_context: ToolContext | None = None) -> dict[str, Any]:
        """Lists all agents currently available in the swarm along with their roles and tools."""
        return {
            "status": "success",
            "agents": registry.list_agents(),
        }

    async def delegate_to_agent(
        agent_name: str,
        task_prompt: str,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Dispatches a subtask to an existing swarm agent and returns its output.

        Args:
            agent_name: The name of the registered agent to execute the task.
            task_prompt: The detailed prompt/instructions for the task.
        """
        agent = registry.get_agent(agent_name)
        if not agent:
            return {
                "status": "error",
                "message": f"Agent '{agent_name}' not found. Available agents: {list(registry.agents.keys())}",
            }

        try:
            runner = InMemoryRunner(agent=agent, app_name=f"swarm_task_{agent_name}")
            response_chunks = []

            async for event in runner.run_async(
                user_id="swarm_coordinator",
                session_id=f"session_{agent_name}",
                message=task_prompt,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            response_chunks.append(part.text)

            output_text = "".join(response_chunks).strip()
            return {
                "status": "success",
                "agent": agent_name,
                "output": output_text or "Task executed with no direct text response.",
            }
        except Exception as e:
            return {
                "status": "error",
                "agent": agent_name,
                "message": f"Failed executing task on agent '{agent_name}': {e!s}",
            }

    async def save_file_as_artifact(
        filename: str,
        content: str,
        mime_type: str = "text/plain",
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Saves text or document content as a versioned session artifact in ADK.

        Args:
            filename: Name of the artifact file (e.g. 'summary.md', 'code.py', 'user:pref.json').
            content: Text or string content of the file.
            mime_type: MIME type (e.g. 'text/plain', 'text/markdown', 'application/json').
        """
        if not tool_context:
            return {"status": "error", "message": "No tool context available to save artifact."}

        try:
            part = genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type=mime_type,
                    data=content.encode("utf-8"),
                )
            )
            version = await tool_context.save_artifact(filename=filename, artifact=part)
            return {
                "status": "success",
                "message": f"Artifact '{filename}' saved successfully.",
                "filename": filename,
                "version": version,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed saving artifact: {e!s}"}

    async def load_file_artifact(
        filename: str,
        version: int | None = None,
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Loads an existing artifact from the session by filename and optional version.

        Args:
            filename: Name of the artifact file to load.
            version: Optional version number (defaults to latest if None).
        """
        if not tool_context:
            return {"status": "error", "message": "No tool context available to load artifact."}

        try:
            part = await tool_context.load_artifact(filename=filename, version=version)
            if not part:
                return {"status": "error", "message": f"Artifact '{filename}' not found."}

            content = None
            if part.text:
                content = part.text
            elif part.inline_data and part.inline_data.data:
                content = part.inline_data.data.decode("utf-8", errors="replace")

            return {
                "status": "success",
                "filename": filename,
                "content": content,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed loading artifact: {e!s}"}

    async def list_session_artifacts(
        tool_context: ToolContext | None = None,
    ) -> dict[str, Any]:
        """Lists the names of all artifacts attached to the current session."""
        if not tool_context:
            return {"status": "error", "message": "No tool context available to list artifacts."}

        try:
            names = await tool_context.list_artifacts()
            return {
                "status": "success",
                "artifacts": names,
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed listing artifacts: {e!s}"}

    return [
        spawn_agent,
        list_swarm_agents,
        delegate_to_agent,
        save_file_as_artifact,
        load_file_artifact,
        list_session_artifacts,
    ]
