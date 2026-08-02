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
import { getChartColors } from '../../theme/chartTheme'
import type { OHLCRow } from '../../types'

// Pane proportions: the price pane vs. each indicator sub-pane.
const MAIN_PANE_STRETCH = 100
const SUB_PANE_STRETCH = 28

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
  const hasVolume = !!chartData?.some((r) => r.Volume !== undefined && r.Volume !== null)

  useEffect(() => {
    const container = containerRef.current
    if (!container || !chartData || chartData.length === 0) return

    // Read the chart palette from the active theme's CSS vars.
    const colors = getChartColors()
    const intraday = !['1day', '1week', '1month'].includes(interval)

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: colors.bg },
        textColor: colors.text,
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: 11,
        attributionLogo: false,
        panes: {
          separatorColor: colors.separator,
          separatorHoverColor: colors.ref,
          enableResize: true,
        },
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: colors.separator },
      timeScale: {
        borderColor: colors.separator,
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
        upColor: colors.candle_up,
        downColor: colors.candle_down,
        wickUpColor: colors.candle_up,
        wickDownColor: colors.candle_down,
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

    if (indicators.ema_10) overlay(colors.ema_10, 1, 'EMA10')
    if (indicators.ema_20) overlay(colors.ema_20, 1, 'EMA20')
    if (indicators.ema_50) overlay(colors.ema_50, 2, 'EMA50')
    if (indicators.ema_100) overlay(colors.ema_100, 2, 'EMA100')

    if (indicators.bb && chartData.some((r) => r.BB_Upper !== undefined)) {
      overlay(colors.bb_band, 1, 'BB_Upper', true)
      overlay(colors.bb_band, 1, 'BB_Lower', true)
      overlay(colors.bb_middle, 1, 'BB_Middle')
    }

    // --- Sub-panes ---
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
          color: r.Close >= r.Open ? colors.volume_up : colors.volume_down,
        })),
      )
      pane += 1
    }

    if (indicators.rsi) {
      const rsi = chart.addSeries(
        LineSeries,
        { color: colors.rsi, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      rsi.setData(lineData(chartData, 'RSI14'))
      refLine(rsi, 70, colors.rsi_overbought)
      refLine(rsi, 30, colors.rsi_oversold)
      refLine(rsi, 50, colors.ref, LineStyle.Dotted)
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
          color: (r.MACD_Diff ?? 0) >= 0 ? colors.macd_hist_pos : colors.macd_hist_neg,
        })),
      )
      const macd = chart.addSeries(
        LineSeries,
        { color: colors.macd_line, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      macd.setData(lineData(chartData, 'MACD'))
      const signal = chart.addSeries(
        LineSeries,
        { color: colors.macd_signal, lineWidth: 1, priceLineVisible: false, lastValueVisible: false },
        pane,
      )
      signal.setData(lineData(chartData, 'MACD_Signal'))
      refLine(macd, 0, colors.ref, LineStyle.Dotted)
      pane += 1
    }

    if (indicators.atr) {
      const atr = chart.addSeries(
        AreaSeries,
        {
          lineColor: colors.atr,
          topColor: colors.atr_fill,
          bottomColor: 'transparent',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        pane,
      )
      atr.setData(lineData(chartData, 'ATR'))
    }

    // Proportional pane sizing: the chart fills its flex container (autoSize)
    // and stretch factors split that height between price and indicator panes.
    chart.panes().forEach((p, i) => {
      p.setStretchFactor(i === 0 ? MAIN_PANE_STRETCH : SUB_PANE_STRETCH)
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
    <div
      className="relative h-full w-full overflow-hidden border"
      style={{
        borderColor: 'var(--border)',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--chart-bg)',
      }}
    >
      <button
        type="button"
        onClick={resetView}
        title="Reset view"
        aria-label="Reset chart view"
        className="tm-focus absolute right-3 top-3 z-10 inline-flex items-center gap-1.5 border px-2.5 py-1.5 font-mono text-[0.68rem] font-semibold uppercase tracking-[0.08em] backdrop-blur transition-colors"
        style={{
          background: 'color-mix(in srgb, var(--surface) 82%, transparent)',
          borderColor: 'var(--border)',
          borderRadius: 'var(--radius-xs)',
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
        <span className="material-symbol" style={{ fontSize: 15 }}>
          restart_alt
        </span>
        Reset view
      </button>
      <div ref={containerRef} className="h-full w-full" />
    </div>
  )
}
