export default function HeroBadge() {
  return (
    <div
      className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold"
      style={{
        background: 'var(--brand-soft)',
        border: '1px solid var(--brand-ring)',
        color: 'var(--brand)',
      }}
    >
      <span className="pulse-dot inline-block h-2 w-2 rounded-full" style={{ background: 'var(--brand)' }} />
      Powered by Google Gemini 3.0
    </div>
  )
}
