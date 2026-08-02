interface Feature {
  icon: string
  title: string
  description: string
}

const FEATURES: Feature[] = [
  {
    icon: 'hub',
    title: 'Multi-agent analysis',
    description:
      'Seamless orchestration between specialized vision agents (pattern recognition) and math agents (quant data), synthesized into one answer.',
  },
  {
    icon: 'visibility',
    title: 'Pattern recognition',
    description:
      'The AI reads visual candlestick structures — Head & Shoulders, flags — while simultaneously computing RSI divergence on the raw series.',
  },
  {
    icon: 'account_tree',
    title: 'Full reasoning chains',
    description:
      'No black boxes. Every trade signal ships with its full logical deduction path, citing specific data points and patterns.',
  },
]

export default function FeaturesSection() {
  return (
    <section className="mt-16">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {FEATURES.map((f, i) => (
          <article
            key={f.title}
            className="tm-reveal tm-card p-6 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]"
            style={{ animationDelay: `${0.1 + i * 0.08}s` }}
          >
            <span
              className="inline-flex h-10 w-10 items-center justify-center"
              style={{
                background: 'var(--brand-soft)',
                color: 'var(--brand)',
                borderRadius: 'var(--radius-md)',
              }}
              aria-hidden
            >
              <span className="material-symbol" style={{ fontSize: 20 }}>
                {f.icon}
              </span>
            </span>
            <h3
              className="font-display mt-4 text-[1.15rem] leading-snug"
              style={{ fontWeight: 620, color: 'var(--text)' }}
            >
              {f.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {f.description}
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}
