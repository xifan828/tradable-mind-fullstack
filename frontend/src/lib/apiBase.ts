// Origin the frontend talks to for both the technical chart API (app.py routes)
// and the LangGraph agent stream. The React app is served *by* the backend under
// `/app`, so in production the API lives on the same origin — deriving it from
// `window.location.origin` makes the build portable across localhost:8123, the
// Cloud deployment URL, or any host, with no rebuild.
//
// Resolution order:
//   1. VITE_API_BASE — explicit override (set in an env file or at build time).
//   2. Dev server (`npm run dev`) — Vite runs on its own port, so fall back to the
//      LangGraph dev server on 127.0.0.1:2024.
//   3. Production build — same origin the page was served from.
export const API_BASE: string =
  import.meta.env.VITE_API_BASE ??
  (import.meta.env.DEV ? 'http://127.0.0.1:2024' : window.location.origin)
