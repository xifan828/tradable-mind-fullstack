import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useAppStore } from '../../store/useAppStore'
import type { IndicatorSettings } from '../../types'

const EMA_ROWS: Array<{ key: keyof IndicatorSettings; label: string; dotVar: string }> = [
  { key: 'ema_10', label: 'EMA 10', dotVar: 'var(--chart-ema-10)' },
  { key: 'ema_20', label: 'EMA 20', dotVar: 'var(--chart-ema-20)' },
  { key: 'ema_50', label: 'EMA 50', dotVar: 'var(--chart-ema-50)' },
  { key: 'ema_100', label: 'EMA 100', dotVar: 'var(--chart-ema-100)' },
]

/** Number of active indicators, shown as a badge on the trigger. */
function activeCount(ind: IndicatorSettings): number {
  return Object.values(ind).filter(Boolean).length
}

export default function IndicatorsPopover() {
  const isStreaming = useAppStore((s) => s.isStreaming)
  const currentIndicators = useAppStore((s) => s.currentIndicators)
  const setCurrentIndicators = useAppStore((s) => s.setCurrentIndicators)

  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function onPointerDown(e: PointerEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  function toggle(key: keyof IndicatorSettings) {
    setCurrentIndicators({ ...currentIndicators, [key]: !currentIndicators[key] })
  }

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="true"
        className="tm-btn tm-btn-ghost !gap-1.5 !px-3 !py-2 text-[0.8rem]"
      >
        <span className="material-symbol" style={{ fontSize: 17 }}>
          tune
        </span>
        Indicators
        <span
          className="ml-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-[var(--radius-xs)] px-1 font-mono text-[0.66rem] font-semibold"
          style={{ background: 'var(--surface-3)', color: 'var(--text-muted)' }}
        >
          {activeCount(currentIndicators)}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          className="tm-fade-in absolute left-0 top-[calc(100%+6px)] z-50 w-60 border px-4 pb-3 pt-2"
          style={{
            background: 'var(--surface)',
            borderColor: 'var(--border-strong)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <Section title="Overlays">
            {EMA_ROWS.map((row) => (
              <ToggleRow
                key={row.key}
                label={row.label}
                checked={currentIndicators[row.key]}
                disabled={isStreaming}
                dot={row.dotVar}
                onToggle={() => toggle(row.key)}
              />
            ))}
            <ToggleRow
              label="Bollinger Bands"
              checked={currentIndicators.bb}
              disabled={isStreaming}
              dot="var(--chart-bb)"
              onToggle={() => toggle('bb')}
            />
          </Section>

          <Section title="Subplots">
            <ToggleRow label="RSI" checked={currentIndicators.rsi} disabled={isStreaming} onToggle={() => toggle('rsi')} />
            <ToggleRow label="MACD" checked={currentIndicators.macd} disabled={isStreaming} onToggle={() => toggle('macd')} />
            <ToggleRow label="ATR" checked={currentIndicators.atr} disabled={isStreaming} onToggle={() => toggle('atr')} />
            <ToggleRow label="Volume" checked={currentIndicators.volume} disabled={isStreaming} onToggle={() => toggle('volume')} />
          </Section>

          <Section title="Levels" last>
            <ToggleRow label="Pivot Points" checked={currentIndicators.pivot} disabled={isStreaming} onToggle={() => toggle('pivot')} />
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ title, children, last }: { title: string; children: ReactNode; last?: boolean }) {
  return (
    <div className={last ? '' : 'mb-1'}>
      <div
        className="tm-kicker mt-2 border-b pb-1.5"
        style={{ borderColor: 'var(--border)' }}
      >
        {title}
      </div>
      <div className="py-1">{children}</div>
    </div>
  )
}

function ToggleRow({
  label,
  checked,
  disabled,
  dot,
  onToggle,
}: {
  label: string
  checked: boolean
  disabled: boolean
  dot?: string
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={checked}
      disabled={disabled}
      onClick={onToggle}
      className="tm-focus flex w-full items-center gap-2 rounded-[var(--radius-xs)] px-1 py-1.5 text-left text-[0.82rem] transition-colors hover:bg-[color:var(--surface-2)] disabled:cursor-not-allowed disabled:opacity-50"
      style={{ color: checked ? 'var(--text)' : 'var(--text-muted)' }}
    >
      {dot && (
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: dot, opacity: checked ? 1 : 0.35 }}
        />
      )}
      <span className="flex-1 truncate font-medium">{label}</span>
      <span
        className="material-symbol"
        style={{ fontSize: 16, color: checked ? 'var(--brand)' : 'var(--border-strong)' }}
      >
        {checked ? 'check_box' : 'check_box_outline_blank'}
      </span>
    </button>
  )
}
