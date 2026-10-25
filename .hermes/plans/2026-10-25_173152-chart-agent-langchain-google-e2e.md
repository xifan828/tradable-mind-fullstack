# Chart agent: one LangChain Google GenAI call with native code execution

## Goal

Replace the two-model chain (`chart_description_agent` → `chart_analysis_agent`) behind the `task` tool with a
single `ChatGoogleGenerativeAI` call that binds Gemini's native `code_execution` tool, as prototyped in
`backend/examples/single_agent_chart_code_execution.ipynb`, with the model name and API key read from
`backend/.env`.

## Current context / assumptions

Files that matter:

- `backend/src/agent/tools/task_tool.py:22-152` — `ChartAnalysisTask` renders the chart, calls two LangChain
  agents (`synthesize_chart_description` `:86`, `synthesize_technical_analysis` `:112`), returns the second answer.
- `backend/src/agent/agents/chart_agent.py` — the two `create_agent(...)` objects (19 lines).
- `backend/src/agent/prompts/technical_analysis.py:115-203` — the four chart prompts being retired.
- `backend/src/agent/states_and_contexts/technical_analysis.py:44-50` — `ChartAgentContext`.
- `backend/src/agent/utils/charts.py:321` — `fig.savefig(buf, format='png')` writes to a `BytesIO`. **No PNG is
  ever written to disk**, and this plan keeps it that way.
- `backend/src/agent/config/settings.py` — only `BASE_DIR`, `ENV`, `TWELVE_DATA_API_KEY` today.
- `backend/.env` already has `GEMINI_API_KEY`; `OPENROUTER_API_KEY` stays for the orchestrator and quant agents.
- `langchain-google-genai` is **not installed**; `google-genai 2.31.0` and `langchain-core 1.6.10` already are,
  and both satisfy `langchain-google-genai 4.4.2` (`google-genai<3.0.0,>=2.20.0`, `langchain-core<2.0.0,>=1.6.10`).

LangChain API facts (from the `langchain-google-genai` reference docs; `content_blocks` / `.text` /
`usage_metadata` verified against the installed `langchain-core 1.6.10`):

- `ChatGoogleGenerativeAI(model=..., api_key=..., timeout=..., max_retries=...)`.
- `thinking_level="minimal"|"low"|"medium"|"high"` for Gemini 3+ models (`thinking_budget` for 2.5).
- `model.bind_tools([{"code_execution": {}}])` binds Gemini's **server-side** code interpreter.
- The reply is an `AIMessage` whose `content_blocks` are:
  `{'type': 'server_tool_call', 'name': 'code_interpreter', 'args': {'code': ..., 'language': ...}, 'id': ...}`,
  `{'type': 'server_tool_result', ..., 'status': ..., 'output': ...}`,
  `{'type': 'text', 'text': ...}` (plus `thinking` blocks when thoughts are enabled).
- Images are passed exactly like the existing code: `{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}`
  inside a `HumanMessage`.

### Answers to the two open points

1. **No PNG on disk.** `prepare_chart` returns base64 only; that base64 goes straight into the message content and
   Gemini's sandbox receives the image. No temp file, no `data/charts/`, no cleanup, no `chart_dir` context field,
   no local sandbox tool.
2. **Google direct, no OpenRouter for this agent — through LangChain.** The chart agent is a
   `ChatGoogleGenerativeAI` model created with `GEMINI_API_KEY` (falling back to `GOOGLE_API_KEY`), model name from
   `CHART_AGENT_MODEL` (default `gemini-3.8-flash`), and `code_execution` bound via `bind_tools`. Orchestrator and
   quant keep `build_openrouter_model`.

### Input/output contract — unchanged

Same `task_type="chart"`, same `task_description`, same `ChartAnalysisInput` (asset / interval / indicator / size /
end_date), same renderer, and one string returned as the tool result. Only the execution changes.

## Architecture / proposed approach

`ChartAnalysisTask.synthesize_analysis` builds the same user prompt as today and calls
`analyze_chart(user_prompt, chart_b64)`, which builds a `ChatGoogleGenerativeAI` from `.env`, binds
`{"code_execution": {}}`, sends system + human messages (text + base64 PNG), and parses the reply's
`content_blocks` into a `ChartAnalysisResult`; the task returns `.answer`. `agents/chart_agent.py` becomes a thin
LangChain model-call module — no `create_agent`, no middleware.

**Validation is one end-to-end run of the `task` tool** (Task 6). No unit tests are added.

## Step-by-step tasks

Work from `backend/`, using the project venv explicitly (`.venv/bin/python`); no venv is activated in the shell.

---

### Task 1 — Add `langchain-google-genai`

```bash
cd backend
uv add "langchain-google-genai>=4.4.2"
.venv/bin/python -c "import langchain_google_genai as g; from importlib.metadata import version; print('google-genai integration', version('langchain-google-genai'))"
.venv/bin/python -c "import google.genai, langchain_core; from importlib.metadata import version; print('google-genai', version('google-genai'), '| langchain-core', version('langchain-core'))"
git diff --stat pyproject.toml uv.lock
```

Expected: `google-genai integration 4.4.x`; `google-genai 2.31.0 | langchain-core 1.6.10` (both unchanged —
they already satisfy the new package's ranges); `pyproject.toml` gains `langchain-google-genai>=4.4.2` and
`uv.lock` gains only that package and anything genuinely new. If the lock rewrites unrelated packages, stop and
report it rather than committing a noisy lockfile.

```bash
git add pyproject.toml uv.lock
git commit -m "build: depend on langchain-google-genai for the chart agent"
```

---

### Task 2 — `.env` settings

Append to `backend/src/agent/config/settings.py`:

```python
# Chart agent -----------------------------------------------------------------
# The chart agent is a ChatGoogleGenerativeAI model bound to Gemini's native
# `code_execution` tool, so its model is a Gemini model name, not an OpenRouter
# slug. Override with CHART_AGENT_MODEL in backend/.env.
DEFAULT_CHART_AGENT_MODEL = "gemini-3.8-flash"


def get_chart_agent_model() -> str:
    """Return the chart agent's Gemini model name (CHART_AGENT_MODEL)."""
    return os.getenv("CHART_AGENT_MODEL") or DEFAULT_CHART_AGENT_MODEL


def get_chart_agent_thinking_level() -> str | None:
    """Return the optional Gemini 3 thinking level for the chart call, or None."""
    return os.getenv("CHART_AGENT_THINKING_LEVEL") or None


def get_gemini_api_key() -> str:
    """Return the Google API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set in backend/.env"
        )
    return key
```

Append to `backend/.env.example`:

```
# Chart agent: Gemini with native code execution, called through LangChain.
CHART_AGENT_MODEL=gemini-3.8-flash
# Optional: minimal | low | medium | high. Omit to use the model default.
# CHART_AGENT_THINKING_LEVEL=medium
GEMINI_API_KEY=
```

Verification:

```bash
.venv/bin/python -c "from agent.config.settings import get_chart_agent_model, get_gemini_api_key; print(get_chart_agent_model(), bool(get_gemini_api_key()))"
```

Expected (with `backend/.env` loaded by `settings.py`'s `load_dotenv()`): `gemini-3.8-flash True`.

```bash
git add src/agent/config/settings.py .env.example
git commit -m "feat: chart agent settings from .env (model, thinking level, Gemini key)"
```

---

### Task 3 — New prompts

In `backend/src/agent/prompts/technical_analysis.py`, replace the four legacy chart prompts
(`CHART_DESCRIPTION_AGENT_SYSTEM_PROMPT`, `CHART_DESCRIPTION_USER_PROMPT`,
`CHART_ANALYSIS_AGENT_SYSTEM_PROMPT`, `CHART_ANALYSIS_USER_PROMPT`, formerly lines 115-203) with these two
constants. Keep everything else in the file (the large commented block, `QUANT_AGENT_SYSTEM_PROMPT`,
`TASK_DESCRIPTION`, …).

```python
CHART_AGENT_SYSTEM_PROMPT = """<role>
You are an expert visual financial chart analyst and discretionary trader.
</role>

<goal>
Analyze the provided financial chart image with the code execution tool and answer the user's task precisely.
</goal>

<code_execution>
You have Gemini's native `code_execution` tool, and the chart PNG is attached to this conversation so that
sandbox can open it. Treat code as your ruler, magnifying glass and crosshair: crop regions, print pixel
coordinates of candle bodies and wicks, draw guide lines on a copy, and align price-panel points vertically with
indicator panels — every panel shares the same x-axis.

Display every image you produce (a crop, or an annotated copy) so you actually see it; never assume what a crop
looks like. Stop as soon as the measurements answer the task.
</code_execution>

<general_guidelines>
- Focus exclusively on visual inspection, spatial relationships, price action and indicator structure.
- Do not do quantitative math on OHLC data and do not OCR numbers off the axes; read levels from candle
  geometry and from the latest values the user supplies.
- Measure, don't eyeball. Any claim about a level, a crossover or an alignment must be checked with a crop, a
  pixel probe or a drawn guide first.
- No forecasts: describe structure and levels, not predictions.
</general_guidelines>

<output_format>
Respond in 300 words or fewer using continuous prose (strictly no bullet points, numbered lists, or markdown
headers).
</output_format>"""

CHART_AGENT_USER_PROMPT = """{asset} {interval}, {size} bars, {analysis_type} chart. Current close {current_price}.
Latest values: {extra_context}

Task: {task_description}"""
```

Verification:

```bash
.venv/bin/python -c "from agent.prompts.technical_analysis import CHART_AGENT_SYSTEM_PROMPT as p; print(len(p.split()), 'words')"
```

Expected: `229 words` (anything in 200-260 is fine).

```bash
git add src/agent/prompts/technical_analysis.py
git commit -m "feat: chart agent prompt for native code execution"
```

---

### Task 4 — `agents/chart_agent.py` becomes the LangChain Gemini call

Replace the whole file `backend/src/agent/agents/chart_agent.py`:

```python
"""Chart analysis through Gemini's native code execution, via LangChain.

One call gets the chart PNG, the task and Gemini's `code_execution` tool, so the
model measures the chart in Google's sandbox instead of describing it first and
interpreting the description afterwards. The image travels in the message
content as base64 — nothing is written to disk.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from agent.config.settings import (
    get_chart_agent_model,
    get_chart_agent_thinking_level,
    get_gemini_api_key,
)
from agent.prompts.technical_analysis import CHART_AGENT_SYSTEM_PROMPT
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# langchain-google-genai turns this into Gemini's server-side code interpreter.
CODE_EXECUTION_TOOL = {"code_execution": {}}
REQUEST_TIMEOUT_SECONDS = 600
MAX_RETRIES = 2


@dataclass(frozen=True)
class ChartAnalysisResult:
    """Result of one chart interaction."""

    answer: str
    code: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    usage: dict[str, Any] | None = None


def build_chart_model(
    model: str | None = None,
    thinking_level: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Build the Gemini chat model used for chart analysis.

    Args:
        model: Gemini model name; defaults to CHART_AGENT_MODEL.
        thinking_level: Gemini 3 thinking level; defaults to
            CHART_AGENT_THINKING_LEVEL and is omitted from the request when unset.

    Returns:
        The chat model, with no tools bound yet.
    """
    params: dict[str, Any] = {
        "model": model or get_chart_agent_model(),
        "api_key": get_gemini_api_key(),
        "timeout": REQUEST_TIMEOUT_SECONDS,
        "max_retries": MAX_RETRIES,
    }
    level = thinking_level or get_chart_agent_thinking_level()
    if level:
        params["thinking_level"] = level
    return ChatGoogleGenerativeAI(**params)


def parse_chart_response(message: AIMessage) -> ChartAnalysisResult:
    """Extract the answer, executed code and content-block trace from a reply.

    Args:
        message: The AIMessage returned by the code-execution-bound model.

    Returns:
        The parsed result.

    Raises:
        RuntimeError: When the reply carries no text answer.
    """
    blocks = list(message.content_blocks)
    answer = "".join(
        block.get("text", "") for block in blocks if block.get("type") == "text"
    ).strip() or (message.text or "").strip()
    if not answer:
        raise RuntimeError(
            "Chart agent returned no answer "
            f"(finish_reason={message.response_metadata.get('finish_reason')!r})"
        )

    code: list[str] = []
    for block in blocks:
        if block.get("type") != "server_tool_call":
            continue
        args = block.get("args") or {}
        if isinstance(args, dict) and args.get("code"):
            code.append(args["code"])

    return ChartAnalysisResult(
        answer=answer,
        code=code,
        steps=[str(block.get("type")) for block in blocks],
        usage=dict(message.usage_metadata) if message.usage_metadata else None,
    )


async def analyze_chart(
    user_prompt: str,
    chart_b64: str,
    *,
    model: str | None = None,
    thinking_level: str | None = None,
) -> ChartAnalysisResult:
    """Run one chart analysis with Gemini's native code execution.

    Args:
        user_prompt: Task text built by the caller.
        chart_b64: Base64 PNG of the chart; sent inline, never written to disk.
        model: Gemini model name; defaults to CHART_AGENT_MODEL.
        thinking_level: Gemini 3 thinking level; defaults to CHART_AGENT_THINKING_LEVEL.

    Returns:
        The parsed reply.
    """
    resolved_model = model or get_chart_agent_model()
    chat = build_chart_model(model=resolved_model, thinking_level=thinking_level)
    chat_with_code = chat.bind_tools([CODE_EXECUTION_TOOL])

    message = HumanMessage(
        content=[
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{chart_b64}"},
            },
        ]
    )
    response = await chat_with_code.ainvoke(
        [SystemMessage(content=CHART_AGENT_SYSTEM_PROMPT), message]
    )
    result = parse_chart_response(response)
    logger.info(
        "chart interaction model=%s steps=%s code_runs=%d",
        resolved_model,
        result.steps,
        len(result.code),
    )
    return result
```

Verification:

```bash
.venv/bin/python -c "from agent.agents.chart_agent import analyze_chart, parse_chart_response; print('import ok')"
```

Expected: `import ok`.

```bash
git add src/agent/agents/chart_agent.py
git commit -m "feat: chart agent is one LangChain Gemini call with native code execution"
```

---

### Task 5 — `ChartAnalysisTask` makes one call, writes nothing

Edits are in `backend/src/agent/tools/task_tool.py` plus a trim in
`backend/src/agent/states_and_contexts/technical_analysis.py`.

**5a. Imports** — replace lines 9-16 with:

```python
from agent.agents.chart_agent import analyze_chart
from agent.agents.quant_agent import quant_agent
from agent.services.technical.technical_indicator import TechnicalIndicatorService
from agent.prompts.technical_analysis import CHART_AGENT_USER_PROMPT, TASK_DESCRIPTION
from agent.utils.constants import get_decimal_places
from agent.utils.llm import parse_langchain_ai_message
from agent.states_and_contexts.technical_analysis import ChartAnalysisInput, QuantAgentContext, ChartAgentContext
```

Leave the existing `ToolRuntime`, `HumanMessage`, `asyncio`, `random`, `shutil`, `Path` imports untouched. Do **not**
add `base64`, `uuid`, `dataclasses.replace`, or any `data/charts` constant.

**5b. Replace `synthesize_chart_description` and `synthesize_technical_analysis`** (lines 86-138) with:

```python
    async def synthesize_analysis(
            self,
            encoded_chart: str,
            extra_context: str,
            current_price: float
    ) -> str:
        text_prompt = CHART_AGENT_USER_PROMPT.format(
            asset=self.asset,
            interval=self.interval,
            size=self.size,
            analysis_type=self.indicator,
            current_price=current_price,
            extra_context=extra_context,
            task_description=self.task_description,
        )
        result = await analyze_chart(text_prompt, encoded_chart)
        return result.answer
```

**5c. Replace `execute`** (lines 140-152) with:

```python
    async def execute(self) -> str:
        encoded_chart, extra_context, current_price = await asyncio.to_thread(
            self.prepare_chart_and_context
        )
        return await self.synthesize_analysis(
            encoded_chart=encoded_chart,
            extra_context=extra_context,
            current_price=current_price,
        )
```

**5d. In `task()`**, replace the chart context construction (lines 177-181) with:

```python
        chart_context = ChartAgentContext(asset_type=context.asset_type)
```

**5e. Trim the context** — replace `ChartAgentContext` in
`backend/src/agent/states_and_contexts/technical_analysis.py` (lines 44-50) with:

```python
@dataclass
class ChartAgentContext:
    """Runtime context for the chart analysis task."""

    asset_type: AssetType | None = None  # Asset type for market hours filtering
```

`model_name`/`reasoning_effort` moved to `.env`; `asset_type` is still used by `prepare_chart_and_context`.
`QuantAgentContext` and `OrchestratorContext` keep their fields (`dynamic_model_from_context` still reads them).

**5f. Verification** — nothing in `src/` still references the retired agents or prompts:

```bash
cd backend
grep -rn "chart_description_agent\|chart_analysis_agent\|CHART_DESCRIPTION_AGENT_SYSTEM_PROMPT\|CHART_ANALYSIS_AGENT_SYSTEM_PROMPT\|CHART_DESCRIPTION_USER_PROMPT\|CHART_ANALYSIS_USER_PROMPT" src --include='*.py'
.venv/bin/python -c "from agent.graph import graph; print(type(graph).__name__)"
```

Expected: no output from the grep; `CompiledStateGraph`.

```bash
git add src/agent/tools/task_tool.py src/agent/states_and_contexts/technical_analysis.py
git commit -m "feat: chart task runs one native code-execution interaction"
```

---

### Task 6 — End-to-end run of the task tool (the only validation)

This calls the actual `task` tool coroutine exactly as the orchestrator would, with the runtime it injects.

Preflight — Google must be reachable:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://generativelanguage.googleapis.com/
```

Expected: `404` (reachable). A TLS/EOF error means the local network filter is blocking Google — see Risks.

Run:

```bash
cd backend
.venv/bin/python - <<'PY'
import asyncio
import logging
from types import SimpleNamespace

from dotenv import load_dotenv

from agent.states_and_contexts.technical_analysis import ChartAnalysisInput, OrchestratorContext
from agent.tools.task_tool import task

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")


async def main() -> None:
    answer = await task.coroutine(
        runtime=SimpleNamespace(
            context=OrchestratorContext(asset_type="commodity")
        ),
        task_type="chart",
        task_description="Describe the trend direction and the EMA stacking order.",
        chart_analysis_input=ChartAnalysisInput(
            asset="XAU/USD", interval="1day", indicator="ema", size=80
        ),
    )
    print()
    print(answer)


asyncio.run(main())
PY
ls data | grep charts || echo "no data/charts directory"
```

Expected:

- one log line `agent.agents.chart_agent chart interaction model=gemini-3.8-flash steps=[...] code_runs=N` where
  `steps` contains at least one `server_tool_call` **and** one `server_tool_result` — proof the model measured the
  chart instead of only describing it;
- a non-empty answer of at most ~300 words in continuous prose, naming trend direction and EMA order;
- `no data/charts directory` (nothing was written to disk).

If `steps` contains only `text` (no `server_tool_call`), the model ignored the tool: tighten `<code_execution>` in
`CHART_AGENT_SYSTEM_PROMPT` to "Before answering, run at least one crop or pixel probe", re-run, and commit:

```bash
git add src/agent/prompts/technical_analysis.py
git commit -m "chore: require at least one measurement before answering"
```

---

## Risks, tradeoffs, and open questions

1. **Live verification needs Google reachability.** `curl` currently returns `404` (reachable), but the notebook
   previously hit `APIConnectionError: [SSL: UNEXPECTED_EOF_WHILE_READING]` from this machine. If the E2E fails
   that way it is the network filter, not the code.
2. **`gemini-3.8-flash` must be valid for your key.** `CHART_AGENT_MODEL` is the escape hatch; a `404 model not
   found` means fix `.env`, not the code. `thinking_level` only exists on Gemini 3+ models — leave
   `CHART_AGENT_THINKING_LEVEL` unset if you switch to a 2.5 model (use `thinking_budget` instead, not wired here).
3. **No tests exist for the new code.** The E2E run proves the happy path only; a change to the parser or the
   request shape will not be caught automatically. `task()` still converts any exception into a tool-result error
   string, so failures surface to the orchestrator rather than aborting the run.
4. **Server-side tool call shape is a LangChain contract.** `server_tool_call` / `server_tool_result` blocks come
   from `langchain-google-genai` (4.x); if a future release renames them, `parse_chart_response` would raise
   "returned no answer" only when the text is also missing — otherwise the answer still comes through and
   `code_runs` silently reads 0. Check the E2E log line after any dependency bump.
5. **This agent no longer follows the UI model picker.** `CHART_AGENT_MODEL` wins; quant and orchestrator still use
   `subagent_model_name`. If the picker must stay authoritative, pass a model through instead — that contradicts
   "model from .env", so it is flagged, not chosen.
6. **Cost/latency shape.** One model call, but Gemini can run several code executions inside it; the timeout is
   600 s and there is no cap on code runs. Watch usage before scheduling this.
7. **No image is stored, so a failed run is not replayable.** The chart is regenerated from TwelveData each call.
   If that becomes painful, log the base64 behind a debug flag — explicitly out of scope now, since you asked for
   no disk writes.
8. **Prompt still governs length.** Nothing truncates an over-long answer; add a post-processing trim if downstream
   publishing needs a hard limit.
