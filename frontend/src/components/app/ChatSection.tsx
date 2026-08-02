import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useAppStore } from '../../store/useAppStore'
import { langGraphClient, normalizeChunk } from '../../lib/agentClient'
import { MODEL_MAP } from '../../types'
import type { ChatMessage, StreamEvent } from '../../types'
import AgentConfigExpander from './AgentConfigExpander'
import ChatMessageItem from './ChatMessageItem'
import WelcomeCard from './WelcomeCard'

let msgCounter = 0
function nextId(prefix: string) {
  msgCounter += 1
  return `${prefix}-${Date.now()}-${msgCounter}`
}

interface ChatSectionProps {
  onClearConversation: () => void
}

export default function ChatSection({ onClearConversation }: ChatSectionProps) {
  const messages = useAppStore((s) => s.messages)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const geminiApiKey = useAppStore((s) => s.geminiApiKey)
  const chartLoaded = useAppStore((s) => s.chartLoaded)

  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  // Staggered messages reveal after the store update; follow them too.
  useEffect(() => {
    function onReveal() {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
    window.addEventListener('tm:msg-reveal', onReveal)
    return () => window.removeEventListener('tm:msg-reveal', onReveal)
  }, [])

  return (
    <div className="flex h-full min-h-0 flex-col border-l" style={{ borderColor: 'var(--border)' }}>
      {/* Panel header */}
      <div
        className="flex shrink-0 items-center justify-between gap-3 border-b px-5 py-3.5"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-2.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: 'var(--up)' }}
            aria-hidden
          />
          <span className="font-display text-lg leading-none" style={{ fontWeight: 650, color: 'var(--text)' }}>
            AI Analyst
          </span>
          <span className="tm-kicker hidden sm:inline">Multi-agent</span>
        </div>
        <button
          type="button"
          onClick={onClearConversation}
          title="Clear conversation"
          className="tm-focus inline-flex items-center gap-1 font-mono text-[0.68rem] font-semibold uppercase tracking-[0.08em] transition-colors hover:text-[color:var(--brand)]"
          style={{ color: 'var(--text-faint)' }}
        >
          <span className="material-symbol" style={{ fontSize: 15 }}>
            restart_alt
          </span>
          Clear
        </button>
      </div>

      {/* Scrollable conversation region */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <AgentConfigExpander />

        {!chartLoaded && (
          <div
            className="mb-4 flex items-center gap-2 border-l-2 py-1.5 pl-3 text-[0.8rem]"
            style={{ borderColor: 'var(--border-strong)', color: 'var(--text-faint)' }}
          >
            <span className="material-symbol" style={{ fontSize: 16 }}>
              candlestick_chart
            </span>
            No chart loaded yet — set a market in the toolbar for chart-aware analysis.
          </div>
        )}

        {!geminiApiKey && (
          <div
            className="mb-4 flex items-center gap-2 border-l-2 py-1.5 pl-3 text-sm"
            style={{ borderColor: 'var(--warn)', color: 'var(--warn)' }}
          >
            <span className="material-symbol" style={{ fontSize: 18 }}>
              key
            </span>
            Enter your Gemini API key to enable AI analysis chat.
          </div>
        )}

        <div className="space-y-3">
          {messages.length === 0 && !isStreaming && <WelcomeCard />}
          {messages.map((m) => (
            <RevealOnTime key={m.id} revealAt={m.revealAt}>
              <ChatMessageItem message={m} />
            </RevealOnTime>
          ))}
          {isStreaming && <ThinkingIndicator />}
          <div ref={scrollRef} />
        </div>
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t px-4 py-3" style={{ borderColor: 'var(--border)' }}>
        <ChatInput />
      </div>
    </div>
  )
}

/**
 * Holds a message off-screen until its `revealAt` timestamp, then fades it
 * in. Burst-arriving stream events (thinking + plan + sub-agent tasks) get
 * staggered timestamps in createStreamHandler, so they appear one by one.
 */
function RevealOnTime({ revealAt, children }: { revealAt?: number; children: ReactNode }) {
  const [visible, setVisible] = useState(() => !revealAt || revealAt <= Date.now())

  useEffect(() => {
    if (visible || !revealAt) return
    const t = setTimeout(() => {
      setVisible(true)
      window.dispatchEvent(new CustomEvent('tm:msg-reveal'))
    }, Math.max(0, revealAt - Date.now()))
    return () => clearTimeout(t)
  }, [visible, revealAt])

  if (!visible) return null
  return <div className="tm-msg-in">{children}</div>
}

function ThinkingIndicator() {
  return (
    <div
      className="flex items-center gap-2.5 border-l-2 py-0.5 pl-3.5"
      style={{ borderColor: 'var(--brand)' }}
    >
      <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Thinking</span>
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="tm-think-dot h-1 w-1 rounded-full"
            style={{ background: 'var(--brand)', animationDelay: `${i * 0.18}s` }}
          />
        ))}
      </span>
    </div>
  )
}

function ChatInput() {
  const [value, setValue] = useState('')

  const geminiApiKey = useAppStore((s) => s.geminiApiKey)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const disabled = !geminiApiKey || isStreaming

  // Suggested prompts (WelcomeCard) fill the composer via this event.
  useEffect(() => {
    function onSuggest(e: Event) {
      const detail = (e as CustomEvent<string>).detail
      if (typeof detail === 'string') setValue(detail)
    }
    window.addEventListener('tm:suggest', onSuggest)
    return () => window.removeEventListener('tm:suggest', onSuggest)
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const query = value.trim()
    if (!query || disabled) return
    setValue('')
    await sendMessage(query)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border py-1 pl-4 pr-1 transition-shadow focus-within:shadow-[0_0_0_3px_var(--brand-ring)]"
      style={{
        borderColor: 'var(--border-strong)',
        borderRadius: 'var(--radius-pill)',
        background: 'var(--surface)',
      }}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={isStreaming ? 'Analyzing…' : 'Ask about the chart…'}
        className="flex-1 bg-transparent py-2 text-sm outline-none disabled:opacity-50"
        style={{ color: 'var(--text)' }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="tm-btn tm-btn-primary !p-2"
      >
        <span className="material-symbol" style={{ fontSize: 17 }}>
          arrow_upward
        </span>
      </button>
    </form>
  )
}

async function sendMessage(query: string) {
  const store = useAppStore.getState()
  const {
    geminiApiKey,
    currentAssetType,
    agentModelLabel,
    subagentModelLabel,
    minResearchIterations,
    maxResearchIterations,
    maxConcurrentTasks,
  } = store

  store.setIsStreaming(true)

  const userMessage: ChatMessage = {
    id: nextId('user'),
    role: 'user',
    type: 'text',
    content: query,
  }
  store.addMessage(userMessage)

  let threadId = store.threadId
  try {
    if (!threadId) {
      const thread = await langGraphClient.threads.create()
      threadId = thread.thread_id
      store.setThreadId(threadId)
    }

    const streamResponse = langGraphClient.runs.stream(threadId, 'agent', {
      input: { messages: [{ role: 'human', content: query }] },
      context: {
        api_key: geminiApiKey,
        asset_type: currentAssetType,
        model_name: MODEL_MAP[agentModelLabel],
        subagent_model_name: MODEL_MAP[subagentModelLabel],
        min_research_iterations: minResearchIterations,
        max_research_iterations: maxResearchIterations,
        max_concurrent_tasks: maxConcurrentTasks,
      },
      streamMode: ['messages-tuple', 'updates', 'custom'],
    })

    const handler = createStreamHandler()

    for await (const chunk of streamResponse) {
      const events = normalizeChunk(chunk as { event: string; data: unknown })
      for (const evt of events) {
        handler.handle(evt)
      }
    }
    handler.finish()
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    const friendly = message.includes('free_tier')
      ? 'Your Gemini API key appears to be a free-tier key. Please use a paid-tier key — see the rate limits page for details.'
      : message
    useAppStore.getState().addMessage({
      id: nextId('error'),
      role: 'assistant',
      type: 'text',
      content: `⚠ ${friendly}`,
    })
  } finally {
    useAppStore.getState().setIsStreaming(false)
    runPendingActions()
  }
}

// Orchestrator tools that should not surface their own tool blocks in the chat.
const HIDDEN_TOOLS = new Set(['read_todos'])

/**
 * Turns the ordered stream of events into chat messages. Events already arrive
 * in chronological order (see normalizeChunk), so this just maps each one to a
 * message and, for the `task` tool, fills the result into the same block.
 *
 * Per-tool handling:
 *   - read_todos      → hidden entirely (call + result)
 *   - think_tool      → rendered as a Thinking block (its reflection); result hidden
 *   - write_todos     → rendered as the Planning block; result hidden
 *   - task            → tool block whose result is merged in when it arrives
 *   - assistant text  → streamed into a single bubble, rendered as markdown
 */
function createStreamHandler() {
  const store = useAppStore.getState()
  // Maps a tool_call_id to the message id whose `result` should be filled in.
  const resultTargets = new Map<string, string>()
  let pendingTextId: string | null = null

  // Events often arrive in one burst (thinking + plan + task calls). Give
  // each assistant message a staggered reveal timestamp so the UI unfolds
  // sequentially instead of dumping everything at once.
  const STAGGER_MS = 700
  let lastRevealAt = 0
  function addPaced(message: ChatMessage) {
    const revealAt = Math.max(Date.now(), lastRevealAt + STAGGER_MS)
    lastRevealAt = revealAt
    store.addMessage({ ...message, revealAt })
  }

  function endText() {
    pendingTextId = null
  }

  function handle(evt: StreamEvent) {
    switch (evt.event_type) {
      case 'thinking':
        endText()
        addPaced({
          id: nextId('thinking'),
          role: 'assistant',
          type: 'thinking',
          content: String(evt.content),
        })
        break

      case 'tool_call': {
        endText()
        const name = evt.tool_name ?? 'tool'
        const args = (evt.content as Record<string, unknown>) ?? {}

        if (HIDDEN_TOOLS.has(name)) break

        if (name === 'think_tool') {
          const reflection = typeof args.reflection === 'string' ? args.reflection : ''
          if (reflection.trim()) {
            addPaced({
              id: nextId('thinking'),
              role: 'assistant',
              type: 'thinking',
              content: reflection,
            })
          }
          break
        }

        const id = nextId('toolcall')
        // The task tool's result is merged back into this same block.
        if (name === 'task' && evt.tool_call_id) {
          resultTargets.set(evt.tool_call_id, id)
        }
        addPaced({
          id,
          role: 'assistant',
          type: 'tool_call',
          content: '',
          toolName: name,
          toolArgs: args,
          toolCallId: evt.tool_call_id,
          result: name === 'task' ? null : undefined,
        })
        break
      }

      case 'tool_result': {
        // Only task results are shown; they merge into their call block.
        const targetId = evt.tool_call_id ? resultTargets.get(evt.tool_call_id) : undefined
        if (!targetId) break
        const result = typeof evt.content === 'string' ? evt.content : JSON.stringify(evt.content)
        store.updateMessage(targetId, (m) => ({ ...m, result }))
        break
      }

      case 'text': {
        const text = String(evt.content)
        if (pendingTextId) {
          store.updateMessage(pendingTextId, (m) => ({ ...m, content: m.content + text }))
        } else {
          pendingTextId = nextId('text')
          addPaced({
            id: pendingTextId,
            role: 'assistant',
            type: 'text',
            content: text,
          })
        }
        break
      }

      case 'error':
        endText()
        addPaced({
          id: nextId('error'),
          role: 'assistant',
          type: 'text',
          content: `⚠ ${typeof evt.content === 'string' ? evt.content : JSON.stringify(evt.content)}`,
        })
        break
    }
  }

  function finish() {
    endText()
  }

  return { handle, finish }
}

function runPendingActions() {
  const store = useAppStore.getState()
  if (store.pendingClearConversation) {
    store.setPendingClearConversation(false)
    store.resetConversation()
  }
  if (store.pendingLoadChart) {
    store.setPendingLoadChart(false)
    window.dispatchEvent(new CustomEvent('tm:load-chart'))
  }
}
