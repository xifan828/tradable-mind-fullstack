import { useState } from 'react'
import { useAppStore } from '../../store/useAppStore'
import Wordmark from '../common/Wordmark'
import ThemeToggle from '../common/ThemeToggle'
import IndicatorsPopover from './IndicatorsPopover'
import type { AssetType } from '../../types'

const SYMBOL_PLACEHOLDERS: Record<AssetType, string> = {
  forex: 'e.g., EUR/USD, GBP/USD',
  commodity: 'e.g., XAU/USD, XAG/USD',
  crypto: 'e.g., BTC/USD, ETH/USD',
  stock: 'e.g., AAPL, MSFT, GOOGL',
}

const ASSET_TYPES: { value: AssetType; label: string }[] = [
  { value: 'forex', label: 'Forex' },
  { value: 'commodity', label: 'Commodity' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'stock', label: 'Stock' },
]

const INTERVALS = ['5min', '15min', '30min', '1h', '4h', '1day', '1week']

interface ChartToolbarProps {
  onLoadChart: () => void
}

/**
 * Top toolbar: brand + every chart control in one row.
 * Replaces the old fixed sidebar so the chart owns the full height below.
 */
export default function ChartToolbar({ onLoadChart }: ChartToolbarProps) {
  const isStreaming = useAppStore((s) => s.isStreaming)
  const currentAssetType = useAppStore((s) => s.currentAssetType)
  const setCurrentAssetType = useAppStore((s) => s.setCurrentAssetType)
  const currentSymbol = useAppStore((s) => s.currentSymbol)
  const setCurrentSymbol = useAppStore((s) => s.setCurrentSymbol)
  const currentInterval = useAppStore((s) => s.currentInterval)
  const setCurrentInterval = useAppStore((s) => s.setCurrentInterval)
  const currentBars = useAppStore((s) => s.currentBars)
  const setCurrentBars = useAppStore((s) => s.setCurrentBars)

  const [symbolInput, setSymbolInput] = useState(currentSymbol)

  function handleLoadChart() {
    setCurrentSymbol(symbolInput.trim().toUpperCase())
    onLoadChart()
  }

  return (
    <header
      className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b px-4 py-2.5"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      <span className="mr-2 hidden min-[1600px]:block">
        <Wordmark size={22} />
      </span>
      <span className="mr-1 min-[1600px]:hidden">
        <Wordmark size={22} showText={false} />
      </span>

      <span className="hidden h-6 w-px xl:block" style={{ background: 'var(--border)' }} />

      <select
        className="tm-input !w-auto !py-2 text-[0.82rem]"
        value={currentAssetType}
        disabled={isStreaming}
        aria-label="Asset type"
        title="Asset type"
        onChange={(e) => setCurrentAssetType(e.target.value as AssetType)}
      >
        {ASSET_TYPES.map((a) => (
          <option key={a.value} value={a.value}>
            {a.label}
          </option>
        ))}
      </select>

      <input
        type="text"
        className="tm-input !w-40 !py-2 font-mono text-[0.82rem] uppercase"
        placeholder={SYMBOL_PLACEHOLDERS[currentAssetType]}
        value={symbolInput}
        disabled={isStreaming}
        aria-label="Asset symbol"
        title="Asset symbol"
        onChange={(e) => setSymbolInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !isStreaming) handleLoadChart()
        }}
      />

      <select
        className="tm-input !w-auto !py-2 font-mono text-[0.82rem]"
        value={currentInterval}
        disabled={isStreaming}
        aria-label="Interval"
        title="Interval"
        onChange={(e) => setCurrentInterval(e.target.value)}
      >
        {INTERVALS.map((iv) => (
          <option key={iv} value={iv}>
            {iv}
          </option>
        ))}
      </select>

      <input
        type="number"
        min={50}
        max={300}
        step={10}
        className="tm-input !w-[4.75rem] !py-2 font-mono text-[0.82rem]"
        value={currentBars}
        disabled={isStreaming}
        aria-label="Number of bars"
        title="Number of bars"
        onChange={(e) => setCurrentBars(Number(e.target.value))}
      />

      <IndicatorsPopover />

      <button
        onClick={handleLoadChart}
        disabled={isStreaming}
        className="tm-btn tm-btn-primary !px-3.5 !py-2 text-[0.82rem]"
      >
        <span className="material-symbol" style={{ fontSize: 17 }}>
          show_chart
        </span>
        Load
      </button>

      <div className="ml-auto flex items-center gap-3">
        {isStreaming && (
          <span
            className="tm-fade-in inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[0.68rem] font-semibold uppercase tracking-[0.08em]"
            style={{
              background: 'var(--accent-2-soft)',
              borderColor: 'var(--accent-2)',
              color: 'var(--accent-2)',
              borderRadius: 'var(--radius-pill)',
            }}
          >
            <span className="material-symbol tm-spin" style={{ fontSize: 13 }}>
              progress_activity
            </span>
            Agent working
          </span>
        )}
        <ThemeToggle />
      </div>
    </header>
  )
}
