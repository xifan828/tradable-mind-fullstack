import { useState, type ReactNode } from 'react'
import { useAppStore } from '../../store/useAppStore'
import Wordmark from '../common/Wordmark'
import ThemeToggle from '../common/ThemeToggle'
import type { AssetType, IndicatorSettings } from '../../types'

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

interface SidebarProps {
  onLoadChart: () => void
  onClearConversation: () => void
}

export default function Sidebar({ onLoadChart, onClearConversation }: SidebarProps) {
  const isStreaming = useAppStore((s) => s.isStreaming)
  const currentAssetType = useAppStore((s) => s.currentAssetType)
  const setCurrentAssetType = useAppStore((s) => s.setCurrentAssetType)
  const currentSymbol = useAppStore((s) => s.currentSymbol)
  const setCurrentSymbol = useAppStore((s) => s.setCurrentSymbol)
  const currentInterval = useAppStore((s) => s.currentInterval)
  const setCurrentInterval = useAppStore((s) => s.setCurrentInterval)
  const currentBars = useAppStore((s) => s.currentBars)
  const setCurrentBars = useAppStore((s) => s.setCurrentBars)
  const currentIndicators = useAppStore((s) => s.currentIndicators)
  const setCurrentIndicators = useAppStore((s) => s.setCurrentIndicators)

  const [symbolInput, setSymbolInput] = useState(currentSymbol)

  function updateIndicator(key: keyof IndicatorSettings, value: boolean) {
    setCurrentIndicators({ ...currentIndicators, [key]: value })
  }

  function handleLoadChart() {
    setCurrentSymbol(symbolInput.trim().toUpperCase())
    onLoadChart()
  }

  return (
    <aside
      className="flex h-screen w-[290px] shrink-0 flex-col border-r"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between border-b px-5 py-4"
        style={{ borderColor: 'var(--border)' }}
      >
        <div>
          <Wordmark size={24} />
          <p className="mt-1.5 pl-[34px] text-[0.72rem]" style={{ color: 'var(--text-faint)' }}>
            AI-Powered Market Analysis
          </p>
        </div>
        <ThemeToggle />
      </div>

      {/* Scroll body */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {isStreaming && (
          <div
            className="tm-fade-in mb-5 flex items-center gap-2 rounded-[10px] border px-3 py-2.5 text-xs font-medium"
            style={{ background: 'var(--warn-soft)', borderColor: 'var(--warn-border)', color: 'var(--warn)' }}
          >
            <span className="material-symbol tm-spin" style={{ fontSize: 16 }}>
              progress_activity
            </span>
            Agent working — controls disabled
          </div>
        )}

        {/* Chart Settings */}
        <SectionLabel icon="candlestick_chart">Chart Settings</SectionLabel>

        <div className="space-y-3.5">
          <Field label="Asset Type">
            <select
              className="tm-input"
              value={currentAssetType}
              disabled={isStreaming}
              onChange={(e) => setCurrentAssetType(e.target.value as AssetType)}
            >
              {ASSET_TYPES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Asset Symbol">
            <input
              type="text"
              className="tm-input font-mono"
              placeholder={SYMBOL_PLACEHOLDERS[currentAssetType]}
              value={symbolInput}
              disabled={isStreaming}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isStreaming) handleLoadChart()
              }}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Interval">
              <select
                className="tm-input"
                value={currentInterval}
                disabled={isStreaming}
                onChange={(e) => setCurrentInterval(e.target.value)}
              >
                {INTERVALS.map((iv) => (
                  <option key={iv} value={iv}>
                    {iv}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Bars">
              <input
                type="number"
                min={50}
                max={300}
                step={10}
                className="tm-input font-mono"
                value={currentBars}
                disabled={isStreaming}
                onChange={(e) => setCurrentBars(Number(e.target.value))}
              />
            </Field>
          </div>
        </div>

        <Divider />

        {/* Overlay indicators */}
        <SectionLabel icon="ssid_chart">Overlay Indicators</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <ChipToggle label="EMA 10" dot="#2196F3" checked={currentIndicators.ema_10} disabled={isStreaming} onChange={(v) => updateIndicator('ema_10', v)} />
          <ChipToggle label="EMA 20" dot="#FF9800" checked={currentIndicators.ema_20} disabled={isStreaming} onChange={(v) => updateIndicator('ema_20', v)} />
          <ChipToggle label="EMA 50" dot="#9C27B0" checked={currentIndicators.ema_50} disabled={isStreaming} onChange={(v) => updateIndicator('ema_50', v)} />
          <ChipToggle label="EMA 100" dot="#E91E63" checked={currentIndicators.ema_100} disabled={isStreaming} onChange={(v) => updateIndicator('ema_100', v)} />
        </div>
        <div className="mt-2">
          <ChipToggle label="Bollinger Bands" dot="#607D8B" checked={currentIndicators.bb} disabled={isStreaming} onChange={(v) => updateIndicator('bb', v)} full />
        </div>

        <Divider />

        {/* Subplot indicators */}
        <SectionLabel icon="monitoring">Subplot Indicators</SectionLabel>
        <div className="grid grid-cols-3 gap-2">
          <ChipToggle label="RSI" checked={currentIndicators.rsi} disabled={isStreaming} onChange={(v) => updateIndicator('rsi', v)} center />
          <ChipToggle label="MACD" checked={currentIndicators.macd} disabled={isStreaming} onChange={(v) => updateIndicator('macd', v)} center />
          <ChipToggle label="ATR" checked={currentIndicators.atr} disabled={isStreaming} onChange={(v) => updateIndicator('atr', v)} center />
        </div>

        <Divider />

        {/* Price levels */}
        <SectionLabel icon="horizontal_rule">Price Levels</SectionLabel>
        <ChipToggle label="Pivot Points" checked={currentIndicators.pivot} disabled={isStreaming} onChange={(v) => updateIndicator('pivot', v)} full />
      </div>

      {/* Footer actions */}
      <div className="flex flex-col gap-2.5 border-t px-5 py-4" style={{ borderColor: 'var(--border)' }}>
        <button onClick={handleLoadChart} disabled={isStreaming} className="tm-btn tm-btn-primary w-full">
          <span className="material-symbol" style={{ fontSize: 18 }}>
            show_chart
          </span>
          Load Chart
        </button>
        <button onClick={onClearConversation} className="tm-btn tm-btn-ghost w-full">
          <span className="material-symbol" style={{ fontSize: 18 }}>
            restart_alt
          </span>
          Clear Conversation
        </button>
      </div>
    </aside>
  )
}

function SectionLabel({ icon, children }: { icon: string; children: ReactNode }) {
  return (
    <div className="mb-3 flex items-center gap-1.5">
      <span className="material-symbol" style={{ fontSize: 16, color: 'var(--brand)' }}>
        {icon}
      </span>
      <h2 className="text-[0.74rem] font-bold uppercase tracking-[0.06em]" style={{ color: 'var(--text-muted)' }}>
        {children}
      </h2>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="tm-field-label mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function Divider() {
  return <div className="my-5 h-px" style={{ background: 'var(--border)' }} />
}

function ChipToggle({
  label,
  checked,
  disabled,
  onChange,
  dot,
  full,
  center,
}: {
  label: string
  checked: boolean
  disabled: boolean
  onChange: (v: boolean) => void
  dot?: string
  full?: boolean
  center?: boolean
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      aria-pressed={checked}
      onClick={() => onChange(!checked)}
      className={`tm-focus flex items-center gap-1.5 rounded-[9px] border px-2.5 py-2 text-[0.8rem] font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
        full ? 'w-full' : ''
      } ${center ? 'justify-center' : ''}`}
      style={{
        background: checked ? 'var(--brand-soft)' : 'var(--surface-2)',
        borderColor: checked ? 'var(--brand-ring)' : 'var(--border)',
        color: checked ? 'var(--brand)' : 'var(--text-muted)',
      }}
    >
      {dot && (
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: dot, opacity: checked ? 1 : 0.45 }}
        />
      )}
      <span className="truncate">{label}</span>
    </button>
  )
}
