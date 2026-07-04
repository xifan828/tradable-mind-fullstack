import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import type {
  AssetType,
  ChatMessage,
  DailyChange,
  IndicatorSettings,
  ModelLabel,
  OHLCRow,
  PivotLevels,
  SidebarSettings,
  ThemeMode,
} from '../types'

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
  // Auth
  geminiApiKey: string
  setGeminiApiKey: (key: string) => void

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
  subagentModelLabel: ModelLabel
  setMinResearchIterations: (n: number) => void
  setMaxResearchIterations: (n: number) => void
  setMaxConcurrentTasks: (n: number) => void
  setAgentModelLabel: (label: ModelLabel) => void
  setSubagentModelLabel: (label: ModelLabel) => void

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
  pendingChartSettings: Partial<SidebarSettings> | null
  setPendingLoadChart: (pending: boolean) => void
  setPendingClearConversation: (pending: boolean) => void
  setPendingChartSettings: (settings: Partial<SidebarSettings> | null) => void

  // Theme
  themeMode: ThemeMode
  toggleTheme: () => void
}

export const useAppStore = create<AppState>((set) => ({
  geminiApiKey: localStorage.getItem('geminiApiKey') || '',
  setGeminiApiKey: (key) => {
    localStorage.setItem('geminiApiKey', key)
    set({ geminiApiKey: key })
  },

  chartData: null,
  currentSymbol: 'EUR/USD',
  currentInterval: '4h',
  currentAssetType: 'forex',
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
  agentModelLabel: 'Gemini 3 Flash',
  subagentModelLabel: 'Gemini 3 Flash',
  setMinResearchIterations: (n) => set({ minResearchIterations: n }),
  setMaxResearchIterations: (n) => set({ maxResearchIterations: n }),
  setMaxConcurrentTasks: (n) => set({ maxConcurrentTasks: n }),
  setAgentModelLabel: (label) => set({ agentModelLabel: label }),
  setSubagentModelLabel: (label) => set({ subagentModelLabel: label }),

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
  pendingChartSettings: null,
  setPendingLoadChart: (pending) => set({ pendingLoadChart: pending }),
  setPendingClearConversation: (pending) => set({ pendingClearConversation: pending }),
  setPendingChartSettings: (settings) => set({ pendingChartSettings: settings }),

  themeMode: readTheme(),
  toggleTheme: () =>
    set((state) => {
      const next = state.themeMode === 'light' ? 'dark' : 'light'
      localStorage.setItem('themeMode', next)
      return { themeMode: next }
    }),
}))

export function newThreadId(): string {
  return uuidv4()
}
