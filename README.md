# ADK Agent Swarm

An Agent Swarm architecture powered by the Google **Agent Development Kit (ADK)** supporting:

- **Declarative YAML Configuration** — define coordinator and specialist agents in `swarm_config.yaml`.
- **Dynamic Runtime Agent Spawning** — the coordinator LLM can create new specialist agents on the fly via `spawn_agent`.
- **Permanent Persistence** — every spawned agent is written back to `swarm_config.yaml` automatically (default `persist=True`), so they survive restarts.
- **Artifact File Tools** — save, load, and list versioned session files from within any agent.
- **ADK CLI Native** — run interactively with `adk run swarm` or visually with `adk web .`.

---

## Project Structure

```
adk-swarm/
├── swarm/
│   ├── __init__.py        # re-exports app + root_agent for ADK CLI
│   └── agent.py           # _build() wires registry → App (adk web / adk run entry point)
├── swarm_registry.py      # SwarmRegistry: load from YAML, spawn agents, persist to YAML
├── swarm_tools.py         # Tool factory: spawn_agent, list_swarm_agents, delegate_to_agent,
│                          #               save_file_as_artifact, load_file_artifact, list_session_artifacts
├── swarm_config.yaml      # Declarative agent definitions (coordinator, researcher, code_reviewer, ...)
├── main.py                # Standalone demo: build → spawn → verify reload
├── test_swarm.py          # 4 pytest tests
└── pyproject.toml
```

---

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Set Up API Key
```bash
# Linux / macOS
export GEMINI_API_KEY="your-api-key"

# Windows PowerShell
$env:GEMINI_API_KEY="your-api-key"
```

### 3. Run via ADK CLI

**Interactive terminal REPL:**
```bash
uv run adk run swarm
```

**Visual Web Playground (ADK DevUI):**
```bash
uv run adk web . --port 8000
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Run Tests
```bash
uv run pytest -v
```

---

## Configuration — `swarm_config.yaml`

Agents are declared under the `agents:` key. The agent with `is_root: true` becomes the coordinator.

```yaml
version: '1.0'
swarm:
  name: adk_agent_swarm
  default_model: gemini-2.5-flash

agents:
  - name: coordinator
    role: Swarm Orchestrator and Dispatcher
    is_root: true
    model: gemini-2.5-flash
    instruction: |
      You are the Coordinator of an ADK Agent Swarm. ...
    tools:
      - spawn_agent
      - list_swarm_agents
      - delegate_to_agent
      - save_file_as_artifact
      - load_file_artifact
      - list_session_artifacts

  - name: researcher
    role: General Technical Researcher
    model: gemini-2.5-flash
    instruction: |
      You are an expert researcher. ...
    tools:
      - dummy_web_search
      - save_file_as_artifact
```

---

## Permanent Agent Persistence

When the coordinator calls `spawn_agent` with `persist=True` (the default), the new agent is:

1. Created in memory and immediately usable.
2. Written to `swarm_config.yaml` on disk.
3. Automatically available on the **next startup** (loaded from YAML).

**Example — coordinator spawning a new agent during a session:**

> *"Spawn a data_analyst agent that knows how to query SQL databases."*

The coordinator will call:
```json
{
  "name": "data_analyst",
  "role": "SQL & Data Analysis Specialist",
  "instruction": "You write and explain SQL queries...",
  "tool_names": ["save_file_as_artifact"],
  "persist": true
}
```

After that call, `swarm_config.yaml` will contain the new `data_analyst` entry and it will load on the next `adk web .` start.

To spawn an **ephemeral** (session-only) agent pass `persist=False`:
```json
{ "name": "temp_helper", ..., "persist": false }
```

---

## Available Swarm Tools

| Tool | Description |
|---|---|
| `spawn_agent` | Create a new specialist agent (optionally persisted to YAML) |
| `list_swarm_agents` | List all currently registered agents and their tools |
| `delegate_to_agent` | Dispatch a subtask to a named agent and return its output |
| `save_file_as_artifact` | Save text/markdown/JSON content as a versioned session artifact |
| `load_file_artifact` | Load a previously saved artifact by filename (and optional version) |
| `list_session_artifacts` | List all artifact filenames stored in the current session |

---

## Running the Demo

```bash
uv run python main.py
```

This builds the swarm from `swarm_config.yaml`, spawns a `security_auditor` agent with `persist=True`, then reloads from config to verify the agent was written to disk.
