import ApiKeyForm from '../components/landing/ApiKeyForm'
import BrowserMockup from '../components/landing/BrowserMockup'
import FeaturesSection from '../components/landing/FeaturesSection'
import Footer from '../components/landing/Footer'
import ThemeToggle from '../components/common/ThemeToggle'
import Wordmark from '../components/common/Wordmark'

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
              <span className="tm-reveal tm-badge" style={{ animationDelay: '0.05s' }}>
                <span
                  className="pulse-dot inline-block h-1.5 w-1.5 rounded-full"
                  style={{ background: 'var(--brand)' }}
                />
                Powered by Google Gemini 3.0
              </span>

              <h1
                className="tm-reveal font-display mt-6 text-[2.9rem] leading-[1.04] sm:text-[3.6rem]"
                style={{ fontWeight: 640, color: 'var(--text)', animationDelay: '0.12s' }}
              >
                Tradable Mind.
                <br />
                <span className="tm-gradient-text">Your real-time trading partner.</span>
              </h1>

              <p
                className="tm-reveal mt-6 max-w-[32rem] text-[1.05rem] leading-relaxed"
                style={{ color: 'var(--text-muted)', animationDelay: '0.2s' }}
              >
                A multi-agent analyst that reads the market with you. Specialized chart and
                quant agents turn live data into a professional trading plan — and every plan
                arrives as a full reasoning chain, not a black-box signal.
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
