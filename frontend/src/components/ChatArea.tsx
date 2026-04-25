import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Settings } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Button } from './ui/button'
import { MessageBubble } from './MessageBubble'
import { SettingsDialog } from './SettingsDialog'
import { ProcessMonitor } from './ProcessMonitor'

export function ChatArea() {
  const { currentSessionId, messages, loading, intermediateSteps, sendMessage } = useApp()
  const [input, setInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, intermediateSteps])

  const handleSend = () => {
    if (!input.trim() || loading) return
    sendMessage(input.trim())
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  if (!currentSessionId) {
    return (
      <main className="flex-1 flex items-center justify-center bg-white">
        <div className="text-center text-gray-400">
          <p className="text-lg mb-2">旅行规划助手</p>
          <p className="text-sm">创建或选择一个会话开始规划你的旅程</p>
        </div>
      </main>
    )
  }

  return (
    <main className="flex-1 flex flex-col bg-white min-w-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
        <h2 className="text-sm font-medium text-gray-700">旅行规划</h2>
        <Button variant="ghost" size="icon" onClick={() => setShowSettings(true)} title="设置">
          <Settings className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} index={i} />
        ))}

        {loading && intermediateSteps.length > 0 && (
          <ProcessMonitor steps={intermediateSteps} />
        )}

        {loading && intermediateSteps.length === 0 && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            正在分析您的偏好...
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-200 p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="输入你的旅行想法..."
            rows={2}
            className="flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400"
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()} size="icon">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
    </main>
  )
}
