export type AssetType = 'forex' | 'commodity' | 'crypto' | 'stock'
export type ModelLabel =
  | 'DeepSeek V4.1 Flash'
  | 'Gemini 3.8 Flash'
  | 'Kimi K3'
  | 'GLM 5.3 FlashX'
export type ThemeMode = 'light' | 'dark'

export const MODEL_MAP: Record<ModelLabel, string> = {
  'DeepSeek V4.1 Flash': 'deepseek/deepseek-v4.1-flash',
  'Gemini 3.8 Flash': 'google/gemini-3.8-flash',
  'Kimi K3': 'moonshotai/kimi-k3',
  'GLM 5.3 FlashX': 'z-ai/glm-5.3-flashx',
}

export interface OHLCRow {
  Date: string
  DateLabel: string
  Open: number
  High: number
  Low: number
  Close: number
  Volume?: number
  EMA10?: number
  EMA20?: number
  EMA50?: number
  EMA100?: number
  BB_Upper?: number
  BB_Middle?: number
  BB_Lower?: number
  RSI14?: number
  MACD?: number
  MACD_Signal?: number
  MACD_Diff?: number
  ATR?: number
}

export interface PivotLevels {
  Pivot: number
  R1: number
  R2: number
  R3: number
  S1: number
  S2: number
  S3: number
}

export interface IndicatorSettings {
  ema_10: boolean
  ema_20: boolean
  ema_50: boolean
  ema_100: boolean
  bb: boolean
  rsi: boolean
  macd: boolean
  atr: boolean
  pivot: boolean
  volume: boolean
}

export interface DailyChange {
  change: number
  changePct: number
}

// ---- Chat / streaming types ----

export interface TaskArgs {
  task_type: string
  task_description: string
  chart_analysis_input?: Record<string, unknown>
}

export interface TodoItem {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}

export type ChatMessageType = 'text' | 'thinking' | 'tool_call' | 'user'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  type: ChatMessageType
  content: string
  toolName?: string
  toolArgs?: Record<string, unknown>
  /** For a `tool_call` whose result should render inline (e.g. the task tool). */
  toolCallId?: string
  result?: string | null
  /**
   * Epoch ms before which the message stays hidden. Stream events often
   * arrive in bursts; staggering reveals keeps a sequential feel
   * (think → plan → sub-agents).
   */
  revealAt?: number
}

export interface StreamEvent {
  event_type: 'thinking' | 'tool_call' | 'tool_result' | 'text' | 'error'
  content: unknown
  tool_name?: string
  tool_call_id?: string
}
