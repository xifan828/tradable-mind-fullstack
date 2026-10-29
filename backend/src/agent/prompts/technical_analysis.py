# ============================================================
# Quantitative Analysis - Tool descriptions
# ============================================================

CODE_EXECUTION_DESCRIPTION = """Execute Python in a persistent REPL session (variables stay in memory between calls; 90s timeout resets session).

Pre-loaded environment:
- Libraries: `pd`, `np`, `talib`, `math`, `statistics`, `datetime`, `re`, `itertools`, `functools`, `collections`, `json`. (File I/O, OS, network, and other imports are blocked).
- Helper function in scope:
  `download_market_data(ticker, interval, data_provider="twelvedata", timezone="UTC", outputsize=4000) -> pd.DataFrame`
  * Intervals: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month.
  * Providers: Use `"twelvedata"` (default) for forex (EUR/USD), crypto (BTC/USD), stocks (AAPL), commodities (XAU/USD). Use `"yfinance"` for indices/yields (DX-Y.NYB, ^GSPC, ^TNX, ^TYX, ^FVX, ^IRX).
  * Schema (`Date` is a datetime column, NOT the index):
    `Date, Open, High, Low, Close, EMA10, EMA20, EMA50, EMA100, BB_Upper, BB_Middle, BB_Lower, MACD, MACD_Signal, MACD_Diff, RSI14, ATR, ROC12`

Usage rules:
- Fetch data once per asset/interval and reuse the in-memory DataFrame across calls.
- Do not recalculate pre-loaded indicators unless custom periods are needed; use `talib` for other indicators/patterns.
- Last expression echoes automatically. Print compact summaries (`head()`, `describe()`, aggregated stats)—never echo full DataFrames."""


# ============================================================
# Quant & Chart Analysis Agents
# ============================================================
# The quant agent's system prompt lives in quant_agent.md and the chart agent's
# in chart_agent.md; each agent reads its own file from this directory. The chart
# agent's user-message template lives in agent/agents/chart_agent.py, next to the
# middleware that fills it.

# ============================================================
# Task tool
# ============================================================
TASK_DESCRIPTION = """Delegate a technical analysis task to a specialized sub-agent.

The task should be specific"""

# ============================================================
# Todos tool
# ============================================================
WRITE_TODOS_DESCRIPTION = "Writes down a list of analysis tasks to be completed."
READ_TODOS_DESCRIPTION = "Reads the existing list of analysis tasks and their status."

# ============================================================
# think tool
# ============================================================
THINK_TOOL_DESCRIPTION = """Tool for strategic reflection on research progress and decision-making.

Use this tool after receiving subagents' results and plan next steps systematically.
This creates a deliberate pause in the research workflow for quality decision-making.

Reflection should address:
1. Analysis of current findings - What concrete information have I gathered?
2. Gap assessment - What crucial information is still missing?
3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
4. Strategic decision - Should I stick with the current plan or adapt it?"""

# ============================================================
# Post to X tool
# ============================================================
POST_TOOL_DESCRIPTION = """Publish the final analysis to X (Twitter) on the Tradable Mind account.

Use this tool only once the final trading plan has been synthesized and is ready for publication.
The content is posted verbatim and cannot be edited afterwards, so it must be final."""

POST_TO_X_PROMPT = """Post the content below to X (Twitter) on behalf of Tradable Mind.

<content>
{content}
</content>

Follow these steps exactly:

1. Use the browser tool with `profile=True` so the real, logged-in browser profile is used.
2. Navigate to https://x.com/home and confirm you are logged into X.
3. Make sure the active account is **Tradable_Mind**. If another account is active, switch to Tradable_Mind first. Posting from any other account is a failure.
4. Compose a new post containing the content above **verbatim**: do not rewrite, summarise, translate, correct, shorten, or extend it, and do not add hashtags, emojis, mentions or commentary. Preserve the line breaks exactly.
5. Click Post and wait for the post to be published.
6. Verify the post is really live: open the Tradable_Mind profile page and confirm the new post appears there.
7. If X rejects the post (for example because it exceeds the character limit), do NOT truncate or edit the text. Report the rejection instead.
8. When you are finished, fully close the Chrome session: quit Chrome completely (Cmd+Q) rather than only closing the window, and confirm no Chrome process is still running. Leaving Chrome open holds the profile lock and blocks the next run.

Final answer: reply with exactly `posted` if step 6 succeeded. Otherwise reply with `failed: <short reason>`.
"""