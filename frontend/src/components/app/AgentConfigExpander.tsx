import { useState } from 'react'
import { useAppStore } from '../../store/useAppStore'
import type { ModelLabel } from '../../types'

const MODEL_LABELS: ModelLabel[] = ['Gemini 3 Flash', 'Gemini 3.1 Pro']

export default function AgentConfigExpander() {
  const [open, setOpen] = useState(false)

  const agentModelLabel = useAppStore((s) => s.agentModelLabel)
  const setAgentModelLabel = useAppStore((s) => s.setAgentModelLabel)
  const subagentModelLabel = useAppStore((s) => s.subagentModelLabel)
  const setSubagentModelLabel = useAppStore((s) => s.setSubagentModelLabel)
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
          {agentModelLabel}
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
            <SegmentedModel
              label="Orchestrator Model"
              value={agentModelLabel}
              options={MODEL_LABELS}
              disabled={isStreaming}
              onChange={setAgentModelLabel}
            />
            <SegmentedModel
              label="Subagent Model"
              value={subagentModelLabel}
              options={MODEL_LABELS}
              disabled={isStreaming}
              onChange={setSubagentModelLabel}
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

function SegmentedModel({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string
  value: ModelLabel
  options: ModelLabel[]
  disabled: boolean
  onChange: (v: ModelLabel) => void
}) {
  return (
    <div>
      <p className="tm-field-label mb-1.5">{label}</p>
      <div
        className="flex border"
        style={{ borderColor: 'var(--border-strong)', borderRadius: 'var(--radius-sm)' }}
      >
        {options.map((opt, i) => {
          const active = value === opt
          return (
            <button
              key={opt}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt)}
              className="flex-1 px-2 py-1.5 text-[0.78rem] font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                background: active ? 'var(--text)' : 'transparent',
                color: active ? 'var(--canvas)' : 'var(--text-faint)',
                borderLeft: i > 0 ? '1px solid var(--border-strong)' : 'none',
              }}
            >
              {opt.replace('Gemini ', '')}
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
