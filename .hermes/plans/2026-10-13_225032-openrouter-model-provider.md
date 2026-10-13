# Plan: Switch backend LLM provider from Google Gemini to OpenRouter

## Goal

Replace `langchain-google-genai` / `ChatGoogleGenerativeAI` with `langchain-openai`'s `ChatOpenAI` pointed at OpenRouter (`https://openrouter.ai/api/v1`), make the API key server-side only (backend `.env`), and clean out Gemini-shaped response parsing — then verify end-to-end by running the servers and testing in the browser.

## Current context / assumptions

- Backend root: `backend/` (uv project; run with `uv run …`), frontend root: `frontend/` (Vite). Branch `feat/openrouter` is checked out.
- `OPENROUTER_API_KEY` is set in `backend/.env`; the langgraph server loads `.env` (`"env": ".env"` in `backend/langgraph.json`). **`GEMINI_API_KEY` can stay in `.env` (secrets file — not edited) but nothing will read it anymore.**
- **Why OpenAI format (user's question, answered):** Yes — OpenRouter exposes a single OpenAI-compatible REST API (`/chat/completions`) regardless of the underlying vendor model. You always send/receive the OpenAI API format; OpenRouter translates to/from the vendor (Gemini, Anthropic, …) on their side. So the LangChain integration is exactly `ChatOpenAI` with `base_url="https://openrouter.ai/api/v1"` and the OpenRouter key as `api_key`. There is no per-vendor LangChain integration involved.
- All four agents (orchestrator, quant, chart-description, chart-analysis) build their model through **one** shared middleware: `dynamic_model_from_context` in `backend/src/agent/agents/quant_agent.py:13-27`, constructing `ChatGoogleGenerativeAI(model=context.model_name, api_key=context.api_key, max_retries=0)`.
- `backend/src/agent/utils/llm.py` has `ainvoke_gemini_model` / `invoke_gemini_model` (zero callers, verified by grep) and `parse_langchain_ai_message` (called by `task_tool.py:14`).
- Model names arrive at runtime via context dataclasses in `backend/src/agent/states_and_contexts/technical_analysis.py`, defaulting to `models/gemini-3-flash-preview` (Gemini-style IDs).
- **API key flow:** the frontend currently requires the user to paste a "Gemini API key" and sends it as `context.api_key` (`frontend/src/components/app/ChatSection.tsx` — warning banner when missing, `disabled = !geminiApiKey || isStreaming`, and `api_key: geminiApiKey` in the stream context at ~line 279). Since the key now lives in the backend `.env`, the frontend key requirement is being **removed**, not just relabeled.
- **Gemini response shape to remove (not preserve):** Gemini returns `AIMessage.content` as `list[dict]` (`[{"text": …}]`); OpenAI-compatible clients return plain `str`. Three call sites hard-code the old shape and must be changed to the new one only:
  - `backend/src/agent/tools/task_tool.py:109` (chart description)
  - `backend/src/agent/tools/task_tool.py:137` (chart analysis)
  - `backend/src/agent/tools/task_tool.py:223` (quant result)
- Assumption: OpenRouter slugs for the models in use are `google/gemini-3-flash-preview` and `google/gemini-3.1-pro-preview`. **Verify exact slugs on https://openrouter.ai/models before implementing** and substitute everywhere if they differ — this is the most likely 404 source.
- Frontend → backend: `frontend/src/lib/apiBase.ts` defaults the dev server to `http://127.0.0.1:2024` (the `langgraph dev` port), so no wiring change is needed for the browser test.

## Architecture / proposed approach

Add one OpenRouter model factory `build_openrouter_model()` in `backend/src/agent/utils/llm.py` wrapping `ChatOpenAI(model=…, api_key=…, base_url=os.environ["OPENROUTER_API_KEY"], max_retries=0)`, with the key falling back to `OPENROUTER_API_KEY` from the env when the caller doesn't pass one. Re-route the shared middleware and the two helpers through the factory, make `api_key` optional in all three context dataclasses, switch model-ID defaults to OpenRouter slugs, and replace the old-shape `content[0]["text"]` parsing with plain `str(content)`. Frontend: drop the key requirement and update the model map. Verify by running both servers and driving the UI in the browser.

## Step-by-step tasks

Do tasks in order; commit after each. All `uv` commands run from `backend/`, npm from `frontend/`.

### Task 1 — OpenRouter factory in `backend/src/agent/utils/llm.py`

Rewrite the file to:

```python
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

load_dotenv()

openrouter_model_map = {
    "2.5_pro": "google/gemini-2.5-pro",
    "2.5_flash": "google/gemini-2.5-flash",
    "3_pro": "google/gemini-3.1-pro-preview",
    "3_flash": "google/gemini-3-flash-preview",
}


def build_openrouter_model(
    model_name: str,
    api_key: str | None = None,
    **llm_kwargs,
) -> ChatOpenAI:
    """Build a ChatOpenAI client pointed at the OpenRouter API.

    Args:
        model_name: OpenRouter model slug, e.g. "google/gemini-3-flash-preview".
        api_key: OpenRouter API key; falls back to the OPENROUTER_API_KEY
            environment variable when omitted.
        **llm_kwargs: Extra kwargs forwarded to ChatOpenAI (temperature, etc.).
    """
    resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not resolved_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

    return ChatOpenAI(
        model=model_name,
        api_key=resolved_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        **llm_kwargs,
    )


async def ainvoke_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["2.5_pro", "2.5_flash", "3_pro", "3_flash"],
    **llm_kwargs,
) -> AIMessage:
    if model_type not in openrouter_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")
    llm = build_openrouter_model(openrouter_model_map[model_type], **llm_kwargs)
    return await llm.ainvoke(input)


def invoke_model(
    input: str | list[BaseMessage] | list[tuple[str, str]],
    model_type: Literal["2.5_pro", "2.5_flash", "3_pro", "3_flash"],
    **llm_kwargs,
) -> AIMessage:
    if model_type not in openrouter_model_map:
        raise ValueError(f"Unsupported model type: {model_type}")
    llm = build_openrouter_model(openrouter_model_map[model_type], **llm_kwargs)
    return llm.invoke(input)


def parse_langchain_ai_message(ai_message: AIMessage) -> str:
    """Return the message content as a plain string (OpenAI-compatible shape)."""
    return str(ai_message.content)
```

Notes:
- The old helpers `ainvoke_gemini_model` / `invoke_gemini_model` are renamed to `ainvoke_model` / `invoke_model` — safe, they had zero callers.
- `parse_langchain_ai_message` is deliberately stripped to the new shape only (old dual-shape branch deleted — the old shape no longer occurs).
- The hardcoded `base_url` is intentional (YAGNI); there's also a `OPENROUTER_API_KEY` constant to add to `settings.py` — skip it, nothing imports settings for this.

Verify imports of the whole graph chain still work:

```bash
cd backend && uv add langchain-openai
uv run python -c "from agent.utils.llm import build_openrouter_model, parse_langchain_ai_message; print('ok')"
```

Expected: `ok`.

Commit: `git add -A && git commit -m "feat: OpenRouter model factory via langchain-openai"`

### Task 2 — Swap the shared model middleware

Edit `backend/src/agent/agents/quant_agent.py`:
- Delete line 4 (`from langchain_google_genai import ChatGoogleGenerativeAI`).
- Add `from agent.utils.llm import build_openrouter_model`.
- Replace lines 13-27 (`dynamic_model_from_context`) with:

```python
@wrap_model_call
async def dynamic_model_from_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    model_name = request.runtime.context.model_name
    api_key = request.runtime.context.api_key

    model = build_openrouter_model(model_name, api_key=api_key)

    return await handler(request.override(model=model))
```

(`api_key` may now be `None` — the factory falls back to the env var. Touch nothing else in the file.)

Verify the full agent import chain (orchestrator + chart agents reuse this middleware):

```bash
uv run python -c "from agent.graph import graph; print(type(graph))"
```

Expected: a Pregel class (e.g. `<class 'langgraph.pregel.Pregel'>`), no traceback.

Commit: `git add -A && git commit -m "feat: build agent models through OpenRouter factory"`

### Task 3 — Contexts: optional key + OpenRouter default IDs

Edit `backend/src/agent/states_and_contexts/technical_analysis.py`:
- Make `api_key` optional in all three contexts (server-side env key is now the primary source):
  - `QuantAgentContext` (line 26): `api_key: str | None = None`
  - `ChartAgentContext` (line 45): `api_key: str | None = None`
  - `OrchestratorContext` (line 61): `api_key: str | None = None`
- Replace all four occurrences of the default `model_name: str = "models/gemini-3-flash-preview"` (lines 27, 46, 62) and `subagent_model_name: str = "models/gemini-3-flash-preview"` (line 63) with:

```python
model_name: str = "google/gemini-3-flash-preview"
subagent_model_name: str = "google/gemini-3-flash-preview"
```

Edit `backend/src/agent/config/settings.py`: delete line 17 (`GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")`) — dead after the swap.

Verify no stale Gemini IDs remain in source:

```bash
grep -rn "models/gemini\|langchain_google_genai\|GEMINI_API_KEY" src tests --include="*.py"
```

Expected: only hits inside commented-out blocks (`quant_agent.py` `__main__` demo, `graph.py` comments) — acceptable; everything live is clean.

Commit: `git add -A && git commit -m "feat: optional context api_key with OpenRouter default model IDs"`

### Task 4 — New-shape-only response parsing in `task_tool.py`

In `backend/src/agent/tools/task_tool.py`, replace the three old-shape parses (Gemini `content[0]["text"]`) with the new shape:
1. Line 14 import stays: `from agent.utils.llm import parse_langchain_ai_message`.
2. Line 109: `chart_description = result["messages"][-1].content[0]["text"]`
   → `chart_description = parse_langchain_ai_message(result["messages"][-1])`
3. Line 137: `technical_analysis = result["messages"][-1].content[0]["text"]`
   → `technical_analysis = parse_langchain_ai_message(result["messages"][-1])`
4. Lines 222-223:
   ```python
   if messages:
       last_msg = messages[-1]
       return parse_langchain_ai_message(last_msg)
   ```

Verify import:

```bash
uv run python -c "from agent.tools.task_tool import task; print('ok')"
```

Expected: `ok`.

Commit: `git add -A && git commit -m "refactor: parse AIMessage content as OpenAI-style string only"`

### Task 5 — Dependency cleanup

```bash
uv remove langchain-google-genai
uv run python -c "from agent.graph import graph; print(type(graph))"
```

Expected: Pregel class, no `ModuleNotFoundError`. (`uv.lock` updates with the removal.)

Commit: `git add -A && git commit -m "chore: drop langchain-google-genai dependency"`

### Task 6 — Frontend: no more key requirement, OpenRouter slugs

1. `frontend/src/types/index.ts` — replace lines 2-8:
   ```typescript
   export type ModelLabel = 'Gemini 3 Flash' | 'Gemini 3.1 Pro'

   export const MODEL_MAP: Record<ModelLabel, string> = {
     'Gemini 3 Flash': 'google/gemini-3-flash-preview',
     'Gemini 3.1 Pro': 'google/gemini-3.1-pro-preview',
   }
   ```
   (Labels stay "Gemini …" — same models, new route. Renaming labels is out of scope.)
2. `frontend/src/components/app/ChatSection.tsx` — remove the key requirement:
   - Delete the `{!geminiApiKey && (…Enter your Gemini API key…)` warning banner block (~lines 110-119).
   - Change the send button guard (~line 188) from `const disabled = !geminiApiKey || isStreaming` to `const disabled = isStreaming`.
   - In the stream context (~line 279), change `api_key: geminiApiKey` to `api_key: geminiApiKey || undefined` (omitting it entirely when no local key is set, so the backend falls back to `.env`).
3. Leave the "Gemini API key" input field itself and the zustand store untouched — it still works as an optional override if someone pastes a key (YAGNI on deeper UI surgery).

Verify: `cd frontend && npx tsc --noEmit` → no errors.

Commit: `git add -A && git commit -m "feat: make frontend API key optional, send OpenRouter model slugs"`

### Task 7 — End-to-end browser test (the validation for this plan)

No unit or smoke tests per the user's instruction — validation is the live app:

1. Start the backend (background process):
   ```bash
   cd backend && uv run langgraph dev
   ```
   Expected: server ready on `http://127.0.0.1:2024` (watch for "Application startup complete" / the Studio URL in output). Leave it running.
2. Start the frontend dev server (background process):
   ```bash
   cd frontend && npm run dev
   ```
   Expected: Vite ready on `http://localhost:5173` (dev proxy targets `http://127.0.0.1:2024` per `frontend/src/lib/apiBase.ts`). Leave it running.
3. Drive the UI with the browser tool:
   - Open `http://localhost:5173`.
   - Confirm **no** "Enter your Gemini API key" banner and that chat is enabled without entering a key.
   - Load a chart via the toolbar (e.g. EUR/USD, 4h).
   - Send a prompt that exercises the full chain — orchestrator + a subagent tool call, e.g.: `Download EUR/USD 4h data and summarize the current trend using EMA crossovers.`
   - **Pass criteria:** the assistant streams a final answer containing actual EMA/trend content; no error card in the chat; no traceback in the `langgraph dev` terminal output (in particular no `TypeError: 'str' object is not subscriptable` and no OpenRouter 404 on the model slug).
4. Second check for the quant agent path: ask something quantitative like `What is the most successful trading strategy in the last 30 days for XAU/USD?` and confirm a data-backed answer arrives.
5. If anything fails, check the `langgraph dev` output for the exact error before touching code.

Commit: nothing unless a fix was needed; then commit the fix with a targeted message and re-run step 3.

## Risks, tradeoffs, and open questions

- **Exact OpenRouter slugs unverified.** `google/gemini-3-flash-preview` / `google/gemini-3.1-pro-preview` are presumed. Verify on openrouter.ai/models in Task 0 of implementation. Most likely failure mode: 404 "model not found" in Task 7 — fix is substituting the real slug in `MODEL_MAP`, the context defaults, and `openrouter_model_map`.
- **Tool-calling fidelity through the OpenAI-compatible layer.** The quant agent leans on function calling (`create_agent` + tools). Gemini tool-calling works through OpenRouter, but strictness quirks differ from the native API. Task 7 step 4 is the gate; if tool calls misbehave, try a different vendor slug or add `extra_body` options before debugging deeper.
- **`content=None` turns.** With str-only parsing, a tool-call-only turn has `content=""` or `None` (`str(None)` → `"None"`). We only parse final answers (orchestrator/quant end-of-run), so this shouldn't trigger; if it does, guard with `or ""`.
- **Frontend key input semantics.** The input still says "Gemini API key" but now means "optional OpenRouter key override". Deliberately not renamed (scope); flag in the PR description.
- **Open question:** should the now-unused `GEMINI_API_KEY` be deleted from `backend/.env`? Left alone here (secrets file).
- **No automated tests added** per user instruction. If this branch grows beyond a provider swap later, the parsing and factory logic are the natural first candidates for tests.
