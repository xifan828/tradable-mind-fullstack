import { Client } from '@langchain/langgraph-sdk'
import type { StreamEvent } from '../types'
import { API_BASE } from './apiBase'

export const langGraphClient = new Client({ apiUrl: API_BASE })

interface RawChunk {
  event: string
  data: unknown
}

interface ContentBlock {
  type?: string
  text?: string
  thinking?: string
  reasoning?: string
}

interface ToolCall {
  id?: string
  name?: string
  args?: Record<string, unknown>
}

function asContentBlocks(content: unknown): ContentBlock[] {
  if (typeof content === 'string') return [{ type: 'text', text: content }]
  if (Array.isArray(content)) return content as ContentBlock[]
  return []
}

/**
 * Translates a raw LangGraph SDK stream chunk into zero or more normalized
 * StreamEvents the chat UI understands.
 *
 * Ordering matters: the agent runs many tools, and the UI must show each tool
 * call followed by *its* result, in the order they happened. To get that we use
 * exactly two stream modes for two non-overlapping purposes:
 *
 *   - `messages-tuple` → streaming assistant TEXT/THINKING tokens only. These are
 *     the only things that benefit from token-by-token streaming.
 *   - `updates` → tool CALLS and tool RESULTS. Updates fire once per super-step,
 *     in execution order, so a tool call and its result arrive in sequence rather
 *     than the call (streamed as partial deltas) racing ahead of the result.
 *
 * We deliberately do NOT emit tool calls from `messages-tuple` (they stream as
 * incomplete arg deltas and arrive out of order with their results), and we do
 * NOT emit text from `updates` (it would duplicate the streamed tokens).
 */
export function normalizeChunk(chunk: RawChunk): StreamEvent[] {
  const events: StreamEvent[] = []
  const { event, data } = chunk

  if (event === 'metadata') return events

  if (event === 'error') {
    events.push({ event_type: 'error', content: data })
    return events
  }

  // Streaming assistant text / thinking tokens. `messages-tuple` emits
  // `{ event: 'messages', data: [message, metadata] }`; the legacy `messages`
  // modes emit a cumulative array. Normalize both to a flat list of messages.
  if (event === 'messages' || event === 'messages/partial' || event === 'messages/complete') {
    let messages: unknown[]
    if (event === 'messages') {
      messages = Array.isArray(data) ? [data[0]] : [data]
    } else {
      messages = Array.isArray(data) ? data : [data]
    }
    for (const msg of messages) {
      if (!msg || typeof msg !== 'object') continue
      const m = msg as Record<string, unknown>
      // Tool result messages also flow through this stream; their content is
      // handled (or suppressed) via `updates`, so never render them as text here.
      if (m.type === 'tool' || m.tool_call_id) continue
      for (const block of asContentBlocks(m.content)) {
        if (block.type === 'thinking' || block.type === 'reasoning') {
          const text = block.thinking ?? block.reasoning ?? block.text
          if (text) events.push({ event_type: 'thinking', content: text })
        } else if (block.type === 'text' && block.text) {
          events.push({ event_type: 'text', content: block.text })
        }
      }
    }
    return events
  }

  // Tool calls and tool results, in chronological super-step order.
  if (event === 'updates') {
    const updates = data as Record<string, unknown>
    for (const nodeUpdate of Object.values(updates ?? {})) {
      if (!nodeUpdate || typeof nodeUpdate !== 'object') continue
      const upd = nodeUpdate as Record<string, unknown>
      const msgs = upd.messages
      const msgList = Array.isArray(msgs) ? msgs : msgs ? [msgs] : []
      for (const msg of msgList) {
        if (!msg || typeof msg !== 'object') continue
        const m = msg as Record<string, unknown>
        // Tool result message.
        if (m.type === 'tool' || m.tool_call_id) {
          events.push({
            event_type: 'tool_result',
            content: m.content,
            tool_call_id: m.tool_call_id as string | undefined,
          })
          continue
        }
        // AI message carrying one or more tool calls.
        const toolCalls = (m.tool_calls as ToolCall[] | undefined) ?? []
        for (const tc of toolCalls) {
          if (!tc.name) continue
          events.push({
            event_type: 'tool_call',
            content: tc.args ?? {},
            tool_name: tc.name,
            tool_call_id: tc.id,
          })
        }
      }
    }
    return events
  }

  return events
}
