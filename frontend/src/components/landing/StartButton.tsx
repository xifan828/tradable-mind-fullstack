import { Link } from 'react-router-dom'

/**
 * Hero CTA. Nothing is asked of the visitor: the backend always runs on its
 * own OPENROUTER_API_KEY (backend/.env), so this is a plain link into the app
 * rather than a form that has to collect a key first.
 */
export default function StartButton() {
  return (
    <div className="mt-9 flex max-w-[34rem] flex-col gap-3">
      <Link
        to="/app"
        className="tm-btn tm-btn-primary self-start !px-6 !py-3 !text-[0.95rem]"
      >
        Start analyzing
        <span className="material-symbol" style={{ fontSize: 18 }}>
          arrow_forward
        </span>
      </Link>
      <p className="text-[0.82rem]" style={{ color: 'var(--text-faint)' }}>
        No account and no API key — ask your first question straight away.
      </p>
    </div>
  )
}
