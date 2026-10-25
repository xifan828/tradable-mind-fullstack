import asyncio
import shutil
from pathlib import Path

from langchain.tools import tool

from agent.prompts.technical_analysis import POST_TOOL_DESCRIPTION, POST_TO_X_PROMPT

# The hermes CLI is not guaranteed to be on the backend process's PATH, so fall
# back to its standard install location.
HERMES_BIN_FALLBACK = Path.home() / ".hermes" / "hermes-agent" / ".hermes" / "bin" / "hermes"

# Browser automation is slow; the subprocess also has to log in and verify the post.
POST_TIMEOUT_SECONDS = 600

# Every post drives the same real browser profile, so two concurrent calls would
# fight over it (and could double-post). Serialize them.
_post_lock = asyncio.Lock()


def _resolve_hermes_bin() -> str | None:
    on_path = shutil.which("hermes")
    if on_path:
        return on_path
    if HERMES_BIN_FALLBACK.exists():
        return str(HERMES_BIN_FALLBACK)
    return None


@tool(description=POST_TOOL_DESCRIPTION, parse_docstring=True)
async def post_to_x(content: str) -> str:
    """Publish the final analysis to X (Twitter) under the Tradable Mind account.

    Args:
        content: The finished, X-ready analysis text to publish. It is posted
            verbatim, so it must be final before calling this tool.

    Returns:
        "posted" if the post was published and verified live, otherwise an
        error string explaining what went wrong.
    """
    if not content or not content.strip():
        return "Error: content is empty, nothing was posted."

    try:
        return await _publish_to_x(content)
    except Exception as e:
        # ToolNode re-raises anything that escapes a tool, which aborts the whole
        # run (the orchestrator never gets a result to react to). Anything
        # unexpected - including a blocking-call guard from a sync helper - has
        # to come back as a tool result instead.
        return (
            f"Error: publishing to X failed unexpectedly ({type(e).__name__}). {e} "
            "The post was not confirmed - verify the Tradable_Mind timeline before retrying."
        )


async def _publish_to_x(content: str) -> str:
    # shutil.which does os.access and Path.exists does os.stat: both blocking
    # syscalls, which langgraph dev's blockbuster guard turns into a hard error
    # rather than a slow call. Resolve off the event loop.
    hermes_bin = await asyncio.to_thread(_resolve_hermes_bin)
    if hermes_bin is None:
        return (
            "Error: the hermes CLI was not found on PATH or at "
            f"{HERMES_BIN_FALLBACK}. Cannot publish to X."
        )

    prompt = POST_TO_X_PROMPT.format(content=content)

    async with _post_lock:
        try:
            # argv list, no shell involved. The prompt goes in over stdin via
            # `--query-file -`, which the CLI documents as the path for
            # arbitrary text, so quotes, $(...) and backticks in the analysis
            # are never shell-interpreted and never touch disk.
            process = await asyncio.create_subprocess_exec(
                hermes_bin,
                "chat",
                "--oneshot",
                "-Q",
                "--query-file",
                "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path.home()),
            )
        except OSError as e:
            return f"Error: could not start the hermes CLI ({type(e).__name__}: {e})."

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(prompt.encode("utf-8")),
                timeout=POST_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            process.kill()
            await process.wait()  # reap it, otherwise it lingers as a zombie
            return (
                f"Error: publishing timed out after {POST_TIMEOUT_SECONDS}s. "
                "The post may or may not have been published - verify the "
                "Tradable_Mind timeline manually before retrying."
            )

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            detail = stderr_text or stdout_text or "no output"
            return f"Error: the hermes CLI exited with code {process.returncode}. {detail}"

        # -Q prints the final response, then a trailing "session_id: ..." line.
        answer = "\n".join(
            line for line in stdout_text.splitlines() if not line.startswith("session_id:")
        ).strip()

        if answer.lower() == "posted":
            return "posted"
        return (
            "Error: publishing did not confirm success. "
            f"Agent reported: {answer or stderr_text or 'no output'}"
        )
