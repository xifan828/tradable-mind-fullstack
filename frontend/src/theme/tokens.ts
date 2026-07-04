export const LIGHT = {
  app_bg: '#f5f5f5',
  sidebar_bg: '#ffffff',
  card_bg: '#ffffff',
  border: '#e0e0e0',
  text_primary: '#1a1a1a',
  text_muted: '#666666',
  primary: '#1976d2',
  primary_hover: '#1565c0',
  primary_shadow: 'rgba(25, 118, 210, 0.2)',
  input_bg: '#ffffff',
  input_border: '#e0e0e0',
  tool_call_bg: '#e3f2fd',
  tool_result_bg: '#e8f5e9',
  thinking_bg: '#fff8e1',
  task_bg: '#e0f2f1',
  todo_bg: '#f3e5f5',
  secondary_bg: '#f5f5f5',
  secondary_hover: '#e0e0e0',
}

export const DARK = {
  app_bg: '#0e1117',
  sidebar_bg: '#1a1a2e',
  card_bg: '#1a1a2e',
  border: '#2d2d3d',
  text_primary: '#e8e8f0',
  text_muted: '#a0a0b0',
  primary: '#4a90d9',
  primary_hover: '#3a7bc8',
  primary_shadow: 'rgba(74, 144, 217, 0.3)',
  input_bg: '#252535',
  input_border: '#3d3d4d',
  tool_call_bg: '#1a2435',
  tool_result_bg: '#1a2d1e',
  thinking_bg: '#2d2a1f',
  task_bg: '#1a2d2d',
  todo_bg: '#261d2e',
  secondary_bg: '#2d2d3d',
  secondary_hover: '#3d3d4d',
}

export type ThemeTokens = typeof LIGHT

export function getTheme(mode: 'light' | 'dark'): ThemeTokens {
  return mode === 'light' ? LIGHT : DARK
}

export const PIVOT_COLORS_LIGHT: Record<string, { bg: string; text: string }> = {
  R3: { bg: '#fee2e2', text: '#dc2626' },
  R2: { bg: '#fecaca', text: '#dc2626' },
  R1: { bg: '#fef2f2', text: '#dc2626' },
  Pivot: { bg: '#f3f4f6', text: '#374151' },
  S1: { bg: '#f0fdf4', text: '#16a34a' },
  S2: { bg: '#bbf7d0', text: '#16a34a' },
  S3: { bg: '#86efac', text: '#16a34a' },
}

export const PIVOT_COLORS_DARK: Record<string, { bg: string; text: string }> = {
  R3: { bg: '#3d1a1a', text: '#ff9999' },
  R2: { bg: '#4d2020', text: '#ff9999' },
  R1: { bg: '#5d2626', text: '#ff9999' },
  Pivot: { bg: '#2d2d3d', text: '#e8e8f0' },
  S1: { bg: '#1a3d1a', text: '#99ff99' },
  S2: { bg: '#204d20', text: '#99ff99' },
  S3: { bg: '#266626', text: '#99ff99' },
}

export const CHART_COLORS = {
  candle_up: '#26a69a',
  candle_down: '#ef5350',
  ema_10: '#2196F3',
  ema_20: '#FF9800',
  ema_50: '#9C27B0',
  ema_100: '#E91E63',
  bb_band: '#607D8B',
  bb_middle: '#2196F3',
  rsi: '#9C27B0',
  rsi_overbought: '#ef5350',
  rsi_oversold: '#26a69a',
  macd_line: '#2196F3',
  macd_signal: '#FF9800',
  macd_hist_pos: '#26a69a',
  macd_hist_neg: '#ef5350',
  atr: '#29b6f6',
  volume_up: 'rgba(38, 166, 154, 0.5)',
  volume_down: 'rgba(239, 83, 80, 0.5)',
}
