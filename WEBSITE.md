# TaxPrep website publishing

Status, October 16, 2026 (America/Los_Angeles): an existing Vercel Hobby frontend was recovered at https://taxprep-mu.vercel.app. This is not a verified working hosted tax application. The backend and persistent database are not connected or deployed by this session. Only synthetic test data is permitted.

## Selected free route

Use the existing Vercel Hobby account and frontend project, a second Vercel FastAPI project, and Neon Free PostgreSQL. No Render resources are used by this plan. No paid tier, card, new provider grant, or new service has been created.

Verified provider documentation:
- https://vercel.com/docs/frameworks/backend/fastapi supports app/main.py and Python serverless deployment.
- https://vercel.com/docs/plans/hobby is free for personal, non-commercial use, with usage caps that can pause service. This route is for a personal test preview, not a commercial tax-preparation business.
- https://neon.com/pricing explicitly offers Free without a credit card or time limit; quota and backup limits still apply.

## Necessary account intervention

Neon sign-in via GitHub stops at **Authorize Neon Console**, requesting read-only access to GitHub email addresses. New access requires user confirmation. Any subsequent account-creation terms must also be completed/accepted by the user. Do not authorize or accept on their behalf without the required confirmation.

## Deployment settings prepared

1. Reuse the existing frontend Vercel project `taxprep`, repository root `taxprep/frontend`. Build `npm run build`, Node 22, Next.js framework. GitHub pushes automatically deploy it.
2. Create a Neon project on Free after account authorization. Use its pooled PostgreSQL connection URL with TLS. Do not reuse the expiring Render database or migrate unknown taxpayer records.
3. Import the same GitHub repo as a separate Vercel project, proposed name `taxprep-api`, root `taxprep/backend`, detected FastAPI entrypoint `app/main.py`, Python 3.12. `vercel.json` limits execution to 60 seconds; `.vercelignore` excludes local databases and secrets.
4. Configure backend-only environment variables: `DATABASE_URL` (pooled PostgreSQL TLS URL), `JWT_SECRET` (48 random bytes encoded URL-safe), `DATA_KEY` (valid persistent Fernet key), `PRODUCTION=1`, `DB_SSLMODE=require`, `CORS_ORIGINS=https://taxprep-mu.vercel.app`. The API refuses unsafe production configuration. Never expose secrets in a public frontend variable or source control.
5. Set frontend `NEXT_PUBLIC_API_URL` to the observed backend HTTPS origin and rebuild. Do not guess the URL. Keep the existing projects separate from the portfolio.
6. Rules/templates must be included in the Python function bundle. Rule editing in the hosted admin API is read-only; reviewed rule changes must be committed and redeployed. Serverless local storage is not durable. PostgreSQL persists accounts/returns.
7. Tesseract is unavailable in this serverless plan. Manual entry remains supported. Scanned-image OCR remains unverified/unsupported; do not promise it works. Confirm provider payload limits before uploads; the app's 15 MB bound does not override a provider's smaller bound.
8. Before sharing a working preview: verify health, CORS, synthetic registration/login, cross-account isolation, encryption at rest, create/resume/recalculate, official draft PDF download, and mobile/desktop layout against actual hosted services.

## Release gates

The application is not production-ready. Existing federal, treaty, dual-status, CA/NY calculations and supplemental-form limitations require independent review, including changes in law. Authentication needs abuse controls, account recovery/verification and a broader security/privacy review before handling actual taxpayer data. Local tests do not establish hosted E2E or full tax correctness. PDFs and the UI explicitly identify synthetic test previews. No e-filing is supported.

Free tiers have resource limits; they do not guarantee continuous availability or eliminate maintenance.

Public API calls are disabled by default, and Render endpoints are rejected. After verifying the replacement API, set `NEXT_PUBLIC_ENABLE_API=true` together with its HTTPS `NEXT_PUBLIC_API_URL` and rebuild. Localhost development remains enabled.
