import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../../store/useAppStore'

export default function ApiKeyForm() {
  const [apiKey, setApiKey] = useState('')
  const setGeminiApiKey = useAppStore((s) => s.setGeminiApiKey)
  const navigate = useNavigate()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = apiKey.trim()
    // The key is optional: the backend uses OPENROUTER_API_KEY from its .env
    // when the browser doesn't send one. A key entered here acts as a
    // per-browser override.
    if (trimmed) setGeminiApiKey(trimmed)
    navigate('/app')
  }

  return (
    <div className="mt-9 max-w-[34rem]">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="API key (optional — server key used by default)"
          className="tm-input flex-1 !rounded-[var(--radius-pill)] !px-5 !py-3 !text-[0.95rem]"
          autoComplete="off"
        />
        <button type="submit" className="tm-btn tm-btn-primary shrink-0 !px-6 !py-3">
          Start analyzing
          <span className="material-symbol" style={{ fontSize: 18 }}>
            arrow_forward
          </span>
        </button>
      </form>
      <p className="mt-4 flex flex-col gap-1 text-[0.82rem]" style={{ color: 'var(--text-muted)' }}>
        <span className="inline-flex items-center gap-1.5" style={{ color: 'var(--text-faint)' }}>
          <span className="material-symbol" style={{ fontSize: 15, color: 'var(--brand)' }}>
            key
          </span>
          Leave empty to use the server's key. Enter an OpenRouter key here only to override it for this browser.
        </span>
      </p>
    </div>
  )
}
