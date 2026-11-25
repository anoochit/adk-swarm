---
marp: true
theme: default
paginate: true
size: 16:9
title: ADK Agent Swarm
description: A self-organizing multi-agent system built on Google ADK
style: |
  section.lead h1 { color: #1a73e8; }
  table { font-size: 0.72em; }
  code { font-size: 0.85em; }
  footer { color: #888; font-size: 0.7em; }
footer: ADK Agent Swarm · Google ADK + Gemini
---

<!-- _class: lead -->
<!-- _paginate: false -->

# ADK Agent Swarm

## A Self-Organizing Multi-Agent System on Google ADK

Define an army of AI specialists in one YAML file — then let the coordinator **spawn new specialists at runtime** when it meets a task no one anticipated.

Python 3.13+ · Google ADK ≥ 2.15 · Gemini 2.5 Flash · MIT

---

## The Problem: Why One Agent Isn't Enough

- A monolithic agent with a giant prompt suffers **instruction dilution**
  — the more responsibilities you pack in, the worse each one performs
- Classic fix: **multi-agent orchestration** — a coordinator dispatches
  to focused specialists
- But most frameworks hard-code every specialist **up front**
- What happens when the coordinator meets a task nobody anticipated?

> **ADK Swarm fills that gap** — the coordinator spawns new specialists
> at runtime, wires them with tools, and persists them to disk.
> *The swarm doesn't just execute; it evolves.*

---

## Architecture at a Glance

```
User / CLI / Web UI
        │
   ┌────▼─────────────────────────┐
   │   Root Coordinator Agent     │
   └────┬─────────────────────────┘
        │  look up & delegate / spawn
   ┌────▼──────────┐      ┌──────────────────┐
   │ SwarmRegistry │◄────►│ swarm_config.yaml│
   └────┬──────────┘      └──────────────────┘
        │
   ┌────▼──────────────────────────────────────┐
   │ Specialists: generalist · researcher ·    │
   │ code_reviewer · security_auditor · ...    │
   │ + dynamically spawned agents              │
   └───────────────────────────────────────────┘
```

| Layer | Responsibility | Implementation |
|---|---|---|
| Configuration | Declarative agent definitions | `swarm_config.yaml` |
| Registry | Lifecycle, tool binding, persistence | `SwarmRegistry` |
| Tools | Capabilities agents can invoke | `swarm_tools.py` + APIs |

---

## Core Design Decisions

**1. YAML-First, Code-Second** — agents are declared, never hard-coded.
- Non-engineers can add agents by editing YAML
- Version-control diffs show exactly what changed
- Runtime-spawned agents produce YAML identical to hand-written ones

**2. Shared Tool Catalog with Late Binding** — tools are registered by
name *before* agents load; `tools: [serper_search]` strings resolve to
callables at load time.

**3. The Coordinator is an Agent, Not a Router** — it has its own prompt,
reasons about routing, and can decide to spawn a new specialist.

**4. Persistence by Default** — `spawn_agent(persist=True)` writes the
new agent back to YAML. Ephemeral agents supported via `persist=False`.

---

## Configuration Layer: `swarm_config.yaml`

```yaml
version: '1.0'
swarm:
  name: adk_agent_swarm
  default_model: gemini-2.5-flash

agents:
  - name: coordinator
    role: Swarm Orchestrator and Dispatcher
    is_root: true              # entry-point agent
    model: gemini-2.5-flash
    instruction: |
      You are the Coordinator of an ADK Agent Swarm...
    tools: [spawn_agent, list_swarm_agents,
            delegate_to_agent, save_file_as_artifact]

  - name: researcher
    role: General Technical Researcher
    tools: [skills, serper_search, save_file_as_artifact]
    disallow_transfer_to_parent: false
```

**Single source of truth** — name, role, instruction, model, tools, and
transfer constraints, all declarative.

---

## The Current Roster

| Agent | Role |
|---|---|
| `coordinator` | Swarm Orchestrator & Dispatcher *(root)* |
| `generalist` | Multi-disciplinary problem solver |
| `researcher` | General technical researcher |
| `code_reviewer` | Code review & quality specialist |
| `security_auditor` | Application security auditor |
| `story_writer` | Children's story author |
| `illustrator` | Children's book illustrator |
| `editor` | Children's content editor |
| `ebook_formatter` | E-book production specialist |

Add a new specialist with a **~10-line YAML block** — or let the
coordinator spawn one for you.

---

## The Registry: Brain of the Swarm

`SwarmRegistry` (swarm_registry.py) holds three responsibilities:

```python
class SwarmRegistry:
    def __init__(self, default_model="gemini-2.5-flash"):
        self.agents: dict[str, Agent] = {}
        self.tool_catalog: dict[str, Any] = {}
        self.root_agent_name: str | None = None
```

1. **Tool catalog** — `register_tool(name, fn)` before config loading
   (plain functions, ADK built-ins, composite `SkillToolset`s)
2. **Config loading** — parse YAML → construct `google.adk.agents.Agent`
   → resolve tool strings → wire every non-root agent into
   `root_agent.sub_agents`
3. **Persistence** — `_persist_agent_to_yaml()` appends spawned agents
   with a **deduplication guard** for idempotency

---

## Tool System: Catalog

| Category | Tools |
|---|---|
| **Orchestration** | `spawn_agent` · `list_swarm_agents` · `delegate_to_agent` |
| **Artifacts** | `save_file_as_artifact` · `load_file_artifact` · `list_session_artifacts` |
| **Skills** | `skills` → `list_skills` / `load_skill` (native `SkillToolset`) |
| **Live Context** | `serper_search` · `google_search` · `get_weather_forecast` · `get_current_datetime` |

- Tools accept typed parameters, return `{"status": ...}` dicts, handle errors gracefully
- Registry-bound tools use a **closure factory** — no globals, trivial to mock:

```python
def create_swarm_tools(registry: SwarmRegistry) -> list[Callable]:
    def spawn_agent(name, role, instruction, tool_names=None, persist=True, ...):
        return {"status": "success", "agent": registry.spawn_runtime_agent(...)}
    ...
```

---

## Dynamic Spawning & Persistence

The signature capability — a real exchange:

```
User: "We need a database architect for our PostgreSQL schema."
Coordinator: No db_architect in the roster. I'll spawn one.

spawn_agent(
    name="db_architect",
    role="PostgreSQL Database Architect",
    instruction="You design optimized, normalized schemas...",
    tool_names=["save_file_as_artifact"],
    persist=True
)
```

Under the hood:

```
validate name → resolve tools from catalog → auto-append artifact tools
→ construct Agent → register → append to root.sub_agents
→ write swarm_config.yaml → return Agent
```

**Auto-equipped:** every spawned agent receives `save` / `load` /
`list` artifact tools by default, so it can produce deliverables
immediately — and it **survives restarts**.

---

## Delegation: Two Patterns

**Pattern 1 — `delegate_to_agent` (programmatic dispatch)**

```python
async def delegate_to_agent(agent_name, task_prompt, tool_context=None):
    agent = registry.get_agent(agent_name)
    runner = InMemoryRunner(agent=agent, app_name=f"swarm_task_{agent_name}")
    await runner.session_service.create_session(...)
    async for event in runner.run_async(...):
        # stream and collect response parts
    return {"status": "success", "output": "".join(response_chunks)}
```

✔ Coordinator can post-process the output — filtering, aggregation,
multi-step workflows.

**Pattern 2 — ADK native sub-agent transfer**

All specialists are wired as `sub_agents`, so ADK routes internally
when the coordinator simply mentions one.

✔ Simple pass-through — user interacts directly with the specialist.

---

## Session Artifacts: Versioned Deliverables

```python
async def save_file_as_artifact(filename, content, mime_type, tool_context=None):
    part = genai_types.Part(inline_data=genai_types.Blob(
        mime_type=mime_type, data=content.encode("utf-8")))
    version = await tool_context.save_artifact(filename=filename, artifact=part)
    return {"status": "success", "filename": filename, "version": version}
```

| Operation | Tool | Description |
|---|---|---|
| Create / Update | `save_file_as_artifact` | Auto-incrementing version numbers |
| Read | `load_file_artifact` | By filename, optionally a specific version |
| Index | `list_session_artifacts` | All artifact filenames in the session |

**Hand-off workflow:** researcher saves `quantum_2026.md` → editor loads
it, saves `quantum_2026_reviewed.md` → full revision history retained.

---

## Agent Skills: Progressive Discovery

```
skills/
└── market-research/
    └── SKILL.md
```

```python
def load_skills_toolset(self, skills_dir="skills") -> SkillToolset | None:
    has_skills = any((child / "SKILL.md").exists() for child in p.iterdir())
    if has_skills:
        toolset = SkillToolset(skills=load_skills_from_dir(p))
        self.register_tool("skills", toolset)
```

- `list_skills` — browse available skills by name and description
- `load_skill` — load full instructions just-in-time

**Just-in-time knowledge:** agents don't preload every capability —
they discover and apply specialized workflows on demand.

---

## ADK Integration: Every Runtime Surface

```python
# swarm/agent.py
def _build() -> App:
    registry = SwarmRegistry()
    registry.register_tool("serper_search", serper_search)
    ...
    for fn in create_swarm_tools(registry):
        registry.register_tool(fn.__name__, fn)
    registry.load_from_config(str(config))
    return App(name="swarm", root_agent=registry.agents[registry.root_agent_name])

app = _build()
root_agent = app.root_agent   # auto-discovered by the ADK CLI
```

| Command | Surface | Use case |
|---|---|---|
| `uv run adk web . --port 8000` | Browser DevUI | Visual playground |
| `uv run adk run swarm` | Terminal REPL | Interactive CLI |
| `uv run adk api_server` | HTTP API | Programmatic integration |
| `uv run python main.py` | Standalone | Build verification & demo |

---

## Testing Strategy

`test_swarm.py` — pytest + pytest-asyncio:

- **Configuration & hierarchy** — root agent and sub-agent wiring from YAML
- **Persistence round-trip** — spawn `crypto_analyst` → fresh registry
  reloads from YAML → agent still present
- **Ephemeral agents** — `persist=False` never touches the config file
- **Artifact lifecycle** — async save → list → load against
  `InMemoryArtifactService` with a mocked `ToolContext`
- **External API mocking** — Serper success paths via
  `monkeypatch.setattr("urllib.request.urlopen", ...)`, plus missing-key
  and empty-query error cases

```bash
uv run pytest -v
```

---

## Session Walkthrough

> _"Create a children's ebook about a robot learning to paint —
> 5 short stories, illustrated, edited, formatted."_

1. Coordinator checks the roster → `story_writer`, `illustrator`, `editor`, `ebook_formatter`
2. Delegates to `story_writer` → `story_1.txt` … `story_5.txt` saved as artifacts
3. Delegates to `editor` → loads each, saves `story_1_edited.txt` …
4. Delegates to `illustrator` → saves `illustration_suggestions.md`
5. Delegates to `ebook_formatter` → saves `ebook_content_outline.md`
6. Coordinator summarizes the pipeline to the user

Every artifact versioned · every interaction tracked ·
**one natural-language request** orchestrates the whole workflow.

---

## Lessons Learned

**What worked well**
- YAML-first design — adding a specialist is a ~10-line block
- Auto-persistence creates organic growth; the swarm adapts to workload
- Closure-based tool factories made testing painless
- ADK's native sub-agent wiring removed the need for a custom router

**Current limitations**
- Single-file persistence — YAML grows unbounded
- No agent retirement — no TTL / usage-based pruning yet
- Synchronous YAML writes — read-modify-write can race under concurrency

**Roadmap**
1. Inter-agent messaging 2. DB-backed persistent sessions
3. Capability negotiation 4. Tool marketplace
5. Observability dashboard

---

## Technical Stack

| Component | Technology | Version |
|---|---|---|
| Runtime | Python | ≥ 3.13 |
| Agent Framework | Google ADK | ≥ 2.15.0 |
| LLM | Gemini 2.5 Flash | — |
| Configuration | YAML (PyYAML) | ≥ 6.0.4 |
| Package Manager | uv | latest |
| Validation | Pydantic | ≥ 2.14.4 |
| Testing | pytest + pytest-asyncio | ≥ 9.2.0 |
| Web Search | Serper API (`google.serper.dev`) | — |
| Weather | wttr.in | — |

---

<!-- _class: lead -->

# Get Started

```bash
git clone https://github.com/your-org/adk-swarm.git
cd adk-swarm && uv sync
cp .env.example .env    # add GEMINI_API_KEY + SERPER_API_KEY

uv run adk web . --port 8000   # visual playground
uv run adk run swarm           # terminal REPL
uv run pytest -v               # test suite
```

**ADK Agent Swarm** — declarative · self-expanding · persistent

MIT License · Built with Google ADK & Gemini
