import { useRef } from 'react'

/** The demo video floating in a glassy rounded frame. */
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
    <div className="tm-glass overflow-hidden p-1.5">
      <div className="group relative overflow-hidden" style={{ borderRadius: 'calc(var(--radius-xl) - 6px)' }}>
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
          className="absolute bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full opacity-0 backdrop-blur transition-opacity duration-150 group-hover:opacity-100"
          style={{ background: 'rgba(0,0,0,0.55)', color: '#ffffff' }}
        >
          <span className="material-symbol" style={{ fontSize: '20px' }}>
            fullscreen
          </span>
        </button>
      </div>
    </div>
  )
}
