# ADK Agent Swarm

An Agent Swarm architecture powered by the Google **Agent Development Kit (ADK)** supporting:
- **Declarative YAML Configuration**: Define swarm coordinators and specialists declaratively (`swarm_config.yaml`).
- **Dynamic Runtime Agent Spawning**: Create and equip new specialist agents dynamically during conversations or via API.
- **FastAPI / ADK Native ApiServer**: Serve the swarm over standard REST endpoints and Swagger UI (`server.py`).
- **Official ADK CLI Compatible**: Run via `adk run` or test visually in `adk web`.

---

## Quick Start

### 1. Install Dependencies
```bash
uv sync
```

### 2. Set Up API Key
```bash
export GEMINI_API_KEY="your-api-key"
# On Windows PowerShell:
# $env:GEMINI_API_KEY="your-api-key"
```

### 3. Run with ADK CLI
- **Interactive Terminal REPL**:
  ```bash
  uv run adk run swarm
  ```
- **Official Visual Web Playground**:
  ```bash
  uv run adk web . --port 8000
  ```

### 4. Run Standalone FastAPI Server
```bash
uv run uvicorn server:app --reload --port 8000
```
Swagger UI available at: `http://localhost:8000/docs`.

### 5. Run Tests
```bash
uv run pytest
```
