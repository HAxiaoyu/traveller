import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
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
  createSession: () => Promise<void>
  deleteSession: (id: string) => Promise<void>
  switchSession: (id: string) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  updateSettings: (s: Settings) => void
}

const AppContext = createContext<AppState | null>(null)

function parseSSEStream(raw: string): { type: string; payload: Record<string, unknown> }[] {
  const events: { type: string; payload: Record<string, unknown> }[] = []
  let currentEvent = ''
  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim()
    } else if (line.startsWith('data: ')) {
      try {
        const payload = JSON.parse(line.slice(6))
        events.push({ type: currentEvent || 'unknown', payload })
      } catch {
        // skip unparseable events
      }
      currentEvent = ''
    }
  }
  return events
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [travelPlan, setTravelPlan] = useState<TravelPlan | null>(null)
  const [intermediateSteps, setIntermediateSteps] = useState<string[]>([])
  const [settings, setSettings] = useLocalStorage<Settings>('traveller_settings', DEFAULT_SETTINGS)

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
    async (content: string) => {
      if (!currentSessionId || !content.trim()) return
      setLoading(true)
      setIntermediateSteps([])

      const userMsg: Message = { role: 'user', content }
      setMessages((prev) => [...prev, userMsg])

      try {
        const resp = await fetch(`/api/chat/${currentSessionId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: content,
            model_provider: settings.model_provider,
            model_name: settings.model_name,
            api_key: settings.api_key,
            base_url: settings.base_url,
            google_maps_key: settings.google_maps_key,
            weather_api_key: settings.weather_api_key,
          }),
        })

        if (!resp.ok) {
          const errText = resp.status === 401 ? 'API Key 无效，请在设置中检查。' : '服务器错误，请稍后重试。'
          setMessages((prev) => [...prev, { role: 'assistant', content: errText }])
          setLoading(false)
          return
        }

        const reader = resp.body?.getReader()
        if (!reader) {
          setLoading(false)
          return
        }

        const decoder = new TextDecoder()
        let assistantContent = ''
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const events = parseSSEStream(buffer)
          for (const evt of events) {
            if (evt.type === 'status') {
              setIntermediateSteps((prev) => [...prev, evt.payload.content as string])
            } else if (evt.type === 'done') {
              assistantContent = (evt.payload.content as string) || assistantContent
              if (evt.payload.travel_plan) {
                setTravelPlan(evt.payload.travel_plan as TravelPlan)
              }
            } else if (evt.type === 'error') {
              assistantContent = evt.payload.content as string
            }
          }

          const lastNewline = buffer.lastIndexOf('\n')
          if (lastNewline !== -1) {
            buffer = buffer.slice(lastNewline + 1)
          }
        }

        if (assistantContent) {
          const aiMsg: Message = { role: 'assistant', content: assistantContent }
          setMessages((prev) => [...prev, aiMsg])
        }
        await loadSessions()
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '网络连接失败，请检查网络后重试。' },
        ])
      } finally {
        setLoading(false)
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
