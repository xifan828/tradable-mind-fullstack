import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, TaskArgs, TodoItem } from '../../types'

const AGENT_META: Record<string, { icon: string; name: string; color: string }> = {
  chart: { icon: 'candlestick_chart', name: 'Chart Analysis', color: '#2196F3' },
  quantitative: { icon: 'functions', name: 'Quant Analysis', color: '#FF9800' },
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

export default function ChatMessageItem({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[82%] rounded-2xl rounded-br-md px-4 py-2.5 text-sm leading-relaxed"
          style={{ background: 'var(--brand)', color: 'var(--brand-contrast)', boxShadow: '0 6px 18px -8px var(--glow)' }}
        >
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant: structured blocks render full-width; plain text in a soft bubble.
  if (message.type === 'text') {
    return (
      <div className="flex justify-start">
        <div
          className="max-w-[88%] rounded-2xl rounded-bl-md border px-4 py-3"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
        >
          <Markdown>{message.content}</Markdown>
        </div>
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
        return <TodoListBlock todos={todos} title="Planning" icon="checklist" />
      }
      if (message.toolName === 'task') {
        return <TaskBlock args={(message.toolArgs ?? {}) as unknown as TaskArgs} result={message.result ?? null} />
      }
      return <ToolCallBlock name={message.toolName ?? 'tool'} args={message.toolArgs ?? {}} />
    default:
      return null
  }
}

function ThinkingBlock({ content }: { content: string }) {
  return (
    <div
      className="rounded-xl border px-4 py-3"
      style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
    >
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
        <Icon name="neurology" size={15} color="var(--brand)" />
        Thinking
      </p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {content}
      </p>
    </div>
  )
}

function ToolCallBlock({ name, args }: { name: string; args: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="overflow-hidden rounded-xl border" style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}>
      <button
        className="flex w-full items-center justify-between px-4 py-2.5 text-xs font-bold"
        style={{ color: 'var(--text)' }}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="flex items-center gap-1.5">
          <Icon name="build" size={15} color="var(--text-faint)" />
          Tool Call: <span className="font-mono font-semibold" style={{ color: 'var(--brand)' }}>{name}</span>
        </span>
        <Icon name="expand_more" size={18} color="var(--text-faint)" />
      </button>
      {open && (
        <pre
          className="overflow-x-auto border-t px-4 py-3 text-xs"
          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
        >
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
    </div>
  )
}

function TodoListBlock({ todos, title, icon }: { todos: TodoItem[]; title: string; icon: string }) {
  return (
    <div className="rounded-xl border px-4 py-3" style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}>
      <p className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
        <Icon name={icon} size={15} color="var(--brand)" />
        {title}
      </p>
      <ul className="space-y-1.5">
        {todos.map((todo, idx) => {
          const meta = TODO_META[todo.status]
          return (
            <li key={idx} className="flex items-start gap-2 text-sm" style={{ color: 'var(--text)' }}>
              <Icon name={meta.icon} size={16} color={meta.color} spin={meta.spin} />
              <span style={{ opacity: todo.status === 'completed' ? 0.6 : 1 }}>{todo.content}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/**
 * A single `task` tool call. The sub-agent's result is merged into this same
 * block once it arrives (a spinner shows while it is still running).
 */
function TaskBlock({ args, result }: { args: TaskArgs; result: string | null }) {
  const [open, setOpen] = useState(false)
  const meta = AGENT_META[args.task_type] ?? { icon: 'smart_toy', name: args.task_type, color: 'var(--text-faint)' }
  const params = args.chart_analysis_input
  const done = result !== null

  return (
    <div
      className="overflow-hidden rounded-xl border"
      style={{ background: 'var(--surface)', borderColor: done ? 'var(--border)' : 'var(--brand-ring)' }}
    >
      <button className="w-full px-4 py-3 text-left" onClick={() => setOpen((o) => !o)}>
        <div className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--text)' }}>
            <Icon name={meta.icon} size={17} color={meta.color} />
            {meta.name}
          </span>
          <Icon
            name={done ? 'check_circle' : 'progress_activity'}
            size={17}
            color={done ? 'var(--up)' : 'var(--brand)'}
            spin={!done}
          />
        </div>
        <p className="mt-1.5 text-sm italic" style={{ color: 'var(--text-muted)' }}>
          {args.task_description}
        </p>
        {params && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {Object.entries(params).map(([k, v]) => (
              <span
                key={k}
                className="rounded-md px-1.5 py-0.5 font-mono text-[0.7rem]"
                style={{ background: 'var(--surface-3)', color: 'var(--text-faint)' }}
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
