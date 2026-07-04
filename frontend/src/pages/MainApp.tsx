import { useCallback, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import Sidebar from '../components/app/Sidebar'
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

  // Resizable boundary between the chart (middle) and the chat panel (right).
  const [chatWidth, setChatWidth] = useState<number>(() => {
    const stored = Number(localStorage.getItem('chatWidth'))
    return stored > 0 ? stored : 480
  })

  useEffect(() => {
    localStorage.setItem('chatWidth', String(chatWidth))
  }, [chatWidth])

  const startResize = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    const onMove = (ev: PointerEvent) => {
      const fromRight = window.innerWidth - ev.clientX
      // Keep room for the sidebar (290) plus a usable chart area.
      const max = Math.max(380, window.innerWidth - 290 - 420)
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
  }, [])

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

  const showChat = chartLoaded && !chartLoading

  return (
    <div className="flex h-screen w-full overflow-hidden" style={{ background: 'var(--canvas)' }}>
      {/* Left — settings & inputs */}
      <Sidebar onLoadChart={loadChart} onClearConversation={clearConversation} />

      {/* Middle — chart */}
      <main className="relative flex min-w-0 flex-1 flex-col overflow-y-auto">
        <div
          className="pointer-events-none absolute inset-0 -z-0"
          style={{ background: 'var(--canvas-grad)' }}
        />
        <div className="relative w-full px-6 py-7">
          {!chartLoaded && !chartLoading && !chartError && <EmptyState />}
          {chartLoading && <LoadingState symbol={currentSymbol} />}
          {chartError && <ErrorState message={chartError} />}

          {showChat && (
            <div className="tm-fade-in">
              <PriceHeader />
              <CandlestickChart />
            </div>
          )}
        </div>
      </main>

      {/* Draggable boundary */}
      {showChat && (
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
          <span
            className="absolute inset-y-0 -left-1 -right-1 transition-colors group-hover:bg-[color:var(--brand-ring)]"
          />
          <span
            className="absolute left-1/2 top-1/2 flex h-9 w-1 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-0.5 rounded-full opacity-0 transition-opacity group-hover:opacity-100"
            style={{ background: 'var(--brand)' }}
          />
        </div>
      )}

      {/* Right — agent chat */}
      {showChat && (
        <aside
          className="tm-fade-in flex h-screen shrink-0 flex-col"
          style={{ width: chatWidth, background: 'var(--surface)' }}
        >
          <ChatSection />
        </aside>
      )}
    </div>
  )
}

function EmptyState() {
  const steps = [
    { icon: 'tag', text: 'Enter an asset symbol' },
    { icon: 'tune', text: 'Choose your indicators' },
    { icon: 'show_chart', text: 'Press Load Chart' },
  ]
  return (
    <div className="tm-reveal mx-auto mt-[12vh] max-w-md text-center">
      <div
        className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl"
        style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}
      >
        <span className="material-symbol" style={{ fontSize: 32 }}>
          insights
        </span>
      </div>
      <h2 className="font-display text-2xl font-bold" style={{ color: 'var(--text)' }}>
        Load a market to begin
      </h2>
      <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
        Configure your chart in the sidebar, then start a conversation with the agent.
      </p>
      <div className="mt-7 space-y-2.5 text-left">
        {steps.map((s, i) => (
          <div
            key={s.text}
            className="tm-card flex items-center gap-3 px-4 py-3"
          >
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold"
              style={{ background: 'var(--surface-3)', color: 'var(--brand)' }}
            >
              {i + 1}
            </span>
            <span className="material-symbol" style={{ fontSize: 18, color: 'var(--text-faint)' }}>
              {s.icon}
            </span>
            <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
              {s.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function LoadingState({ symbol }: { symbol: string }) {
  return (
    <div className="tm-fade-in">
      <div className="tm-card mb-4 flex items-center gap-3 px-5 py-4">
        <span className="material-symbol tm-spin" style={{ fontSize: 20, color: 'var(--brand)' }}>
          progress_activity
        </span>
        <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
          Loading data for <span className="font-mono font-semibold">{symbol}</span>…
        </span>
      </div>
      <div className="tm-card overflow-hidden p-0">
        <div className="tm-skeleton" style={{ height: 460 }} />
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div
      className="tm-reveal mx-auto mt-[10vh] max-w-xl rounded-2xl border px-6 py-5"
      style={{ background: 'var(--down-soft)', borderColor: 'var(--down)', color: 'var(--down)' }}
    >
      <div className="flex items-center gap-2">
        <span className="material-symbol" style={{ fontSize: 22 }}>
          error
        </span>
        <span className="font-display text-base font-bold">Couldn’t load chart</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
        {message}
      </p>
    </div>
  )
}
