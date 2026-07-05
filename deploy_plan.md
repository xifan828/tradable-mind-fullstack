# Deployment Plan

## Target: LangGraph Platform — Managed Cloud (Plus plan)

The app is deployed as a single LangGraph server image. `langgraph.json` already
declares the graph (`agent`), the custom FastAPI app (`http.app → app.py:app`), and
runs the React frontend mounted at `/app`. All of it ships in one image on one URL.

### Why managed Cloud and not standalone self-host

- Standalone / self-hosted server requires `LANGGRAPH_CLOUD_LICENSE_KEY`, issued
  **only on the Enterprise plan** (custom/sales pricing).
- Managed Cloud needs **no license key**. The **Plus plan ($39/seat/mo) includes one
  free managed deployment**. LangChain runs the server, Postgres, and Redis.
- Cloud builds and runs the same Docker image as `langgraph build`/`langgraph up`,
  so custom `http.app` routes and the static frontend mount work as they do locally.

Reconsider self-host (Enterprise) only if data must stay entirely in our own infra.

## What works as-is

- Custom routes `/api/time-series`, `/api/pivot-levels` — supported, no caveats.
- Frontend served at `/app` via `StaticFiles` — standard ASGI, runs verbatim.
- No collision with platform routes (`/assistants`, `/threads`, `/runs`, `/ok`).
- No app DB / auth. Gemini key is passed per-request via run context.

> ✅ **Resolved — platform auth.** Managed deployments gate the **built-in**
> run/stream endpoints (`/threads`, `/runs`) behind a LangSmith API key by default;
> the custom `http.app` routes (`/app`, `/api/*`) are **not** behind that gate. On
> deploy the chart worked but the chat 403'd. Fixed with a custom anonymous auth
> handler that replaces the gate. See "Auth handling" below.

## Blockers to fix before deploy

1. **Frontend build context.** ✅ Fixed. Vite now emits to `backend/frontend_dist`
   (`frontend/vite.config.ts` → `build.outDir`), which is inside the build context
   (`langgraph.json` lives in `backend/`), and `app.py`'s `create_frontend_router`
   default `build_dir` is now `frontend_dist`. The directory is gitignored; it is
   copied into the image from disk at `langgraph build` time, so build the frontend
   before building the image.

2. **`ta-lib` is a C library.** ✅ Fixed. `langgraph.json` now installs the TA-Lib
   C library (v0.6.4, matching the `ta-lib>=0.6.8` Python wrapper) at the OS level
   via `dockerfile_lines` — `apk add build-base wget`, then build from source into
   `/usr`. Test `langgraph build` early to confirm the compile succeeds.

3. **Outbound egress.** Container needs internet for TwelveData / yfinance calls.

### Additional fixes found while verifying the image (`langgraph build` + `langgraph up`)

4. **No IANA tzdata in the Wolfi image.** ✅ Fixed. `ZoneInfo("America/New_York")`
   raised `ZoneInfoNotFoundError` at import time. Added the pure-Python `tzdata`
   package to `pyproject.toml` dependencies; Python's `zoneinfo` uses it as a
   fallback when the OS timezone database is absent.

5. **Frontend API origin was hardcoded to `127.0.0.1:2024`.** ✅ Fixed. The app is
   served by the backend under `/app`, so on any deployed host the chart API
   (`chartApi.ts`) and agent stream (`agentClient.ts`) were calling the wrong
   origin. New `frontend/src/lib/apiBase.ts` resolves `API_BASE` to
   `VITE_API_BASE` → dev fallback `127.0.0.1:2024` → else `window.location.origin`,
   making the build portable across localhost:8123 and the Cloud URL with no rebuild.

Verified locally: image builds, `langgraph up` serves `/app/`, chart APIs return
data (ta-lib works), and a full chat run succeeds.

### Local build/run notes (Windows)

- Build the frontend before `langgraph build` — the image copies `frontend_dist/`
  from disk (gitignored, not from git).
- On PowerShell, set `$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'` before
  langgraph commands; the CLI prints emoji that crash the default cp1252 console.
- Run the built image with `langgraph up --image tradable-mind:test --no-pull`
  (note: `up` uses `--image`, not `-t`; `-t` is a `build` flag). Requires
  `LANGSMITH_API_KEY` for the local dev license.

## Steps

### Done

1. ✅ Sign up for LangSmith Plus.
2. ✅ Fix blockers #1 (frontend output path) and #2 (`ta-lib` OS deps), plus the two
   runtime fixes #4 (tzdata) and #5 (frontend API origin).
3. ✅ Build the frontend, then `langgraph build` and verify locally with
   `langgraph up` (brings up Postgres + Redis): `/ok`, `/app/`, chart APIs, and a
   full chat run all pass.

### Deploy to managed Cloud (LangSmith UI, GitHub-based) — ✅ Done

4. ✅ **Push to GitHub.** The Cloud deployment builds from a GitHub repo and tracks
   one branch, so push this repo to GitHub first.
5. ✅ **One-time GitHub authorization.** A GitHub org owner/admin completes the OAuth
   flow in LangSmith to install/authorize the `hosted-langserve` GitHub app (once
   per workspace).
6. ✅ **Create the deployment.** LangSmith → **Deployments → + New Deployment → Import
   from GitHub** → select the repo. Then configure:
   - Deployment **name**.
   - **Branch** to track.
   - **Config file path: `backend/langgraph.json`** — not repo root; this field is
     where that matters.
   - Deployment type: **Development** first (minimal resources), **Production** later
     (up to ~500 req/s).
   - Optionally: "Automatically update deployment on push to branch."
7. ✅ **Env vars / secrets.** Add `TWELVE_DATA_API_KEY` (+ anything else the agent
   reads). Do **not** set `LANGGRAPH_CLOUD_LICENSE_KEY` (managed doesn't need it) or
   `LANGSMITH_API_KEY` (platform-managed). The Gemini key stays client-side.
8. ✅ **Submit** → it builds the same image (ta-lib compile + `frontend_dist` + tzdata)
   and provisions Postgres + Redis. Live URL:
   `https://tradablemind-7df27f20733657c7aedf03f4685e9f16.us.langgraph.app`; the app
   lives at `…/app/`.
9. ✅ **Smoke-test the deployed URL.** `/app/` loads, the chart draws from TwelveData
   (`/api/*` works). The agent run initially 403'd — resolved in "Auth handling".

### Auth handling — ✅ Done (custom anonymous auth added)

**What happened on the live URL:** `/app/` and the custom `/api/*` chart routes
worked with no key, but the first chat message returned
`403 {"detail":"Missing authentication headers"}` immediately.

**Root cause:** the chart uses our custom `http.app` routes (not behind the gate),
but the chat uses the LangGraph SDK `Client`, which hits the platform's **built-in**
run/stream endpoints (`/threads`, `/runs`). On managed Cloud those sit behind the
default LangSmith-API-key gate; the browser sends no key → 403.

**Fix (shipped):** registered a custom auth handler, which **replaces** that default
gate with our own. It accepts every request as an anonymous user, restoring the
keyless behavior we have locally (matches the "no app auth, user brings their own
Gemini key" design).

- `backend/src/agent/auth.py` — `Auth()` with an `@auth.authenticate` that returns
  `{"identity": "anonymous", ...}` for all requests. No `@auth.on` handlers, so
  authorization defaults to accept.
- `backend/langgraph.json` — new `"auth"` key: `path` → the handler,
  `disable_studio_auth: false` (keeps LangSmith Studio working).

Committed and pushed to `main`; the deployment rebuilt and the chat now streams.

> ⚠️ **Security note:** this makes the deployment fully public — anyone with the URL
> can create runs. That matches the current design; cost is bounded because each run
> needs the caller's own Gemini key. To restrict later, add a shared-secret/token
> check inside the same `authenticate` handler.

### Remaining — point a custom domain at the app (hide the langgraph URL)

**Goal:** serve the app at `tradablemind.com` and never expose the
`…langgraph.app` URL in the browser.

**Registrar URL forwarding does NOT achieve this.** Both "Remove paths" and
"Maintain paths" issue an HTTP redirect, so the browser bounces to the langgraph URL
and shows it in the address bar. "Masked/framed forwarding" wraps the app in an
iframe and breaks the SDK's streaming, cookies, and deep links — do not use it.

**Why a reverse proxy is required (not a redirect):** the frontend derives its API
origin from `window.location.origin` (`frontend/src/lib/apiBase.ts`), so it sends
*all* traffic to whatever host served the page — `/app/*`, `/api/*`, **and**
`/threads` + `/runs`. A redirect changes the origin to the langgraph host (exposed).
A reverse proxy answers on `tradablemind.com` and forwards **every one of those
paths** to the langgraph origin, so the address bar stays on our domain.

**Two options:**

1. **LangGraph native custom domain** — the "official" path, but a **Enterprise-plan**
   feature. Not available on Plus, so not usable here without upgrading.

2. **Cloudflare reverse proxy (recommended, free, ~15 min):**
   - Move `tradablemind.com` nameservers to Cloudflare (free plan).
   - Add a **proxied** DNS record (orange cloud) for the domain.
   - Add a **Cloudflare Worker** routed on `tradablemind.com/*` that rewrites the
     hostname to the origin (overriding Host/SNI so TLS to `*.langgraph.app`
     succeeds). Minimal Worker:

     ```js
     export default {
       async fetch(request) {
         const ORIGIN = "tradablemind-7df27f20733657c7aedf03f4685e9f16.us.langgraph.app";
         const url = new URL(request.url);
         url.hostname = ORIGIN;
         return fetch(new Request(url, request));
       },
     };
     ```

   - Optionally redirect `/` → `/app/` so the bare domain lands on the app.
   - This forwards *all* paths, so chart + chat both work and the browser only ever
     sees `tradablemind.com`.

   Deferred — not doing this yet.

References:
- Cloud deployment setup (GitHub, LangSmith UI): https://docs.langchain.com/langsmith/deploy-to-cloud
- Custom routes: https://docs.langchain.com/langgraph-platform/custom-routes
- Custom auth: https://docs.langchain.com/langgraph-platform/custom-auth
- Cloudflare Workers (reverse proxy for custom domain): https://developers.cloudflare.com/workers/

## Cost

- Plus: $39/seat/mo, one managed deployment included; additional usage metered.
- Enterprise (self-host) only if required: custom pricing via sales.
