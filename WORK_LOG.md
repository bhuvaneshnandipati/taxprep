# TaxPrep work log and next-day handoff

Last updated: October 16, 2026 (America/Los_Angeles).

## Current status

The application code has been pushed to GitHub, but the public website is **not live yet**. GitHub authorization is working. A Render database was created, and the API deployment form was prepared. The API and frontend still need to be deployed and tested together.

Your requirements: a website people can use on mobile and desktop, no Docker, code saved to GitHub, and application usage instructions after updates.

- Repository: https://github.com/bhuvaneshnandipati/taxprep
- Local repository: `C:\Users\nandi\Documents\taxprep\github-taxprep`
- Application source: `taxprep/backend` and `taxprep/frontend` inside that repository.

## Completed and pushed to GitHub

1. Restored the saved tax calculation, security, saved-return/resume, and official-form fixes.
2. Added the official 2025 Schedule 2 PDF and mapped the supported additional taxes to its fields.
3. Prepared native Python deployment on Render without Docker.
4. Improved the mobile header and dashboard layout.
5. Added website deployment documentation and an optional Windows launcher for local use.
6. Completed GitHub device authorization and successfully pushed `main`.

Pushed commits:

| Commit | Description |
| --- | --- |
| `2b01121` | Restore audited tax preparation fixes and generate official Schedule 2 |
| `66876cb` | Prepare native Python website deployment and improve mobile layout |

## Frontend upgrade saved locally, not committed or pushed yet

- Upgraded Next.js to `16.4.2` and React/React DOM to `19.3.1`.
- Updated React type packages and dependency lockfile.
- Applied compatible dependency audit fixes.
- Next.js updated its TypeScript configuration/generated type reference file.

At the time of this handoff, these files have uncommitted changes:

- `taxprep/frontend/package.json`
- `taxprep/frontend/package-lock.json`
- `taxprep/frontend/tsconfig.json`
- `taxprep/frontend/next-env.d.ts`

This work log is also newly created locally. Preserve these changes when resuming.

## Checks already completed

- Backend test suite: **78 passed, 2 skipped**. The skipped checks need Tesseract OCR, which was unavailable.
- Upgraded frontend: production build passed using `next build --webpack`, including TypeScript checking and route generation.
- Production dependency audit: `npm audit --omit=dev` reported **0 vulnerabilities** at the time of the check.
- Full dependency audit still reported **7 development-tool findings** (5 high, 2 moderate). These need separate review; the full audit is not clean.
- No deployed end-to-end test has been completed yet.

The package build script is still `next build`. Before deployment, align it with the tested `next build --webpack` command or validate the default build. Review the older pnpm lockfile so it does not conflict with the npm/package-lock workflow.

## Render setup so far

The chosen deployment approach is now **Render for the frontend, API, and PostgreSQL database**. It does not require Docker or separate Vercel/Neon accounts. Older deployment documents still describe Vercel/Neon and need updating once the final deployment is established.

### Database created

- Name: `taxprep-db`
- Resource ID: `dpg-db9giojrjlhs73eoo7ag-a`
- Dashboard: https://dashboard.render.com/d/dpg-db9giojrjlhs73eoo7ag-a
- Region: Oregon
- PostgreSQL: version 18
- Plan: Free
- Last observed status: Creating; readiness still needs checking.
- Dashboard expiration date: **November 15, 2026**. The free database is temporary and is not a durable home for saved returns beyond that date.

An edit to block external database connections was started: the public `0.0.0.0/0` inbound rule was removed in the form, but **Save had not yet been clicked**. Check the current page and save that restriction before continuing. Use the private/internal database connection for the API.

### API form prepared, service not created yet

- Name: `taxprep-api`
- Repository/branch: `bhuvaneshnandipati/taxprep`, `main`
- Runtime: Python 3, native (not Docker)
- Root directory: `taxprep/backend`
- Region: Oregon
- Plan: Free
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health endpoint: `/health`

Environment setup still needed: internal `DATABASE_URL`, a strong `JWT_SECRET`, a Fernet `DATA_KEY`, `PYTHON_VERSION=3.12.10`, and `CORS_ORIGINS` matching the final frontend origin. Preserve the encryption key across deployments. Never commit these secrets or expose them in frontend variables.

### Frontend service still to create

Planned native Node service settings:

- Root directory: `taxprep/frontend`
- Build: `npm ci && npm run build`
- Start: `npm start -- --hostname 0.0.0.0 --port $PORT`
- Use a compatible Node version (the upgraded framework requires at least Node 20.9).
- Set `NEXT_PUBLIC_API_URL` to the actual API HTTPS URL before building.
- Select a free plan unless a paid plan is explicitly approved.

## Resume checklist

1. Preserve the local frontend changes and inspect the current Git diff.
2. Finish the frontend build-script/lockfile cleanup, update outdated documentation, and commit/push the upgrade.
3. Check the existing Render database rather than creating a duplicate; finish the pending network restriction and confirm readiness.
4. Complete the API environment variables and deploy the native Python service.
5. Deploy the frontend as a native Node service and set the API's allowed origin to the exact frontend URL.
6. Verify `/health` and test account creation, sample return entry, calculation, PDF download, sign-out/sign-in, and saved-return resume.
7. Check the website at mobile and desktop sizes.
8. Record the actual public URL, deployment results, remaining limitations, and updated usage instructions here.

GitHub authorization succeeded. Do not restart the earlier OAuth troubleshooting unless a new authentication failure is confirmed. Render's browser dashboard was usable; repeated connector OAuth attempts previously failed.

## How to use the application when the website is live

There is no verified public application URL yet. The GitHub repository and Render dashboard are not the user-facing application.

Once deployed:

1. Open the public website in a browser on your phone or computer; no installation or Docker is required.
2. Create an account or sign in.
3. Choose **Start 2025 return**.
4. Complete **About you → Residency → Interview → Income**.
5. Select **Calculate my return** and review the results and warnings.
6. Select **Download filing package (PDF)**.
7. Reopen saved returns from the dashboard after signing in again.

Use sample data for the initial deployment checks. The app prepares tax year 2025 returns and does **not** electronically file them. Review warnings and required supplemental attachments before using a filing package. Scanned-document OCR needs Tesseract and must be verified separately on the host; manual income entry does not depend on OCR.

## Instructions for the next work session

Suggested message: “Read WORK_LOG.md in C:\Users\nandi\Documents\taxprep\github-taxprep, continue the pending Render deployment without Docker, preserve the local upgrade changes, push completed code to GitHub, and update this log with what changed and how to use the application.”

Keep credentials, database passwords, authentication tokens, and encryption keys out of this log.
