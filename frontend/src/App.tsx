import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import MainApp from './pages/MainApp'
import { useAppStore } from './store/useAppStore'

function App() {
  const themeMode = useAppStore((s) => s.themeMode)

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode
  }, [themeMode])

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/app" element={<MainApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
