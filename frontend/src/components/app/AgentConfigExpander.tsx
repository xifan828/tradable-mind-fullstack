import { useState } from 'react'
import { useAppStore } from '../../store/useAppStore'
import type { ModelLabel, ReasoningEffort } from '../../types'
import { MODEL_LABELS, REASONING_EFFORTS } from '../../types'

interface SelectOption<T extends string> {
  value: T
  label: string
}

const MODEL_OPTIONS: SelectOption<ModelLabel>[] = MODEL_LABELS.map((label) => ({
  value: label,
  label,
}))

const EFFORT_LABELS: Record<ReasoningEffort, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

const EFFORT_OPTIONS: SelectOption<ReasoningEffort>[] = REASONING_EFFORTS.map((effort) => ({
  value: effort,
  label: EFFORT_LABELS[effort],
}))

export default function AgentConfigExpander() {
  const [open, setOpen] = useState(false)

  const agentModelLabel = useAppStore((s) => s.agentModelLabel)
  const setAgentModelLabel = useAppStore((s) => s.setAgentModelLabel)
  const agentReasoningEffort = useAppStore((s) => s.agentReasoningEffort)
  const setAgentReasoningEffort = useAppStore((s) => s.setAgentReasoningEffort)
  const minResearchIterations = useAppStore((s) => s.minResearchIterations)
  const setMinResearchIterations = useAppStore((s) => s.setMinResearchIterations)
  const maxResearchIterations = useAppStore((s) => s.maxResearchIterations)
  const setMaxResearchIterations = useAppStore((s) => s.setMaxResearchIterations)
  const maxConcurrentTasks = useAppStore((s) => s.maxConcurrentTasks)
  const setMaxConcurrentTasks = useAppStore((s) => s.setMaxConcurrentTasks)
  const isStreaming = useAppStore((s) => s.isStreaming)

  return (
    <div className="mb-4 border-b" style={{ borderColor: 'var(--border)' }}>
      <button
        className="tm-focus flex w-full items-center justify-between py-2.5 transition-colors"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="tm-kicker" style={{ color: 'var(--text-muted)' }}>
          Methodology
        </span>
        <span
          className="flex items-center gap-2 font-mono text-[0.68rem]"
          style={{ color: 'var(--text-faint)' }}
        >
          {agentModelLabel} · {EFFORT_LABELS[agentReasoningEffort]}
          <span
            className="material-symbol transition-transform"
            style={{ fontSize: 18, transform: open ? 'rotate(180deg)' : 'none' }}
          >
            expand_more
          </span>
        </span>
      </button>

      {open && (
        <div className="tm-fade-in border-t py-4" style={{ borderColor: 'var(--border)' }}>
          <p className="mb-4 text-xs" style={{ color: 'var(--text-muted)' }}>
            Settings apply automatically to your next message.
          </p>

          {/* The chart and quant subagents take their model and thinking level
              from the backend's .env, so only the orchestrator is selectable. */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Select
              label="Model"
              value={agentModelLabel}
              options={MODEL_OPTIONS}
              disabled={isStreaming}
              onChange={setAgentModelLabel}
            />
            <Select
              label="Thinking Level"
              value={agentReasoningEffort}
              options={EFFORT_OPTIONS}
              disabled={isStreaming}
              onChange={setAgentReasoningEffort}
            />
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <Stepper label="Min Iterations" value={minResearchIterations} options={[1, 2, 3, 4, 5, 6]} disabled={isStreaming} onChange={setMinResearchIterations} />
            <Stepper label="Max Iterations" value={maxResearchIterations} options={[1, 2, 3, 4, 5, 6]} disabled={isStreaming} onChange={setMaxResearchIterations} />
            <Stepper label="Parallel Tasks" value={maxConcurrentTasks} options={[1, 2, 3, 4]} disabled={isStreaming} onChange={setMaxConcurrentTasks} />
          </div>
        </div>
      )}
    </div>
  )
}

function Select<T extends string>({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string
  value: T
  options: SelectOption<T>[]
  disabled: boolean
  onChange: (v: T) => void
}) {
  return (
    <div>
      <label className="tm-field-label mb-1.5">{label}</label>
      <select
        className="tm-input"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function Stepper({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string
  value: number
  options: number[]
  disabled: boolean
  onChange: (n: number) => void
}) {
  return (
    <div>
      <label className="tm-field-label mb-1.5">{label}</label>
      <select
        className="tm-input font-mono"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {options.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </div>
  )
}
