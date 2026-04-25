import { useRef } from 'react'
import { Check, Loader2, Circle } from 'lucide-react'

interface Phase {
  key: string
  label: string
  icon: string
}

const PHASES: Phase[] = [
  { key: 'intent_analysis', label: '意图分析', icon: '🔍' },
  { key: 'plan_generation', label: '行程生成', icon: '📋' },
  { key: 'enrichment', label: '数据富化', icon: '🌍' },
  { key: 'format_response', label: '格式化输出', icon: '✨' },
]

interface GroupedStep {
  phaseKey: string
  text: string
  globalIndex: number
}

function groupSteps(steps: string[]): GroupedStep[] {
  return steps.map((s, i) => {
    const phaseKey = PHASES.find((p) => s.startsWith(p.key))?.key ?? 'other'
    const text = s.replace(/^(intent_analysis|plan_generation|enrichment|format_response):\s*/, '')
    return { phaseKey, text, globalIndex: i }
  })
}

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 10) * 100}ms`
  return `${seconds.toFixed(1)}s`
}

interface Props {
  steps: string[]
}

export function ProcessMonitor({ steps }: Props) {
  const timeStamps = useRef<number[]>([])
  const lastCount = useRef(0)

  if (steps.length > lastCount.current) {
    const now = Date.now()
    for (let i = lastCount.current; i < steps.length; i++) {
      timeStamps.current[i] = now
    }
    lastCount.current = steps.length
  }

  const grouped = groupSteps(steps)

  const completedPhaseKeys = new Set<string>()
  const activePhaseKey = grouped.length > 0 ? grouped[grouped.length - 1].phaseKey : null
  for (const g of grouped) {
    if (g.phaseKey !== activePhaseKey) {
      completedPhaseKeys.add(g.phaseKey)
    }
  }
  const activePhaseIndex = PHASES.findIndex((p) => p.key === activePhaseKey)

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {PHASES.map((phase, pi) => {
        const phaseSteps = grouped.filter((g) => g.phaseKey === phase.key)
        const isCompleted = completedPhaseKeys.has(phase.key)
        const isActive = phase.key === activePhaseKey
        const isPending = !isCompleted && !isActive && pi > activePhaseIndex

        if (isPending && phaseSteps.length === 0) return null

        return (
          <div key={phase.key} className={pi > 0 ? 'border-t border-gray-100' : ''}>
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-50">
              <span className="text-sm leading-none">{phase.icon}</span>
              <span
                className={`text-xs font-medium ${
                  isCompleted ? 'text-green-700' : isActive ? 'text-blue-700' : 'text-gray-500'
                }`}
              >
                {phase.label}
              </span>
              {isCompleted && <Check className="w-3 h-3 text-green-500 ml-auto" />}
              {isActive && <Loader2 className="w-3 h-3 animate-spin text-blue-500 ml-auto" />}
              {isPending && <Circle className="w-3 h-3 text-gray-300 ml-auto" />}
            </div>

            {phaseSteps.length > 0 && (
              <div className="px-3 py-1.5 space-y-1">
                {phaseSteps.map((g) => {
                  const isLastStep = isActive && g.globalIndex === steps.length - 1
                  const elapsed =
                    g.globalIndex > 0 && timeStamps.current[g.globalIndex]
                      ? (timeStamps.current[g.globalIndex] - timeStamps.current[g.globalIndex - 1]) / 1000
                      : g.globalIndex === 0 && timeStamps.current[0]
                        ? (timeStamps.current[0] - timeStamps.current[0]) / 1000
                        : null

                  return (
                    <div
                      key={g.globalIndex}
                      className={`flex items-start gap-1.5 text-xs leading-relaxed ${
                        isLastStep ? 'text-blue-600' : 'text-gray-600'
                      }`}
                    >
                      {isLastStep ? (
                        <Loader2 className="w-2.5 h-2.5 mt-0.5 animate-spin shrink-0 text-blue-500" />
                      ) : (
                        <Check className="w-2.5 h-2.5 mt-0.5 shrink-0 text-green-500" />
                      )}
                      <span className="flex-1">{g.text}</span>
                      {elapsed !== null && (
                        <span className="text-gray-400 tabular-nums shrink-0">
                          +{formatDuration(elapsed)}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
