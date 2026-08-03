# Deployment — Render (backend) + Vercel (frontend)

Backend and Redis run on Render, declared in [`render.yaml`](../render.yaml).
The frontend is a static Vite build on Vercel, configured by
[`frontend/vercel.json`](../frontend/vercel.json).

## How the two halves connect

The browser never talks to Render directly. Vercel rewrites `/api/*` to the
Render service server-side, so every request the browser makes is same-origin
with `nexus-mail.me`:

```
browser → https://nexus-mail.me/api/gmail/emails
            │  (Vercel edge rewrite)
            ▼
          https://nexus-mail.onrender.com/api/gmail/emails
```

This is why `src/api.ts` needs no `VITE_API_URL`: its `/api` default works in
development (proxied by `vite.config.ts`) and in production (rewritten by
Vercel) without change. It also means CORS is not in the request path — the
`CORS_ORIGINS` entries in `render.yaml` exist only for direct API access.

## Backend — Render

1. **New → Blueprint**, point it at this repo. Render reads `render.yaml` and
   creates two services: the `nexus-mail` web service and the `nexus-redis`
   Key Value instance. `REDIS_URL` is wired between them automatically.
2. Fill in the secrets. Every variable marked `sync: false` is created empty
   and **the backend will not start until they have values**:

   | Variable | Where it comes from |
   |---|---|
   | `MONGODB_URI` | Atlas → Connect → Drivers (substitute the real password) |
   | `MONGODB_DATABASE` | `nexus_mail` |
   | `APP_SECRET_KEY` | any random string, min 32 chars |
   | `JWT_SECRET_KEY` | any random string, min 32 chars |
   | `ENCRYPTION_KEY` | base64 AES-256 key — `openssl rand -base64 32` |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud Console → Credentials |
   | `GROQ_API_KEY` | console.groq.com |
   | `OPENROUTER_API_KEY` | openrouter.ai |

3. **Atlas Network Access must allow `0.0.0.0/0`.** Render's egress IPs are
   dynamic on the free plan, so an IP allowlist will fail there even when it
   works locally.

Health check is `GET /health`. A successful boot logs `MongoDB connected`,
`Redis connected`, then `Application startup complete`.

## Frontend — Vercel

1. **Add New → Project**, import the repo.
2. Set **Root Directory** to `frontend`. Everything else (framework, build
   command, output directory) comes from `vercel.json`.
3. No environment variables are required.
4. **Domains** → add `nexus-mail.me`, and point the domain's DNS at Vercel.

## Google Cloud Console

Add both redirect URIs under **Credentials → OAuth 2.0 Client ID → Authorized
redirect URIs**, or login will fail with `redirect_uri_mismatch`:

```
https://nexus-mail.me/callback
http://localhost:5173/callback
```

Under **Authorized JavaScript origins**, add `https://nexus-mail.me`.

## Gotchas

- **Free-tier cold starts.** Render free web services sleep after ~15 minutes
  idle; the first request then takes ~50 seconds. `src/api.ts` uses a 30 s
  axios timeout, so the first call after a sleep can time out — retry once.
- **Free Key Value is ephemeral.** Restarting clears it. That is safe here:
  Redis only holds locks, rate-limit counters, and cached agent memory, all of
  which rebuild on demand.
- **Atlas idles out free clusters.** An M0 cluster paused for inactivity has
  its DNS SRV records withdrawn, and the backend dies at startup with
  `The DNS query name does not exist: _mongodb._tcp.<cluster>`. Resume the
  cluster in Atlas to restore it.
- **Preview deploys** rewrite to the same production Render backend, since the
  rewrite destination in `vercel.json` is a fixed URL.
