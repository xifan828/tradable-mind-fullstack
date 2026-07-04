import { useAppStore } from '../../store/useAppStore'
import { PIVOT_COLORS_DARK, PIVOT_COLORS_LIGHT } from '../../theme/tokens'
import type { PivotLevels } from '../../types'

const PIVOT_ORDER: Array<{ key: keyof PivotLevels; label: string }> = [
  { key: 'R3', label: 'R3' },
  { key: 'R2', label: 'R2' },
  { key: 'R1', label: 'R1' },
  { key: 'Pivot', label: 'P' },
  { key: 'S1', label: 'S1' },
  { key: 'S2', label: 'S2' },
  { key: 'S3', label: 'S3' },
]

export default function PriceHeader() {
  const themeMode = useAppStore((s) => s.themeMode)
  const pivotColors = themeMode === 'light' ? PIVOT_COLORS_LIGHT : PIVOT_COLORS_DARK

  const chartData = useAppStore((s) => s.chartData)
  const currentSymbol = useAppStore((s) => s.currentSymbol)
  const currentInterval = useAppStore((s) => s.currentInterval)
  const pivotLevels = useAppStore((s) => s.pivotLevels)
  const dailyChange = useAppStore((s) => s.dailyChange)
  const indicators = useAppStore((s) => s.currentIndicators)

  if (!chartData || chartData.length === 0) return null

  const lastClose = chartData[chartData.length - 1].Close
  const decimals = lastClose < 100 ? 4 : 2
  const isPositive = (dailyChange?.change ?? 0) >= 0
  const changeColor = isPositive ? 'var(--up)' : 'var(--down)'
  const changeSoft = isPositive ? 'var(--up-soft)' : 'var(--down-soft)'

  return (
    <div className="tm-card mb-4 px-5 py-4">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            {currentSymbol}
          </span>
          <span
            className="rounded-md px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide"
            style={{ background: 'var(--surface-3)', color: 'var(--text-faint)' }}
          >
            {currentInterval}
          </span>
        </div>

        <span className="font-mono text-2xl font-semibold tabular-nums" style={{ color: 'var(--text)' }}>
          {lastClose.toFixed(decimals)}
        </span>

        {dailyChange && (
          <span
            className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-sm font-semibold tabular-nums"
            style={{ background: changeSoft, color: changeColor }}
          >
            <span className="material-symbol" style={{ fontSize: 16 }}>
              {isPositive ? 'trending_up' : 'trending_down'}
            </span>
            {isPositive ? '+' : '−'}
            {Math.abs(dailyChange.change).toFixed(decimals)} ({isPositive ? '+' : '−'}
            {Math.abs(dailyChange.changePct).toFixed(2)}%)
          </span>
        )}

        {indicators.pivot && pivotLevels && (
          <div className="flex flex-wrap items-center gap-1.5 lg:ml-auto">
            {PIVOT_ORDER.map(({ key, label }) => {
              const colors = pivotColors[key as string]
              const value = pivotLevels[key]
              return (
                <span key={key} className="tm-chip" style={{ background: colors.bg, color: colors.text }}>
                  <span style={{ opacity: 0.75 }}>{label}</span>
                  {value.toFixed(value < 100 ? 4 : 2)}
                </span>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
