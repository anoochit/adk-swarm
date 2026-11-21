"""
ADK Agent Swarm Registry and Dynamic Agent Factory.
Manages pre-defined agents loaded from configuration and dynamic agents created at runtime.
Supports permanent persistence of dynamic agents into YAML configuration files.
"""
from pathlib import Path
from typing import Any
import yaml
from google.adk.agents import Agent
from google.adk.skills import load_skills_from_dir
from google.adk.tools.skill_toolset import SkillToolset


DEFAULT_ARTIFACT_TOOLS = [
    "save_file_as_artifact",
    "load_file_artifact",
    "list_session_artifacts",
]


class SwarmRegistry:
    def __init__(self, default_model: str = "gemini-2.5-flash"):
        self.default_model = default_model
        self.agents: dict[str, Agent] = {}
        self.tool_catalog: dict[str, Any] = {}
        self.root_agent_name: str | None = None
        self.config_metadata: dict[str, Any] = {}
        self.config_path: str | None = None

    def register_tool(self, name: str, tool_fn_or_obj: Any) -> None:
        """Register a tool in the catalog available to be assigned to agents."""
        self.tool_catalog[name] = tool_fn_or_obj

    def register_tools(self, tools_dict: dict[str, Any]) -> None:
        """Register multiple tools at once."""
        self.tool_catalog.update(tools_dict)

    def load_skills_toolset(self, skills_dir: str | Path = "skills") -> SkillToolset | None:
        """Discovers and loads agent skills from the given directory into a SkillToolset.
        
        Registers the toolset under the name 'skills' in the tool catalog.
        """
        p = Path(skills_dir).resolve()
        if not p.exists() or not p.is_dir():
            return None

        # Check if directory contains any skill subdirectories with SKILL.md
        has_skills = any(child.is_dir() and (child / "SKILL.md").exists() for child in p.iterdir())
        if not has_skills:
            return None

        try:
            skills = load_skills_from_dir(p)
            toolset = SkillToolset(skills=skills)
            self.register_tool("skills", toolset)
            return toolset
        except Exception as e:
            print(f"[SwarmRegistry] Warning: Failed to load skills from '{p}': {e}")
            return None

    def load_from_config(self, config_path: str) -> Agent:
        """Loads swarm and agents specification from a YAML or JSON configuration file."""
        self.config_path = str(Path(config_path).resolve())
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        swarm_cfg = data.get("swarm", {})
        self.default_model = swarm_cfg.get("default_model", self.default_model)
        self.config_metadata = swarm_cfg

        agents_data = data.get("agents", [])
        root_agent = None

        for item in agents_data:
            name = item["name"]
            tool_names = item.get("tools", [])
            resolved_tools = [self.tool_catalog[t] for t in tool_names if t in self.tool_catalog]

            agent = Agent(
                name=name,
                model=item.get("model", self.default_model),
                instruction=item.get("instruction", "").strip(),
                description=item.get("role", f"Agent {name}"),
                tools=resolved_tools,
                disallow_transfer_to_parent=item.get("disallow_transfer_to_parent", False),
                disallow_transfer_to_peers=item.get("disallow_transfer_to_peers", False),
            )
            self.agents[name] = agent

            if item.get("is_root", False):
                self.root_agent_name = name
                root_agent = agent

        # If coordinator has sub_agents, link non-root agents as sub_agents to coordinator
        if root_agent:
            other_agents = [a for name, a in self.agents.items() if name != self.root_agent_name]
            root_agent.sub_agents = other_agents

        return root_agent or next(iter(self.agents.values()))

    def _persist_agent_to_yaml(
        self,
        name: str,
        role: str,
        instruction: str,
        tool_names: list[str] | None = None,
        model: str | None = None,
    ) -> None:
        """Persists a new agent definition into the YAML configuration file."""
        if not self.config_path or not Path(self.config_path).exists():
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "agents" not in data or not isinstance(data["agents"], list):
            data["agents"] = []

        # Avoid duplicate entries in YAML
        for existing in data["agents"]:
            if existing.get("name") == name:
                return

        new_entry = {
            "name": name,
            "role": role,
            "model": model or self.default_model,
            "instruction": instruction.strip(),
            "tools": tool_names or [],
            "disallow_transfer_to_parent": False,
        }
        data["agents"].append(new_entry)

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def spawn_runtime_agent(
        self,
        name: str,
        role: str,
        instruction: str,
        tool_names: list[str] | None = None,
        model: str | None = None,
        persist: bool = True,
    ) -> Agent:
        """Dynamically creates and registers a new Agent at runtime.

        Args:
            name: Unique name of the agent.
            role: Brief role description.
            instruction: Detailed system instruction.
            tool_names: Tool names to bind from catalog.
            model: Optional model override.
            persist: Whether to permanently write this agent to swarm_config.yaml.
        """
        if name in self.agents:
            raise ValueError(f"Agent '{name}' is already registered in the swarm.")

        final_tools = list(tool_names) if tool_names is not None else []
        for default_tool in DEFAULT_ARTIFACT_TOOLS:
            if default_tool in self.tool_catalog and default_tool not in final_tools:
                final_tools.append(default_tool)

        resolved_tools = []
        for t in final_tools:
            if t in self.tool_catalog:
                resolved_tools.append(self.tool_catalog[t])

        new_agent = Agent(
            name=name,
            model=model or self.default_model,
            instruction=instruction.strip(),
            description=role,
            tools=resolved_tools,
        )
        self.agents[name] = new_agent

        # Dynamically link to root coordinator's sub_agents if coordinator exists
        if self.root_agent_name and self.root_agent_name in self.agents:
            root_agent = self.agents[self.root_agent_name]
            if root_agent.sub_agents is None:
                root_agent.sub_agents = []
            if new_agent not in root_agent.sub_agents:
                root_agent.sub_agents.append(new_agent)

        # Permanent persistence to YAML
        if persist:
            self._persist_agent_to_yaml(
                name=name,
                role=role,
                instruction=instruction,
                tool_names=final_tools,
                model=model,
            )

        return new_agent

    def get_agent(self, name: str) -> Agent | None:
        """Retrieve an agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> list[dict[str, Any]]:
        """List summary of all registered agents in the swarm."""
        roster = []
        for name, agent in self.agents.items():
            tool_names = []
            for t in agent.tools:
                if hasattr(t, "name") and t.name:
                    tool_names.append(t.name)
                elif hasattr(t, "__name__"):
                    tool_names.append(t.__name__)
                elif "SkillToolset" in type(t).__name__:
                    tool_names.append("skills")
                else:
                    tool_names.append(str(t))
            roster.append({
                "name": name,
                "role": agent.description,
                "model": getattr(agent, "model", self.default_model),
                "tools": tool_names,
                "is_root": (name == self.root_agent_name),
            })
        return roster
