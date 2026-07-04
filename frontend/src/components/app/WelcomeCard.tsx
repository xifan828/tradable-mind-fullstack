const PROMPTS = [
  'Analyze the current market structure and provide a high probability trading strategy.',
  'How does the structure align across multiple timeframes?',
  'How does the asset usually perform on Mondays during the first two hours of the New York session?',
]

export default function WelcomeCard() {
  return (
    <div className="tm-card tm-fade-in relative overflow-hidden p-6">
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-60 blur-3xl"
        style={{ background: 'var(--glow)' }}
      />
      <div className="relative">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 items-center justify-center rounded-xl"
            style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}
          >
            <span className="material-symbol" style={{ fontSize: 22 }}>
              auto_awesome
            </span>
          </span>
          <div>
            <h3 className="font-display text-lg font-bold leading-tight" style={{ color: 'var(--text)' }}>
              Welcome to Tradable Mind
            </h3>
            <p className="text-[0.82rem] font-medium" style={{ color: 'var(--text-faint)' }}>
              Your Professional-Grade AI Trading Desk
            </p>
          </div>
        </div>

        <p className="mt-4 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          Ask questions about the loaded chart and get institutional-grade reasoning chains —
          multi-agent analysis combining visual pattern recognition with quantitative data.
        </p>

        <p className="mt-5 mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-faint)' }}>
          Try asking
        </p>
        <div className="space-y-2">
          {PROMPTS.map((p) => (
            <div
              key={p}
              className="flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm leading-relaxed"
              style={{ background: 'var(--surface-2)', borderColor: 'var(--border)', color: 'var(--text)' }}
            >
              <span className="material-symbol mt-0.5 shrink-0" style={{ fontSize: 16, color: 'var(--brand)' }}>
                chevron_right
              </span>
              {p}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
