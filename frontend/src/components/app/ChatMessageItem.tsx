import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, TaskArgs, TodoItem } from '../../types'

// Labels for sub-agent reports.
const AGENT_META: Record<string, { icon: string; name: string; color: string }> = {
  chart: { icon: 'candlestick_chart', name: 'Chart Agent', color: 'var(--brand)' },
  quantitative: { icon: 'functions', name: 'Quant Agent', color: 'var(--accent-2)' },
}

const TODO_META: Record<TodoItem['status'], { icon: string; color: string; spin?: boolean }> = {
  pending: { icon: 'radio_button_unchecked', color: 'var(--text-faint)' },
  in_progress: { icon: 'progress_activity', color: 'var(--brand)', spin: true },
  completed: { icon: 'check_circle', color: 'var(--up)' },
}

function Markdown({ children }: { children: string }) {
  return (
    <div className="tm-prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  )
}

function Icon({ name, size = 18, color, spin }: { name: string; size?: number; color?: string; spin?: boolean }) {
  return (
    <span className={`material-symbol ${spin ? 'tm-spin' : ''}`} style={{ fontSize: size, color }}>
      {name}
    </span>
  )
}

/** Small-caps overline used by every reasoning block. */
function Kicker({ children, color }: { children: string; color?: string }) {
  return (
    <p className="tm-kicker mb-1.5" style={color ? { color } : undefined}>
      {children}
    </p>
  )
}

export default function ChatMessageItem({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[82%] px-4 py-2.5 text-sm leading-relaxed"
          style={{
            background: 'var(--brand)',
            color: 'var(--brand-contrast)',
            borderRadius: 'var(--radius-lg)',
            borderBottomRightRadius: 'var(--radius-xs)',
          }}
        >
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant prose: full-width column with a faint rule — reads like copy.
  if (message.type === 'text') {
    return (
      <div className="border-l-2 py-0.5 pl-3.5" style={{ borderColor: 'var(--border)' }}>
        <Markdown>{message.content}</Markdown>
      </div>
    )
  }

  return <AssistantBlock message={message} />
}

function AssistantBlock({ message }: { message: ChatMessage }) {
  switch (message.type) {
    case 'thinking':
      return <ThinkingBlock content={message.content} />
    case 'tool_call':
      if (message.toolName === 'write_todos') {
        const todos = (message.toolArgs?.todos as TodoItem[] | undefined) ?? []
        return <TodoListBlock todos={todos} />
      }
      if (message.toolName === 'task') {
        return <TaskBlock args={(message.toolArgs ?? {}) as unknown as TaskArgs} result={message.result ?? null} />
      }
      return <ToolCallBlock name={message.toolName ?? 'tool'} args={message.toolArgs ?? {}} />
    default:
      return null
  }
}

/** The agent's intermediate reasoning, set off from the answer. */
function ThinkingBlock({ content }: { content: string }) {
  return (
    <div className="border-l-2 py-0.5 pl-3.5" style={{ borderColor: 'var(--brand)' }}>
      <Kicker color="var(--brand)">Thinking</Kicker>
      <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {content}
      </p>
    </div>
  )
}

/** Generic tool call, rendered as a collapsed footnote line. */
function ToolCallBlock({ name, args }: { name: string; args: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        className="tm-focus flex w-full items-center gap-1.5 py-0.5 font-mono text-[0.72rem] transition-colors hover:text-[color:var(--brand)]"
        style={{ color: 'var(--text-faint)' }}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span aria-hidden>{open ? '▾' : '▸'}</span>
        {name}
      </button>
      {open && (
        <pre
          className="tm-fade-in mt-1 overflow-x-auto border-l-2 py-1 pl-3.5 text-xs"
          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
        >
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
    </div>
  )
}

/** The orchestrator's plan, set like a numbered docket. */
function TodoListBlock({ todos }: { todos: TodoItem[] }) {
  return (
    <div>
      <div className="border-b pb-1.5" style={{ borderColor: 'var(--border)' }}>
        <span className="tm-kicker">Research docket</span>
      </div>
      <ul>
        {todos.map((todo, idx) => {
          const meta = TODO_META[todo.status]
          const active = todo.status === 'in_progress'
          const done = todo.status === 'completed'
          return (
            <li
              key={idx}
              className="flex items-baseline gap-3 border-b py-2 text-sm"
              style={{ borderColor: 'var(--border)', opacity: done ? 0.6 : 1 }}
            >
              <span
                className="font-mono text-xs font-semibold"
                style={{ color: active ? 'var(--brand)' : 'var(--text-faint)' }}
              >
                {String(idx + 1).padStart(2, '0')}
              </span>
              <span
                className="flex-1"
                style={{
                  color: 'var(--text)',
                  fontWeight: active ? 500 : 400,
                  textDecoration: done ? 'line-through' : 'none',
                  textDecorationColor: 'var(--text-faint)',
                }}
              >
                {todo.content}
              </span>
              <span className="self-center">
                <Icon name={meta.icon} size={15} color={meta.color} spin={meta.spin} />
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/**
 * A single `task` tool call — a sub-agent's report. The result is merged
 * into this same block once it arrives (a spinner shows while the agent
 * is still working).
 */
function TaskBlock({ args, result }: { args: TaskArgs; result: string | null }) {
  const [open, setOpen] = useState(false)
  const meta = AGENT_META[args.task_type] ?? { icon: 'smart_toy', name: args.task_type, color: 'var(--text-faint)' }
  const params = args.chart_analysis_input
  const done = result !== null

  return (
    <div
      className="overflow-hidden border"
      style={{
        background: 'var(--surface)',
        borderColor: done ? 'var(--border)' : 'var(--brand-ring)',
        borderRadius: 'var(--radius-md)',
      }}
    >
      <button className="tm-focus w-full px-4 py-3 text-left" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <div className="flex items-center justify-between gap-3">
          <span className="tm-kicker !text-[0.66rem]" style={{ color: meta.color }}>
            <Icon name={meta.icon} size={14} color={meta.color} /> {meta.name}
          </span>
          <Icon
            name={done ? 'check_circle' : 'progress_activity'}
            size={16}
            color={done ? 'var(--up)' : 'var(--brand)'}
            spin={!done}
          />
        </div>
        <p className="mt-1.5 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          {done ? args.task_description : 'Working — ' + args.task_description}
        </p>
        {params && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(params).map(([k, v]) => (
              <span
                key={k}
                className="px-1.5 py-0.5 font-mono text-[0.68rem]"
                style={{
                  background: 'var(--surface-2)',
                  color: 'var(--text-faint)',
                  borderRadius: 'var(--radius-xs)',
                }}
              >
                {k}: {String(v)}
              </span>
            ))}
          </div>
        )}
      </button>

      {done && open && (
        <div className="tm-fade-in border-t px-4 py-3" style={{ borderColor: 'var(--border)' }}>
          <Markdown>{result as string}</Markdown>
        </div>
      )}
    </div>
  )
}
