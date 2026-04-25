import { AppProvider, useApp } from './context/AppContext'
import { Sidebar } from './components/Sidebar'
import { ChatArea } from './components/ChatArea'
import { MapPanel } from './components/MapPanel'

function AppLayout() {
  const { travelPlan, settings } = useApp()
  const showMap = travelPlan && travelPlan.days.length > 0 && settings.google_maps_key

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <ChatArea />
      {showMap && (
        <div className="w-[400px] h-full border-l border-gray-200 shrink-0 hidden lg:block">
          <MapPanel plan={travelPlan} googleMapsKey={settings.google_maps_key} />
        </div>
      )}
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  )
}
