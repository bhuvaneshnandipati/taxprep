# Deploying TaxPrep for free

Three free services, ~15 minutes total. No credit card required for any of them.

| Piece      | Service                  | Why |
|------------|---------------------------|-----|
| Database   | [Neon](https://neon.tech) | Free Postgres that doesn't expire (unlike Render's free DB, which is deleted after 90 days) |
| Backend    | [Render](https://render.com) | Free Docker web service — sleeps after 15 min idle, wakes in ~30–50s on the next request. Fine for a low-traffic app. |
| Frontend   | [Vercel](https://vercel.com) | Free tier built for Next.js, no sleep, generous limits |

## 0. Push this code to GitHub
```bash
cd taxprep
git init && git add -A && git commit -m "TaxPrep v1"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/taxprep.git
git branch -M main
git push -u origin main
```

## 1. Database — Neon
1. Sign up at neon.tech (GitHub login works) → **New Project**.
2. Copy the connection string shown (starts with `postgresql://`). Keep it handy.

## 2. Backend — Render
1. Sign up at render.com → **New → Blueprint** → connect your GitHub repo. Render reads `render.yaml` automatically.
   - No blueprint support? Use **New → Web Service** instead → pick the repo → Runtime: **Docker** → Root/Dockerfile path: `backend/Dockerfile`, context `backend`.
2. In the service's **Environment** tab, set:
   - `DATABASE_URL` → the Neon connection string from step 1
   - `JWT_SECRET` → Render can auto-generate this (blueprint does it for you)
   - `ADMIN_EMAILS` → your email, comma-separated if more than one (optional — makes you an admin on first login)
   - `CORS_ORIGINS` → leave as `*` for now; tighten after step 3
3. Deploy. Note the URL Render gives you, e.g. `https://taxprep-api.onrender.com`.
4. Sanity check: open `https://taxprep-api.onrender.com/health` → should return `{"status":"ok"}`.

## 3. Frontend — Vercel
1. Sign up at vercel.com → **Add New → Project** → import the same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variable: `NEXT_PUBLIC_API_URL` = your Render URL from step 2 (no trailing slash).
4. Deploy. Vercel gives you a URL like `https://taxprep.vercel.app` — that's your live app.

## 4. Lock down CORS (recommended, optional)
Back in Render, set `CORS_ORIGINS` to your exact Vercel URL (e.g. `https://taxprep.vercel.app`) instead of `*`, then redeploy the backend. This restricts which websites can call your API with a browser.

## Notes on the free tier
- **Render free web service sleeps after 15 minutes of no traffic.** The first request after a sleep takes 30–50 seconds to wake up — normal, not a bug. Fine for "a few users."
- **Neon free tier**: 0.5 GB storage, doesn't sleep, doesn't expire. Plenty for this app.
- **Vercel free tier**: effectively unlimited for low-traffic personal projects.
- To update the live app later: `git push` — both Render and Vercel auto-redeploy on push to `main`.
- Rotate `JWT_SECRET` (Render → Environment) if you ever suspect it leaked; this invalidates all existing login sessions.
