import { useEffect, useRef, useState, type FormEvent } from 'react'
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

export default function ChatSection() {
  const messages = useAppStore((s) => s.messages)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const geminiApiKey = useAppStore((s) => s.geminiApiKey)

  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Panel header */}
      <div
        className="flex shrink-0 items-center gap-2.5 border-b px-5 py-4"
        style={{ borderColor: 'var(--border)' }}
      >
        <span
          className="flex h-7 w-7 items-center justify-center rounded-lg"
          style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}
        >
          <span className="material-symbol" style={{ fontSize: 18 }}>
            forum
          </span>
        </span>
        <span className="font-display text-base font-bold" style={{ color: 'var(--text)' }}>
          Ask the Agent
        </span>
      </div>

      {/* Scrollable conversation region */}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <AgentConfigExpander />

        {!geminiApiKey && (
          <div
            className="mb-4 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm"
            style={{ background: 'var(--warn-soft)', borderColor: 'var(--warn-border)', color: 'var(--warn)' }}
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
            <ChatMessageItem key={m.id} message={m} />
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

function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="flex items-center gap-2.5 rounded-2xl rounded-bl-md border px-4 py-3"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
      >
        <span className="material-symbol" style={{ fontSize: 18, color: 'var(--brand)' }}>
          neurology
        </span>
        <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
          Agent is analyzing
        </span>
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="tm-think-dot h-1.5 w-1.5 rounded-full"
              style={{ background: 'var(--brand)', animationDelay: `${i * 0.18}s` }}
            />
          ))}
        </span>
      </div>
    </div>
  )
}

function ChatInput() {
  const [value, setValue] = useState('')

  const geminiApiKey = useAppStore((s) => s.geminiApiKey)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const disabled = !geminiApiKey || isStreaming

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
      className="flex items-center gap-2 rounded-2xl border p-2 transition-colors focus-within:border-[color:var(--brand)]"
      style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={isStreaming ? 'Agent is working…' : 'Ask about the chart or request analysis…'}
        className="flex-1 bg-transparent px-3 py-2 text-sm outline-none disabled:opacity-50"
        style={{ color: 'var(--text)' }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="tm-btn tm-btn-primary !px-3.5 !py-2.5"
      >
        <span className="material-symbol" style={{ fontSize: 18 }}>
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

  function endText() {
    pendingTextId = null
  }

  function handle(evt: StreamEvent) {
    switch (evt.event_type) {
      case 'thinking':
        endText()
        store.addMessage({
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
            store.addMessage({
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
        store.addMessage({
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
          store.addMessage({
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
        store.addMessage({
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
  if (store.pendingChartSettings) {
    store.setPendingChartSettings(null)
  }
  if (store.pendingLoadChart) {
    store.setPendingLoadChart(false)
    window.dispatchEvent(new CustomEvent('tm:load-chart'))
  }
}
