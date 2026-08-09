import { useEffect, useState } from 'react'
import ApiKeyForm from '../components/landing/ApiKeyForm'
import BrowserMockup from '../components/landing/BrowserMockup'
import FeaturesSection from '../components/landing/FeaturesSection'
import Footer from '../components/landing/Footer'
import ThemeToggle from '../components/common/ThemeToggle'
import Wordmark from '../components/common/Wordmark'

/* Example questions the hero cycles through — each one a real thing a user
   would type, so the "just ask" mental model lands immediately. */
/* All long enough to wrap onto the reserved second line, so the hero
   height reads the same no matter which question is showing. */
const ASK_EXAMPLES = [
  'is the S&P 500 uptrend still intact this week?',
  "where's the invalidation on this BTC long setup?",
  'build me a full EUR/USD trade plan with entries',
  'is gold breaking out here or just faking out?',
]

function AskCycler() {
  const [index, setIndex] = useState(0)
  const [chars, setChars] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      // No animation — show the first question in full, statically
      setChars(ASK_EXAMPLES[index].length)
      return
    }
    const full = ASK_EXAMPLES[index]
    let delay: number
    if (!deleting) {
      if (chars < full.length) {
        delay = 42
      } else {
        // Fully typed — hold, then start deleting
        delay = 2400
      }
    } else {
      delay = chars > 0 ? 18 : 350
    }
    const t = window.setTimeout(() => {
      if (!deleting) {
        if (chars < full.length) setChars(chars + 1)
        else setDeleting(true)
      } else if (chars > 0) {
        setChars(chars - 1)
      } else {
        setDeleting(false)
        setIndex((index + 1) % ASK_EXAMPLES.length)
      }
    }, delay)
    return () => window.clearTimeout(t)
  }, [index, chars, deleting])

  return (
    <span className="tm-ask-q">
      “{ASK_EXAMPLES[index].slice(0, chars)}
      <span className="tm-ask-caret" aria-hidden />”
    </span>
  )
}

export default function LandingPage() {
  return (
    <div className="relative min-h-screen w-full overflow-x-hidden" style={{ background: 'var(--canvas)' }}>
      {/* Soft cobalt mesh light behind the hero */}
      <div className="tm-hero-glow" aria-hidden />

      <div className="relative mx-auto w-full max-w-[1180px] px-6">
        {/* Nav */}
        <header className="flex items-center justify-between py-5">
          <Wordmark size={30} />
          <div className="flex items-center gap-4">
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              className="hidden text-sm font-medium transition-colors hover:text-[color:var(--brand)] md:inline"
              style={{ color: 'var(--text-muted)' }}
            >
              Get an API key
            </a>
            <ThemeToggle />
          </div>
        </header>

        {/* Hero */}
        <main>
          <div className="grid grid-cols-1 items-center gap-12 pb-10 pt-12 lg:grid-cols-[1fr_0.9fr] lg:pt-20">
            {/* Left column */}
            <div>
              <span className="tm-reveal tm-eyebrow" style={{ animationDelay: '0.05s' }}>
                <span className="tm-eyebrow-dot pulse-dot" />
                Stocks
                <span className="tm-eyebrow-sep" aria-hidden />
                Crypto
                <span className="tm-eyebrow-sep" aria-hidden />
                Forex
                <span className="tm-eyebrow-sep" aria-hidden />
                Commodities
              </span>

              <h1 className="tm-reveal tm-hero-title mt-7" style={{ animationDelay: '0.12s' }}>
                Your{' '}
                <span className="tm-mark">
                  second brain
                  <i className="tm-mark-stroke" aria-hidden />
                </span>
                <br />
                for live markets
              </h1>

              <p className="tm-reveal tm-hero-sub tm-ask mt-6" style={{ animationDelay: '0.2s' }}>
                Ask Tradable Mind about… <AskCycler />
              </p>

              <p className="tm-reveal tm-hero-sub mt-4" style={{ animationDelay: '0.24s' }}>
                It sees what you see: your chart, its timeframe, the indicators you've
                applied. Then it sends specialist agents to dig in from every angle, from
                the patterns in the price action to the statistics behind the move to the
                levels that matter. Their findings are reconciled into the most probable
                answer, with the reasoning laid out.
              </p>

              <div className="tm-reveal" style={{ animationDelay: '0.28s' }}>
                <ApiKeyForm />
              </div>
            </div>

            {/* Right column — live demo */}
            <div className="tm-reveal" style={{ animationDelay: '0.36s' }}>
              <BrowserMockup />
            </div>
          </div>

          <FeaturesSection />
          <Footer />
        </main>
      </div>
    </div>
  )
}
