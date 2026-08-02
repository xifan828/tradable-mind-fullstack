# Tradable Mind — Backend

LangGraph backend for [Tradable Mind](../README.md): a multi-agent financial-market analyst plus the FastAPI routes and static hosting for the React frontend. Everything runs as a single LangGraph server.

## What the server exposes

- **Agent graph** (`agent`) — the orchestrator chat agent, reachable through LangGraph's built-in run/thread/stream APIs.
- **Chart data API** — custom FastAPI routes `/api/time-series` and `/api/pivot-levels`, used by the frontend to draw the chart.
- **Frontend** — the built React app (`frontend_dist/`, produced by `npm run build` in `../frontend`) mounted at `/app`.

All three are wired in `langgraph.json`.

## Code structure

All code lives in `src/agent/`:

- `graph.py` / `app.py` / `auth.py` — the three entry points: agent graph, FastAPI app + static mount, and anonymous auth.
- `agents/` — `orchestrator.py` (main chat agent; plans with todos and delegates), `chart_agent.py` (two-stage vision analysis of a rendered chart image), `quant_agent.py` (writes and runs Python against downloaded time series).
- `tools/` — `task_tool.py` (the orchestrator's `task` tool dispatching chart and quantitative tasks), plus think/todo/quant tools.
- `services/` — `technical/technical_indicator.py` (data/chart facade shared by the task tool and the `/api/*` routes), `market_hours/`, `asset_metadata.py`.
- `utils/` — TwelveData and yfinance clients with TA-Lib indicator columns, matplotlib chart rendering, constants.
- `prompts/`, `states_and_contexts/`, `config/`.

## Running

```bash
uv sync                # first time; installs deps incl. the TA-Lib wrapper
uv run langgraph dev   # serves http://localhost:2024 (app at /app/)
```

Requires `TD_API_KEY` (TwelveData) in `.env`. The Gemini key is supplied by the client per request — the server stores no LLM credentials.

Build the frontend first if `frontend_dist/` is missing or stale — see the [root README](../README.md) for the full-stack flow, Docker build (`langgraph build` / `langgraph up`), and deployment notes.
