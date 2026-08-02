const PROMPTS = [
  'Analyze the current market structure and provide a high probability trading strategy.',
  'How does the structure align across multiple timeframes?',
  'How does the asset usually perform on Mondays during the first two hours of the New York session?',
]

/** Fills the ChatInput with a suggested prompt (picked up via `tm:suggest`). */
function suggest(prompt: string) {
  window.dispatchEvent(new CustomEvent('tm:suggest', { detail: prompt }))
}

export default function WelcomeCard() {
  return (
    <div className="tm-fade-in">
      <div className="py-4">
        <h3
          className="font-display text-xl leading-snug"
          style={{ fontWeight: 600, color: 'var(--text)' }}
        >
          What are we trading today?
        </h3>
        <p className="mt-2.5 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          Ask anything about the loaded chart and get a full reasoning chain — the chart and
          quant agents work the problem in parallel and synthesize their findings here.
        </p>
      </div>

      <div>
        <p className="tm-kicker mb-2">Try asking</p>
        <div className="space-y-2">
          {PROMPTS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => suggest(p)}
              className="tm-focus flex w-full items-start gap-2.5 border px-3.5 py-2.5 text-left text-sm leading-relaxed transition-colors hover:border-[color:var(--brand)] hover:text-[color:var(--brand)]"
              style={{
                borderColor: 'var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface)',
                color: 'var(--text)',
              }}
            >
              <span className="material-symbol mt-0.5 shrink-0" style={{ fontSize: 15, color: 'var(--brand)' }}>
                arrow_forward
              </span>
              {p}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
