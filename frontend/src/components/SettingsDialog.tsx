import { useState } from 'react'
import { useApp } from '../context/AppContext'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Dialog, DialogFooter } from './ui/dialog'
import type { Settings } from '../types'

interface Props {
  open: boolean
  onClose: () => void
}

const PROVIDERS: { label: string; value: string; defaultModel: string }[] = [
  { label: 'OpenAI', value: 'openai', defaultModel: 'gpt-4o' },
  { label: 'Anthropic', value: 'anthropic', defaultModel: 'claude-sonnet-4-6' },
  { label: '智谱 (Zhipu)', value: 'zhipu', defaultModel: 'glm-4' },
]

export function SettingsDialog({ open, onClose }: Props) {
  const { settings, updateSettings } = useApp()
  const [form, setForm] = useState<Settings>({ ...settings })

  const handleSave = () => {
    updateSettings(form)
    onClose()
  }

  const handleClose = () => {
    setForm({ ...settings })
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} title="设置">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型提供商</label>
          <select
            value={form.model_provider}
            onChange={(e) => {
              const provider = PROVIDERS.find((p) => p.value === e.target.value)
              setForm((f) => ({
                ...f,
                model_provider: e.target.value,
                model_name: provider?.defaultModel || f.model_name,
              }))
            }}
            className="w-full h-9 rounded-md border border-gray-300 bg-white px-3 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
          <Input
            value={form.model_name}
            onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
            placeholder="gpt-4o / claude-sonnet-4-6"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
          <Input
            type="password"
            value={form.api_key}
            onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
            placeholder="sk-..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Google Maps API Key</label>
          <Input
            type="password"
            value={form.google_maps_key}
            onChange={(e) => setForm((f) => ({ ...f, google_maps_key: e.target.value }))}
            placeholder="可选，用于地图和坐标补全"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">OpenWeatherMap API Key</label>
          <Input
            type="password"
            value={form.weather_api_key}
            onChange={(e) => setForm((f) => ({ ...f, weather_api_key: e.target.value }))}
            placeholder="可选，用于天气预报"
          />
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={handleClose}>
          取消
        </Button>
        <Button onClick={handleSave}>保存</Button>
      </DialogFooter>
    </Dialog>
  )
}
