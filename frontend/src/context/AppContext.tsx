import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import type { Session, Message, Settings, TravelPlan } from '../types'
import { useLocalStorage } from '../hooks/useLocalStorage'

const DEFAULT_SETTINGS: Settings = {
  model_provider: 'openai',
  model_name: 'gpt-4o',
  api_key: '',
  base_url: '',
  google_maps_key: '',
  weather_api_key: '',
}

interface AppState {
  sessions: Session[]
  currentSessionId: string | null
  messages: Message[]
  settings: Settings
  loading: boolean
  travelPlan: TravelPlan | null
  intermediateSteps: string[]
  streamingContent: string
  createSession: () => Promise<void>
  deleteSession: (id: string) => Promise<void>
  switchSession: (id: string) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  updateSettings: (s: Settings) => void
}

const AppContext = createContext<AppState | null>(null)

function buildWsUrl(sessionId: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/api/ws/chat/${sessionId}`
}

function closeWs(ws: WebSocket | null) {
  if (ws) {
    ws.onopen = null
    ws.onmessage = null
    ws.onclose = null
    ws.onerror = null
    ws.close()
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [travelPlan, setTravelPlan] = useState<TravelPlan | null>(null)
  const [intermediateSteps, setIntermediateSteps] = useState<string[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [settings, setSettings] = useLocalStorage<Settings>('traveller_settings', DEFAULT_SETTINGS)

  // Track active WebSocket and which session it belongs to
  const wsRef = useRef<WebSocket | null>(null)
  const wsSessionRef = useRef<string | null>(null)

  const loadSessions = useCallback(async () => {
    const r = await fetch('/api/history')
    if (r.ok) {
      const data = (await r.json()) as Session[]
      setSessions(data)
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const createSession = useCallback(async () => {
    const r = await fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: '新规划' }),
    })
    if (r.ok) {
      await loadSessions()
      const session = (await r.json()) as Session
      setCurrentSessionId(session.id)
      setMessages([])
      setTravelPlan(null)
    }
  }, [loadSessions])

  const deleteSession = useCallback(
    async (id: string) => {
      const r = await fetch(`/api/session/${id}`, { method: 'DELETE' })
      if (r.ok) {
        await loadSessions()
        if (currentSessionId === id) {
          setCurrentSessionId(null)
          setMessages([])
          setTravelPlan(null)
        }
      }
    },
    [currentSessionId, loadSessions],
  )

  const switchSession = useCallback(async (id: string) => {
    // 关闭当前会话的 WebSocket，防止消息串到其他会话
    closeWs(wsRef.current)
    wsRef.current = null
    wsSessionRef.current = null

    const r = await fetch(`/api/session/${id}`)
    if (r.ok) {
      const detail = (await r.json()) as {
        messages: Message[]
        travel_plan: TravelPlan | null
      }
      setCurrentSessionId(id)
      setMessages(detail.messages || [])
      setTravelPlan(detail.travel_plan || null)
    }
  }, [])

  const sendMessage = useCallback(
    (content: string) => {
      if (!currentSessionId || !content.trim()) return

      // 关闭之前的连接（防止同一会话重复发送）
      closeWs(wsRef.current)

      setLoading(true)
      setIntermediateSteps([])
      setStreamingContent('')

      const userMsg: Message = { role: 'user', content }
      setMessages((prev) => [...prev, userMsg])

      const sessionId = currentSessionId
      const ws = new WebSocket(buildWsUrl(sessionId))
      wsRef.current = ws
      wsSessionRef.current = sessionId

      let assistantContent = ''

      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'chat',
          message: content,
          model_provider: settings.model_provider,
          model_name: settings.model_name,
          api_key: settings.api_key,
          base_url: settings.base_url,
          google_maps_key: settings.google_maps_key,
          weather_api_key: settings.weather_api_key,
        }))
      }

      ws.onmessage = (evt) => {
        // 如果此连接已不属于当前会话，忽略消息
        if (wsSessionRef.current !== sessionId) return

        const data = JSON.parse(evt.data) as { type: string; content?: string; travel_plan?: TravelPlan; slots_filled?: boolean }

        switch (data.type) {
          case 'status':
            setIntermediateSteps((prev) => [...prev, data.content ?? ''])
            break
          case 'token':
            setStreamingContent((prev) => prev + (data.content ?? ''))
            break
          case 'done':
            assistantContent = data.content ?? assistantContent
            if (data.travel_plan) {
              setTravelPlan(data.travel_plan)
            }
            if (assistantContent) {
              setMessages((prev) => [...prev, { role: 'assistant', content: assistantContent }])
            }
            loadSessions()
            ws.close()
            break
          case 'error':
            assistantContent = data.content ?? '服务器错误，请稍后重试。'
            setMessages((prev) => [...prev, { role: 'assistant', content: assistantContent }])
            ws.close()
            break
        }
      }

      ws.onclose = () => {
        // 只有当前 WebSocket 是最新的才重置 loading
        if (wsRef.current === ws) {
          setLoading(false)
          wsRef.current = null
          wsSessionRef.current = null
        }
      }

      ws.onerror = () => {
        if (wsRef.current === ws) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: '网络连接失败，请检查网络后重试。' },
          ])
          ws.close()
        }
      }
    },
    [currentSessionId, settings, loadSessions],
  )

  const updateSettings = useCallback(
    (s: Settings) => {
      setSettings(s)
    },
    [setSettings],
  )

  return (
    <AppContext.Provider
      value={{
        sessions,
        currentSessionId,
        messages,
        settings,
        loading,
        travelPlan,
        intermediateSteps,
        streamingContent,
        createSession,
        deleteSession,
        switchSession,
        sendMessage,
        updateSettings,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}

export function useApp(): AppState {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
