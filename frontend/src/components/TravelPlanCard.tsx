import { useState, type FC } from 'react'
import type { TravelPlan } from '../types'

const DAY_COLORS = [
  'border-l-red-500', 'border-l-blue-500', 'border-l-green-500',
  'border-l-yellow-500', 'border-l-purple-500', 'border-l-orange-500', 'border-l-teal-500',
]

interface Props {
  plan: TravelPlan
  onHoverDay?: (day: number | null) => void
}

export const TravelPlanCard: FC<Props> = ({ plan, onHoverDay }) => {
  const [expanded, setExpanded] = useState<Set<number>>(new Set([1]))

  const toggleDay = (day: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(day)) next.delete(day)
      else next.add(day)
      return next
    })
  }

  return (
    <div className="space-y-3 my-2">
      <h3 className="text-base font-semibold text-gray-900">{plan.title}</h3>
      {plan.days.map((day) => {
        const isOpen = expanded.has(day.day)
        const colorClass = DAY_COLORS[(day.day - 1) % DAY_COLORS.length]
        return (
          <div
            key={day.day}
            className={`border-l-4 ${colorClass} bg-white rounded-r-lg shadow-sm`}
            onMouseEnter={() => onHoverDay?.(day.day)}
            onMouseLeave={() => onHoverDay?.(null)}
          >
            <button
              className="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-gray-50"
              onClick={() => toggleDay(day.day)}
            >
              <span className="text-xs text-gray-400">{isOpen ? '▼' : '▶'}</span>
              <span className="font-medium text-sm">
                Day {day.day} — {day.city}
              </span>
              <span className="text-xs text-gray-400">· {day.theme}</span>
            </button>
            {isOpen && (
              <div className="px-3 pb-3 text-sm">
                <table className="w-full text-xs mb-2">
                  <thead>
                    <tr className="text-gray-400 border-b border-gray-100">
                      <th className="text-left py-1 w-12">时间</th>
                      <th className="text-left py-1">活动</th>
                      <th className="text-left py-1 w-10">类型</th>
                      <th className="text-left py-1 w-10">时长</th>
                    </tr>
                  </thead>
                  <tbody>
                    {day.activities.map((act, i) => (
                      <tr key={i} className="border-b border-gray-50">
                        <td className="py-1 text-gray-500">{act.time}</td>
                        <td className="py-1">
                          <span className="font-medium">{act.name}</span>
                          {act.notes && (
                            <span className="text-gray-400 ml-1">{act.notes}</span>
                          )}
                        </td>
                        <td className="py-1 text-gray-400">{act.type}</td>
                        <td className="py-1 text-gray-400">{act.duration}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="text-xs text-gray-400 space-y-0.5">
                  <div>
                    交通：{day.transport.mode} · {day.transport.duration}
                  </div>
                  <div>酒店：{day.hotel}</div>
                  {day.weather && (
                    <div className="flex items-center gap-1 text-gray-500">
                      <WeatherIcon desc={day.weather.description} />
                      <span>
                        {day.weather.description} {day.weather.temp}°C (
                        {day.weather.temp_min}°C ~ {day.weather.temp_max}°C) 湿度
                        {day.weather.humidity}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function WeatherIcon({ desc }: { desc: string }) {
  let emoji = '☀️'
  if (desc.includes('雨')) emoji = '🌧️'
  else if (desc.includes('雪')) emoji = '🌨️'
  else if (desc.includes('云') || desc.includes('阴')) emoji = '☁️'
  else if (desc.includes('雾')) emoji = '🌫️'
  return <span>{emoji}</span>
}
