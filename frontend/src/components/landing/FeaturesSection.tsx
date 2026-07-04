interface Feature {
  icon: string
  title: string
  description: string
}

const FEATURES: Feature[] = [
  {
    icon: 'hub',
    title: 'Multi-agent Analysis',
    description:
      'Seamless orchestration between specialized Vision agents (pattern recognition) and Math agents (quant data).',
  },
  {
    icon: 'visibility',
    title: 'Pattern Recognition',
    description:
      'Our AI identifies visual candlestick structures like Head & Shoulders or flags while simultaneously computing RSI divergence.',
  },
  {
    icon: 'account_tree',
    title: 'Full Reasoning Chains',
    description:
      'No black boxes. See the full logical deduction path for every trade signal, citing specific data points and patterns.',
  },
]

function FeatureCard({ icon, title, description, index }: Feature & { index: number }) {
  return (
    <div
      className="tm-card tm-reveal group relative overflow-hidden p-6 transition-all duration-300 hover:-translate-y-1.5"
      style={{ animationDelay: `${0.1 + index * 0.08}s` }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 20px 44px -16px var(--glow)'
        e.currentTarget.style.borderColor = 'var(--brand-ring)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      <div
        className="absolute -right-10 -top-10 h-28 w-28 rounded-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: 'var(--glow)' }}
      />
      <div
        className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl"
        style={{ background: 'var(--brand-soft)', color: 'var(--brand)' }}
      >
        <span className="material-symbol" style={{ fontSize: 24 }}>
          {icon}
        </span>
      </div>
      <h3 className="font-display mb-2 text-lg font-bold" style={{ color: 'var(--text)' }}>
        {title}
      </h3>
      <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        {description}
      </p>
    </div>
  )
}

export default function FeaturesSection() {
  return (
    <section className="mt-24">
      <div className="mb-8 flex items-center gap-3">
        <span
          className="text-xs font-semibold uppercase tracking-[0.18em]"
          style={{ color: 'var(--text-faint)' }}
        >
          How it works
        </span>
        <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
      </div>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {FEATURES.map((f, i) => (
          <FeatureCard key={f.title} {...f} index={i} />
        ))}
      </div>
    </section>
  )
}
