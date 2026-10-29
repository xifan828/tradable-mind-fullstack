export type AssetType = 'forex' | 'commodity' | 'crypto' | 'stock'
export type ModelLabel =
  | 'Google: Gemini 3.8 Flash'
  | 'Google: Gemini 4 Argon'
  | 'MoonshotAI: Kimi K3.1 Pro'
  | 'OpenAI: GPT-6.1 Terra'
export type ThemeMode = 'light' | 'dark'

/** Display label → OpenRouter slug. The label keeps the vendor name so the
 *  dropdown reads on its own; the backend takes the slug verbatim. */
export const MODEL_MAP: Record<ModelLabel, string> = {
  'Google: Gemini 3.8 Flash': 'google/gemini-3.8-flash',
  'Google: Gemini 4 Argon': 'google/gemini-4-argon',
  'MoonshotAI: Kimi K3.1 Pro': 'moonshotai/kimi-k3.1-pro',
  'OpenAI: GPT-6.1 Terra': 'openai/gpt-6.1-terra',
}

export const MODEL_LABELS = Object.keys(MODEL_MAP) as ModelLabel[]

export const DEFAULT_MODEL_LABEL: ModelLabel = 'Google: Gemini 3.8 Flash'

/**
 * Thinking budget sent to the backend as `reasoning_effort`, forwarded to
 * OpenRouter as `reasoning: { effort }`. Keep in sync with REASONING_EFFORTS in
 * the backend (src/agent/utils/llm.py), which falls back to "medium" for
 * anything it does not recognize. The chart and quant subagents take their
 * budget from the backend's .env instead.
 */
export const REASONING_EFFORTS = ['low', 'medium', 'high'] as const
export type ReasoningEffort = (typeof REASONING_EFFORTS)[number]

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
