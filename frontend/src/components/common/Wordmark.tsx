interface WordmarkProps {
  /** Size of the glyph mark in px. Text scales from this. */
  size?: number
  showText?: boolean
  className?: string
}

/**
 * Brand mark: a cobalt gradient rounded-square chip with a rising-line
 * glyph, next to the grotesk wordmark.
 */
export default function Wordmark({ size = 28, showText = true, className = '' }: WordmarkProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <span
        className="relative inline-flex shrink-0 items-center justify-center"
        style={{
          width: size,
          height: size,
          background: 'linear-gradient(135deg, var(--grad-from), var(--grad-to))',
          borderRadius: Math.max(6, size * 0.28),
          boxShadow: 'var(--glow)',
        }}
        aria-hidden
      >
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none">
          <path
            d="M7 14.5 11 10l3 3 4-6"
            stroke="#ffffff"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="18" cy="7" r="1.7" fill="#ffffff" />
        </svg>
      </span>
      {showText && (
        <span
          className="font-display leading-none"
          style={{ fontSize: size * 0.66, fontWeight: 650, color: 'var(--text)' }}
        >
          Tradable&nbsp;Mind
        </span>
      )}
    </div>
  )
}
