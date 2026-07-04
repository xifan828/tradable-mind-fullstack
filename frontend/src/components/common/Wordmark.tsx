interface WordmarkProps {
  /** Size of the glyph mark in px. Text scales from this. */
  size?: number
  showText?: boolean
  className?: string
}

/**
 * Brand mark: a compact "rising candle" glyph + wordmark.
 * The glyph reads as a candlestick/spark — on-theme for a trading desk.
 */
export default function Wordmark({ size = 28, showText = true, className = '' }: WordmarkProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <span
        className="relative inline-flex shrink-0 items-center justify-center rounded-[10px]"
        style={{
          width: size,
          height: size,
          background: 'linear-gradient(150deg, var(--brand), var(--brand-strong))',
          boxShadow: '0 4px 14px -4px var(--glow)',
        }}
        aria-hidden
      >
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none">
          <path d="M7 14.5 11 10l3 3 4-6" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="18" cy="7" r="1.7" fill="white" />
        </svg>
      </span>
      {showText && (
        <span
          className="font-display font-bold leading-none"
          style={{ fontSize: size * 0.62, color: 'var(--text)' }}
        >
          Tradable&nbsp;Mind
        </span>
      )}
    </div>
  )
}
