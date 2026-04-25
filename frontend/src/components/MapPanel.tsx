import { useMemo, useState, type FC } from 'react'
import { GoogleMap, Marker, Polyline, InfoWindow, useJsApiLoader } from '@react-google-maps/api'
import type { TravelPlan, Activity, Weather } from '../types'

const DAY_COLORS = ['#E53E3E', '#3182CE', '#38A169', '#D69E2E', '#805AD5', '#DD6B20', '#319795']

const mapContainerStyle = { width: '100%', height: '100%' }

interface Props {
  plan: TravelPlan | null
  googleMapsKey: string
  highlightedDay?: number | null
}

interface MarkerData {
  lat: number
  lng: number
  name: string
  time: string
  day: number
  city: string
  weather?: Weather
}

export const MapPanel: FC<Props> = ({ plan, googleMapsKey, highlightedDay }) => {
  const [selected, setSelected] = useState<MarkerData | null>(null)

  // 仅在提供了有效 API Key 时加载 Google Maps
  const shouldLoad = !!googleMapsKey
  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: googleMapsKey || '',
    libraries: [],
  })

  if (!shouldLoad) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-400 text-center px-4">
        请在设置中配置 Google Maps API Key 以查看路线地图
      </div>
    )
  }

  const { markers, dayPaths } = useMemo(() => {
    const m: MarkerData[] = []
    const paths: Map<number, { lat: number; lng: number }[]> = new Map()

    if (plan) {
      for (const day of plan.days) {
        const points: { lat: number; lng: number }[] = []
        for (const act of day.activities) {
          if (act.lat != null && act.lng != null) {
            m.push({
              lat: act.lat,
              lng: act.lng,
              name: act.name,
              time: act.time,
              day: day.day,
              city: day.city,
              weather: day.weather,
            })
            points.push({ lat: act.lat, lng: act.lng })
          }
        }
        if (points.length > 0) {
          paths.set(day.day, points)
        }
      }
    }

    return { markers: m, dayPaths: paths }
  }, [plan])

  const bounds = useMemo(() => {
    if (markers.length === 0 || typeof google === 'undefined' || !google.maps?.LatLngBounds) return undefined
    const b = new google.maps.LatLngBounds()
    for (const m of markers) b.extend({ lat: m.lat, lng: m.lng })
    return b
  }, [markers])

  if (!isLoaded) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-400">
        加载地图...
      </div>
    )
  }

  if (!plan || markers.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-400 text-center px-4">
        规划完成后此地展示路线地图
      </div>
    )
  }

  return (
    <GoogleMap
      mapContainerStyle={mapContainerStyle}
      zoom={10}
      onLoad={(map) => {
        if (bounds) map.fitBounds(bounds)
      }}
      options={{ streetViewControl: false, mapTypeControl: false }}
    >
      {Array.from(dayPaths.entries()).map(([day, points]) => (
        <Polyline
          key={day}
          path={points}
          options={{
            strokeColor: DAY_COLORS[(day - 1) % DAY_COLORS.length],
            strokeWeight: highlightedDay === day ? 5 : 3,
            strokeOpacity: highlightedDay != null && highlightedDay !== day ? 0.2 : 0.8,
            zIndex: highlightedDay === day ? 10 : 1,
          }}
        />
      ))}

      {markers.map((m, i) => {
        const isHighlighted = highlightedDay == null || highlightedDay === m.day
        return (
          <Marker
            key={i}
            position={{ lat: m.lat, lng: m.lng }}
            label={{
              text: `${m.day}`,
              color: 'white',
              fontSize: '12px',
              fontWeight: 'bold',
            }}
            icon={{
              path: google.maps.SymbolPath.CIRCLE,
              fillColor: DAY_COLORS[(m.day - 1) % DAY_COLORS.length],
              fillOpacity: isHighlighted ? 1 : 0.3,
              strokeColor: 'white',
              strokeWeight: 2,
              scale: 10,
            }}
            onClick={() => setSelected(m)}
          />
        )
      })}

      {selected && (
        <InfoWindow
          position={{ lat: selected.lat, lng: selected.lng }}
          onCloseClick={() => setSelected(null)}
        >
          <div className="text-sm min-w-[140px]">
            <div className="font-semibold text-gray-900">{selected.name}</div>
            <div className="text-gray-500">
              Day {selected.day} · {selected.city}
            </div>
            <div className="text-gray-500">{selected.time}</div>
            {selected.weather && (
              <div className="text-gray-400 mt-1">
                {selected.weather.description} {selected.weather.temp}°C
              </div>
            )}
          </div>
        </InfoWindow>
      )}
    </GoogleMap>
  )
}
