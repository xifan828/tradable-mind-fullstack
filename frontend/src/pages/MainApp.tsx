import { useCallback, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import ChartToolbar from '../components/app/ChartToolbar'
import PriceHeader from '../components/app/PriceHeader'
import CandlestickChart from '../components/app/CandlestickChart'
import ChatSection from '../components/app/ChatSection'
import { useAppStore } from '../store/useAppStore'
import { fetchChartData } from '../lib/chartApi'

export default function MainApp() {
  const geminiApiKey = useAppStore((s) => s.geminiApiKey)
  const chartLoaded = useAppStore((s) => s.chartLoaded)
  const chartLoading = useAppStore((s) => s.chartLoading)
  const chartError = useAppStore((s) => s.chartError)
  const currentSymbol = useAppStore((s) => s.currentSymbol)

  // Resizable boundary between the chart (left) and the chat panel (right);
  // persisted with the rest of the preferences in the store.
  const chatWidth = useAppStore((s) => s.chatWidth)
  const setChatWidth = useAppStore((s) => s.setChatWidth)

  const startResize = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault()
      const onMove = (ev: PointerEvent) => {
        const fromRight = window.innerWidth - ev.clientX
        // Keep a usable chart column on the left.
        const max = Math.max(380, window.innerWidth - 560)
        setChatWidth(Math.min(Math.max(fromRight, 380), max))
      }
      const onUp = () => {
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('pointerup', onUp)
      }
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerup', onUp)
    },
    [setChatWidth],
  )

  const loadChart = useCallback(async () => {
    const store = useAppStore.getState()
    if (store.isStreaming) {
      store.setPendingLoadChart(true)
      return
    }
    store.setChartLoading(true)
    store.setChartError(null)
    try {
      const result = await fetchChartData({
        symbol: store.currentSymbol,
        interval: store.currentInterval,
        bars: store.currentBars,
        assetType: store.currentAssetType,
      })
      store.setChartData(result.data)
      store.setPivotLevels(result.pivotLevels ?? null)
      store.setDailyChange(result.dailyChange ?? null)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      store.setChartError(message)
      store.setChartData(null)
    } finally {
      store.setChartLoading(false)
    }
  }, [])

  const clearConversation = useCallback(() => {
    const store = useAppStore.getState()
    if (store.isStreaming) {
      store.setPendingClearConversation(true)
      return
    }
    store.resetConversation()
  }, [])

  useEffect(() => {
    function onLoadChartEvent() {
      loadChart()
    }
    window.addEventListener('tm:load-chart', onLoadChartEvent)
    return () => window.removeEventListener('tm:load-chart', onLoadChartEvent)
  }, [loadChart])

  if (!geminiApiKey) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="flex h-screen w-full overflow-hidden" style={{ background: 'var(--canvas)' }}>
      {/* Left column — toolbar over the full-height chart */}
      <div className="flex h-full min-w-0 flex-1 flex-col">
        <ChartToolbar onLoadChart={loadChart} />

        <main className="relative min-h-0 flex-1 p-3">
          {!chartLoaded && !chartLoading && !chartError && <EmptyState />}
          {chartLoading && <LoadingState symbol={currentSymbol} />}
          {chartError && !chartLoading && <ErrorState message={chartError} />}

          {chartLoaded && !chartLoading && !chartError && (
            <div className="tm-fade-in flex h-full min-h-0 flex-col">
              <PriceHeader />
              <div className="min-h-0 flex-1">
                <CandlestickChart />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Draggable boundary */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize chat panel"
        onPointerDown={startResize}
        onDoubleClick={() => setChatWidth(480)}
        title="Drag to resize · double-click to reset"
        className="group relative w-1.5 shrink-0 cursor-col-resize"
        style={{ background: 'var(--border)' }}
      >
        <span className="absolute inset-y-0 -left-1 -right-1 transition-colors group-hover:bg-[color:var(--brand-ring)]" />
        <span
          className="absolute left-1/2 top-1/2 flex h-9 w-1 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-0.5 rounded-full opacity-0 transition-opacity group-hover:opacity-100"
          style={{ background: 'var(--brand)' }}
        />
      </div>

      {/* Right — agent chat, always visible */}
      <aside
        className="flex h-screen shrink-0 flex-col"
        style={{ width: chatWidth, background: 'var(--surface)' }}
      >
        <ChatSection onClearConversation={clearConversation} />
      </aside>
    </div>
  )
}

function EmptyState() {
  const steps = [
    { num: '01', text: 'Pick an asset and symbol in the toolbar above' },
    { num: '02', text: 'Choose interval, bars and indicators' },
    { num: '03', text: 'Press Load — then brief the agent' },
  ]
  return (
    <div
      className="tm-reveal flex h-full flex-col items-center justify-center border border-dashed px-6"
      style={{ borderColor: 'var(--border-strong)', borderRadius: 'var(--radius-lg)' }}
    >
      <div className="w-full max-w-md">
        <div className="flex justify-center">
          <span
            className="inline-flex h-12 w-12 items-center justify-center"
            style={{
              background: 'var(--brand-soft)',
              color: 'var(--brand)',
              borderRadius: 'var(--radius-lg)',
            }}
            aria-hidden
          >
            <span className="material-symbol" style={{ fontSize: 24 }}>
              candlestick_chart
            </span>
          </span>
        </div>
        <h2
          className="font-display mt-4 text-center text-3xl"
          style={{ fontWeight: 600, color: 'var(--text)' }}
        >
          Load a market to begin
        </h2>
        <p className="mt-2 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          The chart renders here; your AI analyst is ready on the right.
        </p>
        <div className="mt-8 space-y-2">
          {steps.map((s) => (
            <div
              key={s.num}
              className="flex items-center gap-4 border px-4 py-3"
              style={{
                borderColor: 'var(--border)',
                background: 'var(--surface)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <span
                className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-[0.68rem] font-semibold"
                style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}
              >
                {s.num}
              </span>
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {s.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function LoadingState({ symbol }: { symbol: string }) {
  return (
    <div className="tm-fade-in flex h-full min-h-0 flex-col">
      <div
        className="mb-2.5 flex shrink-0 items-center gap-3 border-b pb-2.5"
        style={{ borderColor: 'var(--border)' }}
      >
        <span className="material-symbol tm-spin" style={{ fontSize: 18, color: 'var(--brand)' }}>
          progress_activity
        </span>
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Loading <span className="font-mono font-semibold" style={{ color: 'var(--text)' }}>{symbol}</span>…
        </span>
      </div>
      <div
        className="tm-skeleton min-h-0 flex-1 border"
        style={{ borderColor: 'var(--border)', borderRadius: 'var(--radius-lg)' }}
      />
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <div
        className="tm-reveal flex w-full max-w-xl items-start gap-3.5 px-6 py-5"
        style={{ background: 'var(--down-soft)', borderRadius: 'var(--radius-lg)' }}
      >
        <span className="material-symbol mt-0.5 shrink-0" style={{ fontSize: 20, color: 'var(--down)' }}>
          error
        </span>
        <div>
          <p className="font-display text-lg" style={{ fontWeight: 600, color: 'var(--text)' }}>
            Couldn’t load the chart
          </p>
          <p className="mt-1.5 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            {message}
          </p>
        </div>
      </div>
    </div>
  )
}
