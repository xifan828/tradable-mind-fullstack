import { useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  AreaSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useAppStore } from '../../store/useAppStore'
import { CHART_COLORS } from '../../theme/tokens'
import type { OHLCRow } from '../../types'

const SUB_PANE_HEIGHT = 170
const MAIN_PANE_HEIGHT = 550

function toTime(dateStr: string): UTCTimestamp {
  return Math.floor(new Date(dateStr).getTime() / 1000) as UTCTimestamp
}

/** Build {time, value} points for an indicator column, skipping missing values. */
function lineData(rows: OHLCRow[], key: keyof OHLCRow) {
  const out: { time: UTCTimestamp; value: number }[] = []
  for (const r of rows) {
    const v = r[key]
    if (v !== undefined && v !== null) out.push({ time: toTime(r.Date), value: v as number })
  }
  return out
}

export default function CandlestickChart() {
  const themeMode = useAppStore((s) => s.themeMode)
  const chartData = useAppStore((s) => s.chartData)
  const indicators = useAppStore((s) => s.currentIndicators)
  const interval = useAppStore((s) => s.currentInterval)

  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)

  const isDark = themeMode === 'dark'

  // Count the indicator sub-panes so the container can be sized before render.
  const hasVolume = !!chartData?.some((r) => r.Volume !== undefined && r.Volume !== null)
  const subPanes = [
    hasVolume && indicators.volume,
    indicators.rsi,
    indicators.macd,
    indicators.atr,
  ].filter(Boolean).length
  const totalHeight = MAIN_PANE_HEIGHT + subPanes * SUB_PANE_HEIGHT

  useEffect(() => {
    const container = containerRef.current
    if (!container || !chartData || chartData.length === 0) return

    const gridColor = isDark ? '#202632' : '#eef0f5'
    const intraday = !['1day', '1week', '1month'].includes(interval)

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: isDark ? '#12151c' : '#ffffff' },
        textColor: isDark ? '#9aa3b3' : '#586071',
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: gridColor },
      timeScale: {
        borderColor: gridColor,
        timeVisible: intraday,
        secondsVisible: false,
        rightOffset: 4,
      },
    })
    chartRef.current = chart

    const lastClose = chartData[chartData.length - 1].Close
    const precision = lastClose < 1 ? 5 : lastClose < 100 ? 4 : 2

    // --- Main pane: candlesticks ---
    const candles = chart.addSeries(
      CandlestickSeries,
      {
        upColor: CHART_COLORS.candle_up,
        downColor: CHART_COLORS.candle_down,
        wickUpColor: CHART_COLORS.candle_up,
        wickDownColor: CHART_COLORS.candle_down,
        borderVisible: false,
        priceFormat: { type: 'price', precision, minMove: 1 / 10 ** precision },
      },
      0,
    )
    candles.setData(
      chartData.map((r) => ({
        time: toTime(r.Date),
        open: r.Open,
        high: r.High,
        low: r.Low,
        close: r.Close,
      })),
    )

    const overlay = (color: string, width: 1 | 2, key: keyof OHLCRow, dashed = false) => {
      const s = chart.addSeries(
        LineSeries,
        {
          color,
          lineWidth: width,
          lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        },
        0,
      )
      s.setData(lineData(chartData, key))
      return s
    }

    if (indicators.ema_10) overlay(CHART_COLORS.ema_10, 1, 'EMA10')
    if (indicators.ema_20) overlay(CHART_COLORS.ema_20, 1, 'EMA20')
    if (indicators.ema_50) overlay(CHART_COLORS.ema_50, 2, 'EMA50')
    if (indicators.ema_100) overlay(CHART_COLORS.ema_100, 2, 'EMA100')

    if (indicators.bb && chartData.some((r) => r.BB_Upper !== undefined)) {
      overlay(CHART_COLORS.bb_band, 1, 'BB_Upper', true)
      overlay(CHART_COLORS.bb_band, 1, 'BB_Lower', true)
      overlay(CHART_COLORS.bb_middle, 1, 'BB_Middle')
    }

    // --- Sub-panes ---
    const subPaneIndices: number[] = []
    let pane = 1
    const refLine = (
      series: ISeriesApi<'Line'>,
      price: number,
      color: string,
      style: LineStyle = LineStyle.Dashed,
    ) =>
      series.createPriceLine({
        price,
        color,
        lineWidth: 1,
        lineStyle: style,
        axisLabelVisible: false,
      })

    if (hasVolume && indicators.volume) {
      const vol = chart.addSeries(
        HistogramSeries,
        { priceFormat: { type: 'volume' }, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      vol.setData(
        chartData.map((r) => ({
          time: toTime(r.Date),
          value: r.Volume ?? 0,
          color: r.Close >= r.Open ? CHART_COLORS.volume_up : CHART_COLORS.volume_down,
        })),
      )
      subPaneIndices.push(pane)
      pane += 1
    }

    if (indicators.rsi) {
      const rsi = chart.addSeries(
        LineSeries,
        { color: CHART_COLORS.rsi, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      rsi.setData(lineData(chartData, 'RSI14'))
      refLine(rsi, 70, CHART_COLORS.rsi_overbought)
      refLine(rsi, 30, CHART_COLORS.rsi_oversold)
      refLine(rsi, 50, '#9e9e9e', LineStyle.Dotted)
      subPaneIndices.push(pane)
      pane += 1
    }

    if (indicators.macd) {
      const hist = chart.addSeries(
        HistogramSeries,
        { priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      hist.setData(
        chartData.map((r) => ({
          time: toTime(r.Date),
          value: r.MACD_Diff ?? 0,
          color: (r.MACD_Diff ?? 0) >= 0 ? CHART_COLORS.macd_hist_pos : CHART_COLORS.macd_hist_neg,
        })),
      )
      const macd = chart.addSeries(
        LineSeries,
        { color: CHART_COLORS.macd_line, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      macd.setData(lineData(chartData, 'MACD'))
      const signal = chart.addSeries(
        LineSeries,
        { color: CHART_COLORS.macd_signal, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      signal.setData(lineData(chartData, 'MACD_Signal'))
      refLine(macd, 0, '#9e9e9e', LineStyle.Dotted)
      subPaneIndices.push(pane)
      pane += 1
    }

    if (indicators.atr) {
      const atr = chart.addSeries(
        AreaSeries,
        {
          lineColor: CHART_COLORS.atr,
          topColor: isDark ? 'rgba(41, 182, 246, 0.4)' : 'rgba(41, 182, 246, 0.3)',
          bottomColor: 'rgba(41, 182, 246, 0.02)',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        pane,
      )
      atr.setData(lineData(chartData, 'ATR'))
      subPaneIndices.push(pane)
    }

    // Size panes by stretch factor so the main pane and each indicator sub-pane
    // keep a stable proportion (setHeight gets redistributed and squashes subs).
    // Container height equals MAIN + n·SUB, so factors map 1:1 to pixels.
    void subPaneIndices
    const panes = chart.panes()
    panes.forEach((p, i) => {
      p.setStretchFactor(i === 0 ? MAIN_PANE_HEIGHT : SUB_PANE_HEIGHT)
    })

    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
  }, [chartData, indicators, interval, isDark, hasVolume])

  function resetView() {
    const chart = chartRef.current
    if (!chart) return
    chart.timeScale().resetTimeScale()
    chart.timeScale().fitContent()
    chart.priceScale('right').applyOptions({ autoScale: true })
  }

  if (!chartData || chartData.length === 0) return null

  return (
    <div className="tm-card relative w-full overflow-hidden p-0">
      <button
        type="button"
        onClick={resetView}
        title="Reset view"
        aria-label="Reset chart view"
        className="tm-focus absolute right-3 top-3 z-10 inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold backdrop-blur transition-colors"
        style={{
          background: 'color-mix(in srgb, var(--surface) 78%, transparent)',
          borderColor: 'var(--border)',
          color: 'var(--text-muted)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'var(--brand-ring)'
          e.currentTarget.style.color = 'var(--brand)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'var(--border)'
          e.currentTarget.style.color = 'var(--text-muted)'
        }}
      >
        <span className="material-symbol" style={{ fontSize: 16 }}>
          restart_alt
        </span>
        Reset view
      </button>
      <div ref={containerRef} style={{ width: '100%', height: totalHeight }} />
    </div>
  )
}
