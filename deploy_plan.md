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

> ⚠️ **Caveat — platform auth (verify on deploy).** Managed deployments are
> protected by a **LangSmith API key** by default (`X-Api-Key` header expected on
> every request). Locally there is no auth, which is why `/app/` and `/api/*`
> "just work." In the cloud the browser sends no key, so those requests may return
> 401/403. The docs confirm the deploy mechanics but do **not** state whether the
> custom `http.app` routes and the `/app` static mount sit behind that gate — so
> treat it as the first thing to test on the live URL. See "Auth handling" below.

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

### Remaining — deploy to managed Cloud (LangSmith UI, GitHub-based)

4. **Push to GitHub.** The Cloud deployment builds from a GitHub repo and tracks one
   branch, so push this repo to GitHub first.
5. **One-time GitHub authorization.** A GitHub org owner/admin completes the OAuth
   flow in LangSmith to install/authorize the `hosted-langserve` GitHub app (once
   per workspace).
6. **Create the deployment.** LangSmith → **Deployments → + New Deployment → Import
   from GitHub** → select the repo. Then configure:
   - Deployment **name**.
   - **Branch** to track.
   - **Config file path: `backend/langgraph.json`** — not repo root; this field is
     where that matters.
   - Deployment type: **Development** first (minimal resources), **Production** later
     (up to ~500 req/s).
   - Optionally: "Automatically update deployment on push to branch."
7. **Env vars / secrets.** Add `TWELVE_DATA_API_KEY` (+ anything else the agent
   reads). Do **not** set `LANGGRAPH_CLOUD_LICENSE_KEY` (managed doesn't need it) or
   `LANGSMITH_API_KEY` (platform-managed). The Gemini key stays client-side.
8. **Submit** → it builds the same image (ta-lib compile + `frontend_dist` + tzdata)
   and provisions Postgres + Redis. Grab the URL (e.g.
   `https://<name>-<hash>.us.langgraph.app`); the app lives at `…/app/`.
9. **Smoke-test the deployed URL** — and verify auth first (see below):
   `/ok`, `/app/`, `/api/time-series?...`, end-to-end agent run.

### Auth handling (do this at step 9)

Immediately curl the raw URL with **no** API key:

```bash
curl -i https://<name>-<hash>.us.langgraph.app/ok
curl -i "https://<name>-<hash>.us.langgraph.app/api/time-series?symbol=AAPL&interval=1day"
```

- **200 without a key** → nothing to do; it behaves like local.
- **401/403** → the platform's default LangSmith-API-key gate is in front of our
  routes. Add a custom auth handler (`langgraph` auth) that allows unauthenticated
  access to `/app/*` and `/api/*`, keeping the app keyless (matches the "no app
  auth, user brings their own Gemini key" design). Avoid the alternative of shipping
  a platform key to the browser.

References:
- Cloud deployment setup (GitHub, LangSmith UI): https://docs.langchain.com/langsmith/deploy-to-cloud
- Custom routes: https://docs.langchain.com/langgraph-platform/custom-routes
- Custom auth: https://docs.langchain.com/langgraph-platform/custom-auth

## Cost

- Plus: $39/seat/mo, one managed deployment included; additional usage metered.
- Enterprise (self-host) only if required: custom pricing via sales.
