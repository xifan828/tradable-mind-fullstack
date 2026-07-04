import HeroBadge from '../components/landing/HeroBadge'
import ApiKeyForm from '../components/landing/ApiKeyForm'
import BrowserMockup from '../components/landing/BrowserMockup'
import FeaturesSection from '../components/landing/FeaturesSection'
import Footer from '../components/landing/Footer'
import Wordmark from '../components/common/Wordmark'
import ThemeToggle from '../components/common/ThemeToggle'

export default function LandingPage() {
  return (
    <div className="relative min-h-screen w-full overflow-x-hidden" style={{ background: 'var(--canvas)' }}>
      {/* Atmospheric backdrop */}
      <div className="pointer-events-none absolute inset-0 -z-10" style={{ background: 'var(--canvas-grad)' }} />
      <div
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[1px]"
        style={{ background: 'linear-gradient(90deg, transparent, var(--border-strong), transparent)' }}
      />

      {/* Top nav */}
      <header className="mx-auto flex w-full max-w-[1140px] items-center justify-between px-6 py-5">
        <Wordmark size={26} />
        <div className="flex items-center gap-3">
          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noreferrer"
            className="hidden text-sm font-medium transition-colors hover:opacity-80 sm:inline"
            style={{ color: 'var(--text-muted)' }}
          >
            Get an API key
          </a>
          <ThemeToggle />
        </div>
      </header>

      {/* Hero */}
      <main className="mx-auto w-full max-w-[1140px] px-6">
        <div className="grid grid-cols-1 items-center gap-14 pt-10 pb-8 lg:grid-cols-[1fr_0.92fr] lg:pt-16">
          {/* Left column */}
          <div>
            <div className="tm-reveal" style={{ animationDelay: '0.05s' }}>
              <HeroBadge />
            </div>

            <h1
              className="tm-reveal font-display mt-7 text-[2.6rem] font-extrabold leading-[1.05] tracking-tight sm:text-[3.4rem]"
              style={{ color: 'var(--text)', animationDelay: '0.12s' }}
            >
              Your AI thinking partner
              <br />
              for{' '}
              <span
                style={{
                  backgroundImage: 'linear-gradient(100deg, var(--brand), var(--brand-strong))',
                  WebkitBackgroundClip: 'text',
                  backgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                real-time market reasoning
              </span>
            </h1>

            <p
              className="tm-reveal mt-6 max-w-[34rem] text-[1.075rem] leading-relaxed"
              style={{ color: 'var(--text-muted)', animationDelay: '0.2s' }}
            >
              Multi-agent analysis with specialized Chart &amp; Quant agents. Move beyond
              black-box signals with institutional-grade reasoning chains and visual pattern
              recognition.
            </p>

            <div className="tm-reveal" style={{ animationDelay: '0.28s' }}>
              <ApiKeyForm />
            </div>
          </div>

          {/* Right column */}
          <div className="tm-reveal" style={{ animationDelay: '0.36s' }}>
            <BrowserMockup />
          </div>
        </div>

        <FeaturesSection />
        <Footer />
      </main>
    </div>
  )
}
