import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { v4 as uuidv4 } from 'uuid'
import type {
  AssetType,
  ChatMessage,
  DailyChange,
  IndicatorSettings,
  ModelLabel,
  OHLCRow,
  PivotLevels,
  ReasoningEffort,
  ThemeMode,
} from '../types'
import { DEFAULT_MODEL_LABEL, MODEL_MAP, REASONING_EFFORTS } from '../types'

const DEFAULT_INDICATORS: IndicatorSettings = {
  ema_10: false,
  ema_20: true,
  ema_50: true,
  ema_100: false,
  bb: false,
  rsi: false,
  macd: false,
  atr: false,
  pivot: false,
  volume: true,
}

function readTheme(): ThemeMode {
  const stored = localStorage.getItem('themeMode')
  return stored === 'dark' ? 'dark' : 'light'
}

interface AppState {
  // Chart
  chartData: OHLCRow[] | null
  currentSymbol: string
  currentInterval: string
  currentAssetType: AssetType
  currentBars: number
  chartLoaded: boolean
  chartLoading: boolean
  chartError: string | null
  pivotLevels: PivotLevels | null
  dailyChange: DailyChange | null
  currentIndicators: IndicatorSettings
  setChartData: (rows: OHLCRow[] | null) => void
  setChartLoading: (loading: boolean) => void
  setChartError: (error: string | null) => void
  setPivotLevels: (levels: PivotLevels | null) => void
  setDailyChange: (change: DailyChange | null) => void
  setCurrentSymbol: (symbol: string) => void
  setCurrentInterval: (interval: string) => void
  setCurrentAssetType: (assetType: AssetType) => void
  setCurrentBars: (bars: number) => void
  setCurrentIndicators: (indicators: IndicatorSettings) => void
  setChartLoaded: (loaded: boolean) => void

  // Agent config
  minResearchIterations: number
  maxResearchIterations: number
  maxConcurrentTasks: number
  agentModelLabel: ModelLabel
  agentReasoningEffort: ReasoningEffort
  setMinResearchIterations: (n: number) => void
  setMaxResearchIterations: (n: number) => void
  setMaxConcurrentTasks: (n: number) => void
  setAgentModelLabel: (label: ModelLabel) => void
  setAgentReasoningEffort: (effort: ReasoningEffort) => void

  // Chat
  messages: ChatMessage[]
  isStreaming: boolean
  threadId: string | null
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  updateMessage: (id: string, updater: (m: ChatMessage) => ChatMessage) => void
  setIsStreaming: (streaming: boolean) => void
  setThreadId: (id: string | null) => void
  resetConversation: () => void

  // Pending actions
  pendingLoadChart: boolean
  pendingClearConversation: boolean
  setPendingLoadChart: (pending: boolean) => void
  setPendingClearConversation: (pending: boolean) => void

  // Theme
  themeMode: ThemeMode
  toggleTheme: () => void

  // Layout
  chatWidth: number
  setChatWidth: (width: number) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      chartData: null,
      currentSymbol: 'EUR/USD',
      currentInterval: '4h',
      currentAssetType: 'forex' as AssetType,
      currentBars: 100,
      chartLoaded: false,
      chartLoading: false,
      chartError: null,
      pivotLevels: null,
      dailyChange: null,
      currentIndicators: DEFAULT_INDICATORS,
      setChartData: (rows) => set({ chartData: rows, chartLoaded: rows !== null }),
      setChartLoading: (loading) => set({ chartLoading: loading }),
      setChartError: (error) => set({ chartError: error }),
      setPivotLevels: (levels) => set({ pivotLevels: levels }),
      setDailyChange: (change) => set({ dailyChange: change }),
      setCurrentSymbol: (symbol) => set({ currentSymbol: symbol }),
      setCurrentInterval: (interval) => set({ currentInterval: interval }),
      setCurrentAssetType: (assetType) => set({ currentAssetType: assetType }),
      setCurrentBars: (bars) => set({ currentBars: bars }),
      setCurrentIndicators: (indicators) => set({ currentIndicators: indicators }),
      setChartLoaded: (loaded) => set({ chartLoaded: loaded }),

      minResearchIterations: 2,
      maxResearchIterations: 6,
      maxConcurrentTasks: 4,
      agentModelLabel: DEFAULT_MODEL_LABEL,
      // Matches the backend default (agents/utils/llm.py): medium unless asked
      // otherwise, so the UI never sends "unspecified" and the run is explicit.
      agentReasoningEffort: 'medium' as ReasoningEffort,
      setMinResearchIterations: (n) => set({ minResearchIterations: n }),
      setMaxResearchIterations: (n) => set({ maxResearchIterations: n }),
      setMaxConcurrentTasks: (n) => set({ maxConcurrentTasks: n }),
      setAgentModelLabel: (label) => set({ agentModelLabel: label }),
      setAgentReasoningEffort: (effort) => set({ agentReasoningEffort: effort }),

      messages: [],
      isStreaming: false,
      threadId: null,
      setMessages: (messages) => set({ messages }),
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      updateMessage: (id, updater) =>
        set((state) => ({
          messages: state.messages.map((m) => (m.id === id ? updater(m) : m)),
        })),
      setIsStreaming: (streaming) => set({ isStreaming: streaming }),
      setThreadId: (id) => set({ threadId: id }),
      resetConversation: () => set({ messages: [], threadId: null }),

      pendingLoadChart: false,
      pendingClearConversation: false,
      setPendingLoadChart: (pending) => set({ pendingLoadChart: pending }),
      setPendingClearConversation: (pending) => set({ pendingClearConversation: pending }),

      themeMode: readTheme(),
      toggleTheme: () =>
        set((state) => {
          const next = state.themeMode === 'light' ? 'dark' : 'light'
          localStorage.setItem('themeMode', next)
          // Flip the attribute before React re-renders: effects that read
          // theme CSS vars (the chart) run before App's data-theme effect.
          document.documentElement.dataset.theme = next
          return { themeMode: next }
        }),

      chatWidth: 480,
      setChatWidth: (width) => set({ chatWidth: width }),
    }),
    {
      name: 'tm-app-v1',
      version: 1,
      // Only durable user preferences are persisted. themeMode stays on
      // its manual localStorage key: the pre-paint script in index.html
      // reads the raw `themeMode` value.
      partialize: (s) => ({
        currentSymbol: s.currentSymbol,
        currentInterval: s.currentInterval,
        currentAssetType: s.currentAssetType,
        currentBars: s.currentBars,
        currentIndicators: s.currentIndicators,
        minResearchIterations: s.minResearchIterations,
        maxResearchIterations: s.maxResearchIterations,
        maxConcurrentTasks: s.maxConcurrentTasks,
        agentModelLabel: s.agentModelLabel,
        agentReasoningEffort: s.agentReasoningEffort,
        chatWidth: s.chatWidth,
      }),
      // Spread persisted indicators over the defaults so snapshots written
      // before a new indicator key existed still get its default. Model
      // labels from snapshots written before the model roster changed fall
      // back to the current default instead of resolving to undefined.
      merge: (persisted, current) => {
        const p = (persisted ?? {}) as Partial<AppState>
        const validModel = (label: unknown): label is ModelLabel =>
          typeof label === 'string' && label in MODEL_MAP
        // Same reasoning for the effort levels, which are persisted as raw
        // strings and would otherwise reach the backend unvalidated.
        const validEffort = (effort: unknown): effort is ReasoningEffort =>
          typeof effort === 'string' && (REASONING_EFFORTS as readonly string[]).includes(effort)
        return {
          ...current,
          ...p,
          agentModelLabel: validModel(p.agentModelLabel) ? p.agentModelLabel : DEFAULT_MODEL_LABEL,
          agentReasoningEffort: validEffort(p.agentReasoningEffort) ? p.agentReasoningEffort : 'medium',
          currentIndicators: { ...DEFAULT_INDICATORS, ...(p.currentIndicators ?? {}) },
        }
      },
    },
  ),
)

export function newThreadId(): string {
  return uuidv4()
}
