/**
 * Bridge between the CSS design tokens (src/index.css) and lightweight-charts,
 * which needs concrete JS color strings. The `--chart-*` custom properties are
 * the single source of truth; this module only reads them at render time, so
 * the chart follows the active theme automatically (the chart effect re-runs
 * on theme change).
 */

export function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

export function getChartColors() {
  return {
    bg: cssVar('--chart-bg', '#ffffff'),
    grid: cssVar('--chart-grid', '#f2f2f4'),
    text: cssVar('--chart-text', '#8e8e96'),
    ref: cssVar('--chart-ref', '#c2c2c9'),
    separator: cssVar('--chart-separator', '#e4e4e7'),
    candle_up: cssVar('--chart-up', '#0e9f6e'),
    candle_down: cssVar('--chart-down', '#e5484d'),
    ema_10: cssVar('--chart-ema-10', '#0a0a0a'),
    ema_20: cssVar('--chart-ema-20', '#2545ff'),
    ema_50: cssVar('--chart-ema-50', '#ff5c00'),
    ema_100: cssVar('--chart-ema-100', '#71717a'),
    bb_band: cssVar('--chart-bb', '#8e8e96'),
    bb_middle: cssVar('--chart-bb-mid', '#d4d4d8'),
    rsi: cssVar('--chart-rsi', '#2545ff'),
    rsi_overbought: cssVar('--chart-rsi-ob', '#e5484d'),
    rsi_oversold: cssVar('--chart-rsi-os', '#0e9f6e'),
    macd_line: cssVar('--chart-macd', '#0a0a0a'),
    macd_signal: cssVar('--chart-macd-signal', '#ff5c00'),
    macd_hist_pos: cssVar('--chart-macd-pos', 'rgba(14, 159, 110, 0.55)'),
    macd_hist_neg: cssVar('--chart-macd-neg', 'rgba(229, 72, 77, 0.55)'),
    atr: cssVar('--chart-atr', '#71717a'),
    atr_fill: cssVar('--chart-atr-fill', 'rgba(113, 113, 122, 0.10)'),
    volume_up: cssVar('--chart-volume-up', 'rgba(14, 159, 110, 0.35)'),
    volume_down: cssVar('--chart-volume-down', 'rgba(229, 72, 77, 0.35)'),
  }
}

export type ChartColors = ReturnType<typeof getChartColors>

/**
 * Tones for pivot-level chips. Returns CSS var() strings for React inline
 * styles, so chips stay theme-reactive without a JS theme subscription.
 * Resistance levels print in the "down" ink, supports in the "up" ink.
 */
export function pivotTone(key: string): { bg: string; text: string } {
  if (key.startsWith('R')) return { bg: 'var(--down-soft)', text: 'var(--down)' }
  if (key.startsWith('S')) return { bg: 'var(--up-soft)', text: 'var(--up)' }
  return { bg: 'var(--surface-3)', text: 'var(--text-muted)' }
}
