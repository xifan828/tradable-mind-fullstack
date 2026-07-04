import { useRef } from 'react'

export default function BrowserMockup() {
  const videoRef = useRef<HTMLVideoElement>(null)

  function handleExpand() {
    const video = videoRef.current
    if (!video) return
    if (video.requestFullscreen) {
      video.requestFullscreen()
    } else if ('webkitEnterFullscreen' in video) {
      // iOS Safari
      ;(video as HTMLVideoElement & { webkitEnterFullscreen: () => void }).webkitEnterFullscreen()
    }
  }

  return (
    <div className="relative">
      {/* Glow */}
      <div
        className="absolute -inset-8 -z-10 rounded-[2.5rem] opacity-70 blur-3xl"
        style={{ background: 'radial-gradient(closest-side, var(--glow), transparent)' }}
      />
      <div
        className="overflow-hidden rounded-2xl border"
        style={{ borderColor: 'var(--border)', background: 'var(--surface)', boxShadow: 'var(--shadow-lg)' }}
      >
        <div
          className="flex items-center gap-3 border-b px-4 py-3"
          style={{ borderColor: 'var(--border)', background: 'var(--surface-2)' }}
        >
          <div className="flex gap-1.5">
            <span className="h-3 w-3 rounded-full" style={{ background: '#f87171' }} />
            <span className="h-3 w-3 rounded-full" style={{ background: '#fbbf24' }} />
            <span className="h-3 w-3 rounded-full" style={{ background: '#4ade80' }} />
          </div>
          <span
            className="mx-auto rounded-md px-3 py-1 text-xs font-medium"
            style={{ background: 'var(--surface-3)', color: 'var(--text-faint)' }}
          >
            tradablemind.app — Live Demo
          </span>
        </div>
        <div className="group relative">
          <video
            ref={videoRef}
            className="block h-auto w-full"
            autoPlay
            muted
            loop
            playsInline
            src={`${import.meta.env.BASE_URL}demo.mp4`}
          />
          <button
            type="button"
            onClick={handleExpand}
            aria-label="Expand video to full screen"
            title="Full screen"
            className="absolute right-3 bottom-3 flex h-9 w-9 items-center justify-center rounded-lg opacity-0 backdrop-blur transition-opacity duration-150 group-hover:opacity-100"
            style={{ background: 'rgba(0,0,0,0.55)', color: '#ffffff' }}
          >
            <span className="material-symbol" style={{ fontSize: '20px' }}>
              fullscreen
            </span>
          </button>
        </div>
      </div>
    </div>
  )
}
