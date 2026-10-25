import { useState } from 'react'
import { useAppStore } from '../../store/useAppStore'
import type { ModelLabel, ReasoningEffort } from '../../types'
import { REASONING_EFFORTS } from '../../types'

interface SegmentedOption<T extends string> {
  value: T
  label: string
}

const MODEL_LABELS: ModelLabel[] = ['DeepSeek V4.1 Flash', 'Gemini 3.8 Flash', 'Kimi K3', 'GLM 5.3 FlashX']

// The model labels carry the vendor name; the buttons are narrow, so drop it.
const MODEL_OPTIONS: SegmentedOption<ModelLabel>[] = MODEL_LABELS.map((label) => ({
  value: label,
  label: label.replace('Gemini ', ''),
}))

const EFFORT_LABELS: Record<ReasoningEffort, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

const EFFORT_OPTIONS: SegmentedOption<ReasoningEffort>[] = REASONING_EFFORTS.map((effort) => ({
  value: effort,
  label: EFFORT_LABELS[effort],
}))

export default function AgentConfigExpander() {
  const [open, setOpen] = useState(false)

  const agentModelLabel = useAppStore((s) => s.agentModelLabel)
  const setAgentModelLabel = useAppStore((s) => s.setAgentModelLabel)
  const subagentModelLabel = useAppStore((s) => s.subagentModelLabel)
  const setSubagentModelLabel = useAppStore((s) => s.setSubagentModelLabel)
  const agentReasoningEffort = useAppStore((s) => s.agentReasoningEffort)
  const setAgentReasoningEffort = useAppStore((s) => s.setAgentReasoningEffort)
  const subagentReasoningEffort = useAppStore((s) => s.subagentReasoningEffort)
  const setSubagentReasoningEffort = useAppStore((s) => s.setSubagentReasoningEffort)
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

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Segmented
              label="Orchestrator Model"
              value={agentModelLabel}
              options={MODEL_OPTIONS}
              disabled={isStreaming}
              onChange={setAgentModelLabel}
            />
            <Segmented
              label="Subagent Model"
              value={subagentModelLabel}
              options={MODEL_OPTIONS}
              disabled={isStreaming}
              onChange={setSubagentModelLabel}
            />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Segmented
              label="Orchestrator Reasoning"
              value={agentReasoningEffort}
              options={EFFORT_OPTIONS}
              disabled={isStreaming}
              onChange={setAgentReasoningEffort}
            />
            <Segmented
              label="Subagent Reasoning"
              value={subagentReasoningEffort}
              options={EFFORT_OPTIONS}
              disabled={isStreaming}
              onChange={setSubagentReasoningEffort}
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

function Segmented<T extends string>({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string
  value: T
  options: SegmentedOption<T>[]
  disabled: boolean
  onChange: (v: T) => void
}) {
  return (
    <div>
      <p className="tm-field-label mb-1.5">{label}</p>
      <div
        className="flex border"
        style={{ borderColor: 'var(--border-strong)', borderRadius: 'var(--radius-sm)' }}
      >
        {options.map((option, i) => {
          const active = value === option.value
          return (
            <button
              key={option.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(option.value)}
              className="flex-1 px-2 py-1.5 text-[0.78rem] font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                background: active ? 'var(--text)' : 'transparent',
                color: active ? 'var(--canvas)' : 'var(--text-faint)',
                borderLeft: i > 0 ? '1px solid var(--border-strong)' : 'none',
              }}
            >
              {option.label}
            </button>
          )
        })}
      </div>
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
