import { Plus, Trash2, MessageSquare } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Button } from './ui/button'

export function Sidebar() {
  const { sessions, currentSessionId, createSession, deleteSession, switchSession } = useApp()

  return (
    <aside className="w-[260px] h-screen border-r border-gray-200 flex flex-col bg-gray-50 shrink-0">
      <div className="p-3 border-b border-gray-200">
        <Button className="w-full" onClick={createSession} size="sm">
          <Plus className="w-4 h-4 mr-1" />
          新规划
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-100 ${
              s.id === currentSessionId ? 'bg-gray-200' : ''
            }`}
            onClick={() => switchSession(s.id)}
          >
            <MessageSquare className="w-4 h-4 text-gray-400 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate">{s.title}</div>
              <div className="text-xs text-gray-400">
                {new Date(s.updated_at).toLocaleDateString('zh-CN')}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="opacity-0 group-hover:opacity-100 h-7 w-7 shrink-0"
              onClick={(e) => {
                e.stopPropagation()
                if (window.confirm('确定要删除这个会话吗？')) {
                  deleteSession(s.id)
                }
              }}
            >
              <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
            </Button>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">暂无会话，点击上方创建</p>
        )}
      </div>
    </aside>
  )
}
