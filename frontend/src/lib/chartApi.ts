import type { AssetType, DailyChange, OHLCRow, PivotLevels } from '../types'
import { API_BASE } from './apiBase'

// Backend exposes the technical API (see backend/src/agent/app.py) on API_BASE —
// same origin the agent stream client talks to.

interface ChartResponse {
  data: OHLCRow[]
  pivotLevels?: PivotLevels
  dailyChange?: DailyChange
}

interface TimeSeriesResponse {
  symbol: string
  interval: string
  asset_type: string | null
  data: Array<Record<string, unknown>>
}

interface PivotLevelsResponse {
  symbol: string
  interval: string
  pivot_levels: PivotLevels
}

/** Derive change vs. the previous bar's close from the OHLC series. */
function computeDailyChange(rows: OHLCRow[]): DailyChange | undefined {
  if (rows.length < 2) return undefined
  const last = rows[rows.length - 1].Close
  const prev = rows[rows.length - 2].Close
  const change = last - prev
  const changePct = prev !== 0 ? (change / prev) * 100 : 0
  return { change, changePct }
}

async function fetchTimeSeries(params: {
  symbol: string
  interval: string
  assetType: AssetType
}): Promise<OHLCRow[]> {
  const url = new URL('/api/time-series', API_BASE)
  url.searchParams.set('symbol', params.symbol)
  url.searchParams.set('interval', params.interval)
  url.searchParams.set('asset_type', params.assetType)

  const res = await fetch(url.toString())
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Failed to load time series (${res.status})`)
  }
  const body = (await res.json()) as TimeSeriesResponse
  // Backend record field names already match OHLCRow (Date, Open, EMA20, BB_Upper, ...).
  // DateLabel is derived in the chart component, so cast the raw records through.
  return (body.data ?? []) as unknown as OHLCRow[]
}

async function fetchPivotLevels(params: {
  symbol: string
  assetType: AssetType
}): Promise<PivotLevels | undefined> {
  const url = new URL('/api/pivot-levels', API_BASE)
  url.searchParams.set('symbol', params.symbol)
  url.searchParams.set('asset_type', params.assetType)

  const res = await fetch(url.toString())
  if (!res.ok) {
    // Pivot levels are supplementary — don't fail the whole chart load if they're unavailable.
    return undefined
  }
  const body = (await res.json()) as PivotLevelsResponse
  return body.pivot_levels
}

export async function fetchChartData(params: {
  symbol: string
  interval: string
  bars: number
  assetType: AssetType
}): Promise<ChartResponse> {
  const [rows, pivotLevels] = await Promise.all([
    fetchTimeSeries(params),
    fetchPivotLevels(params).catch(() => undefined),
  ])

  // Backend returns its default window of bars; cap to the requested count.
  const trimmed = params.bars > 0 ? rows.slice(-params.bars) : rows

  return {
    data: trimmed,
    pivotLevels,
    dailyChange: computeDailyChange(trimmed),
  }
}
