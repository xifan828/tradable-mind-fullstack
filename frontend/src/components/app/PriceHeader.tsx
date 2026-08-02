import { useAppStore } from '../../store/useAppStore'
import { pivotTone } from '../../theme/chartTheme'
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

/** Summary strip above the chart: symbol, interval, last price, change, pivots. */
export default function PriceHeader() {
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

  return (
    <div
      className="mb-2.5 flex shrink-0 flex-wrap items-baseline gap-x-4 gap-y-2 border-b pb-2.5"
      style={{ borderColor: 'var(--border)' }}
    >
      <span
        className="font-display text-xl leading-none"
        style={{ fontWeight: 650, color: 'var(--text)' }}
      >
        {currentSymbol}
      </span>

      <span className="tm-kicker">{currentInterval}</span>

      <span
        className="font-mono text-xl font-semibold leading-none tabular-nums"
        style={{ color: 'var(--text)' }}
      >
        {lastClose.toFixed(decimals)}
      </span>

      {dailyChange && (
        <span
          className="inline-flex items-center gap-1 font-mono text-sm font-semibold tabular-nums"
          style={{ color: changeColor }}
        >
          <span className="material-symbol" style={{ fontSize: 15 }}>
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
            const tone = pivotTone(key as string)
            const value = pivotLevels[key]
            return (
              <span key={key} className="tm-chip" style={{ background: tone.bg, color: tone.text }}>
                <span style={{ opacity: 0.75 }}>{label}</span>
                {value.toFixed(value < 100 ? 4 : 2)}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
