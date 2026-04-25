import { useApp } from '../context/AppContext'
import ReactMarkdown from 'react-markdown'
import type { Message } from '../types'
import { TravelPlanCard } from './TravelPlanCard'

interface Props {
  message: Message
  index: number
}

export function MessageBubble({ message, index }: Props) {
  const isUser = message.role === 'user'
  const { travelPlan } = useApp()

  const isLastAssistant = !isUser && index > 0
  const showPlanCard = isLastAssistant && travelPlan && travelPlan.days.length > 0

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm ${
          isUser
            ? 'bg-gray-900 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-table:text-xs prose-table:border-collapse">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        {showPlanCard && (
          <div className="mt-2">
            <TravelPlanCard plan={travelPlan} />
          </div>
        )}
      </div>
    </div>
  )
}
