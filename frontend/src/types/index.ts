export interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface SessionDetail extends Session {
  messages: Message[]
  slots: Record<string, unknown>
  travel_plan: TravelPlan | null
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface TravelPlan {
  title: string
  days: DayPlan[]
}

export interface DayPlan {
  day: number
  city: string
  theme: string
  activities: Activity[]
  transport: { mode: string; duration: string }
  hotel: string
  weather?: Weather
}

export interface Activity {
  name: string
  type: string
  lat: number | null
  lng: number | null
  duration: string
  time: string
  notes: string
}

export interface Weather {
  description: string
  temp: number
  temp_min: number
  temp_max: number
  humidity: number
}

export interface Settings {
  model_provider: string
  model_name: string
  api_key: string
  base_url: string
  google_maps_key: string
  weather_api_key: string
}

export interface SSEEvent {
  type: 'status' | 'done' | 'error'
  content: string
  travel_plan?: TravelPlan
  slots_filled?: boolean
}
