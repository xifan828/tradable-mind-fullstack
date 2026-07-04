import { useAppStore } from '../../store/useAppStore'

interface ThemeToggleProps {
  /** "icon" = compact square button; "full" = full-width labelled button. */
  variant?: 'icon' | 'full'
}

export default function ThemeToggle({ variant = 'icon' }: ThemeToggleProps) {
  const themeMode = useAppStore((s) => s.themeMode)
  const toggleTheme = useAppStore((s) => s.toggleTheme)
  const isDark = themeMode === 'dark'
  const icon = isDark ? 'dark_mode' : 'light_mode'

  if (variant === 'full') {
    return (
      <button onClick={toggleTheme} className="tm-btn tm-btn-ghost w-full" aria-label="Toggle color theme">
        <span className="material-symbol" style={{ fontSize: 18 }}>
          {icon}
        </span>
        {isDark ? 'Dark' : 'Light'} mode
      </button>
    )
  }

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle color theme"
      className="tm-focus inline-flex h-9 w-9 items-center justify-center rounded-[10px] border transition-colors"
      style={{ background: 'var(--surface-2)', borderColor: 'var(--border)', color: 'var(--text)' }}
    >
      <span className="material-symbol" style={{ fontSize: 18 }}>
        {icon}
      </span>
    </button>
  )
}
