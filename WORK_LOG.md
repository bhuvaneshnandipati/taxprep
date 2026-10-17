# TaxPrep continuation log

For the current 2025 status and 2026 conversion plan, see [TAX_YEAR_HANDOFF.md](TAX_YEAR_HANDOFF.md). This log retains the history of earlier work and blockers; superseded entries below are not the current release state.

## October 17, 2026: 2025 handoff and PDF safety pass

- Added a file-by-file 2026 conversion guide with current hosting, test evidence, official sources, year-specific code locations, and real-data release blockers.
- Changed the PDF cover from filing instructions to a synthetic preview summary; removed mailing, deadline and signing directions from its cover. The official form pages remain watermarked synthetic-only. A rendered example showed the cover content legibly after wrapping the final note.
- Added a PDF regression assertion for the synthetic-only cover. Backend suite: 95 passed, 2 skipped. This does not establish tax correctness or production readiness.

Updated October 16, 2026 (America/Los_Angeles).

## Recovered

Repository: https://github.com/bhuvaneshnandipati/taxprep
Local: C:/Users/nandi/Documents/taxprep/github-taxprep
Drive WORK_LOG.md, README.md, WEBSITE.md and FIXES.md were located/read; local source recovered intact. The earlier log's Render deployment instructions are superseded by the user's no-Render requirement. Existing local modifications to Render manifests were preserved, not applied.

Existing Vercel Hobby frontend: https://taxprep-mu.vercel.app. Latest observed deployment at recovery was 6e88778, Ready. It is not proof of a connected backend.

## This continuation

- Hardened password hashing with versioned SHA-256-before-bcrypt, preserving old hashes and preventing silent 72-byte collisions for new passwords.
- Added hosting-neutral production checks for strong JWT secret, persistent Fernet key, PostgreSQL and exact HTTPS origins; CORS local default is restricted.
- Added no-store and security response headers.
- Bounded upload reads and validated reviewed/applied OCR amounts, including finite-money validation to stop NaN/infinity or negative OCR bypasses.
- Prepared native Vercel FastAPI configuration and excluded secrets/test DBs from deployment. Hosted rule-pack edits are explicitly read-only.
- Added accessible auth labels/form submission, error alerts, and synthetic-preview notices; draft PDFs are explicitly not filing-ready.
- Updated deployment instructions to Vercel + Neon free personal preview. No Render or paid service used.

## Verification

95 backend checks passed; 2 Tesseract image checks skipped. Production frontend build passed. Local browser journey: synthetic account -> new 2025 return -> synthetic name -> citizen residency -> income $45,000, withholding $4,200 federal/$1,400 CA, age 30 -> $925 federal / $617 CA refunds -> PDF download -> sign-out/sign-in -> saved results resumed. No real taxpayer information was used. API/PDF tests cover additional scenarios, not every tax situation.

## Genuine blocker

Neon OAuth is at GitHub's **Authorize Neon Console**, asking read-only access to email addresses. It was not approved. User confirmation is required for this new access and any subsequent legally binding account terms. Screenshot saved to the chat outputs folder. Existing Vercel account is accessible. No backend or persistent database was created, and no secrets were committed.

Once authorized: create Neon Free project, configure Vercel FastAPI project, set backend-only persistent secrets and exact CORS, connect frontend via NEXT_PUBLIC_API_URL, deploy, and execute hosted synthetic E2E. See WEBSITE.md for settings and release gates. Tax correctness and security reviews remain incomplete, and the app is not production-ready.

Public API calls are disabled by default, and Render endpoints are rejected. After verifying the replacement API, set `NEXT_PUBLIC_ENABLE_API=true` together with its HTTPS `NEXT_PUBLIC_API_URL` and rebuild. Localhost development remains enabled.

## Hosted continuation, October 16, 2026

- With explicit approval for Neon's read-only GitHub email access, created Neon Free project `taxprep-2025-preview` (project ID `silent-sound-12978574`, AWS US East 2). The database contains only synthetic test accounts and returns from this continuation.
- Created separate Vercel Hobby FastAPI project `taxprep-api` at https://taxprep-api.vercel.app with private database and application secrets. No secrets were committed.
- Initial runtime failure exposed SQLAlchemy 2.1's move to the Psycopg 3 default. Updated the production dependency to `psycopg[binary]>=3.2` and pushed commit `fa2c038`.
- Corrected the database URL after the browser editor introduced visual line-wrap whitespace. The deployed `/health` endpoint now returns `{"status":"ok"}`.
- Hosted synthetic API check passed health, exact-origin CORS, registration, cross-account isolation, saved return, federal and CA calculation ($925/$617 refund for the synthetic wages example), resume, and PDF download. The script is in the task's `work/taxprep-hosted-smoke.py`, outside the repository.
- With the user's explicit approval, replaced the old `NEXT_PUBLIC_API_URL` Secret with a public Config value pointing to `https://taxprep-api.vercel.app`; added `NEXT_PUBLIC_ENABLE_API=true` as Config. Both apply to Production and Preview. Redeployment was launched for the frontend.
- The connected frontend deployment became Ready. A hosted browser check registered a new synthetic account, created/saved a return, and calculated the wages example: $925 federal and $677 California refunds (the browser example selected the $60 CA renter credit). This differs from the API-only $617 California example by exactly that credit.
- The public results page still displayed filing directions and a past deadline despite its synthetic-only notice. Removed those directions and changed the PDF action to `Download synthetic preview PDF`; the frontend production build passed. This last UI change still requires deployment verification.
- Security and tax correctness review remain incomplete. Only synthetic test data is permitted; do not treat this as a filing-ready tax service.
