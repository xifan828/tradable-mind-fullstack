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
    <div className="tm-card mb-4 overflow-hidden p-0">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold transition-colors"
        style={{ color: 'var(--text)' }}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="flex items-center gap-2">
          <span className="material-symbol" style={{ fontSize: 18, color: 'var(--brand)' }}>
            tune
          </span>
          Agent Configuration
        </span>
        <span className="flex items-center gap-2 text-xs font-normal" style={{ color: 'var(--text-faint)' }}>
          {agentModelLabel}
          <span
            className="material-symbol transition-transform"
            style={{ fontSize: 20, transform: open ? 'rotate(180deg)' : 'none' }}
          >
            expand_more
          </span>
        </span>
      </button>

      {open && (
        <div className="tm-fade-in border-t px-4 py-4" style={{ borderColor: 'var(--border)' }}>
          <p className="mb-4 text-xs" style={{ color: 'var(--text-faint)' }}>
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
        className="flex rounded-[10px] border p-1"
        style={{ background: 'var(--surface-2)', borderColor: 'var(--border)' }}
      >
        {options.map((opt) => {
          const active = value === opt
          return (
            <button
              key={opt}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt)}
              className="flex-1 rounded-[7px] px-2 py-1.5 text-[0.78rem] font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                background: active ? 'var(--surface)' : 'transparent',
                color: active ? 'var(--brand)' : 'var(--text-faint)',
                boxShadow: active ? 'var(--shadow-sm)' : 'none',
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
