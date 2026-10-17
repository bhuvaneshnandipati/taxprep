# TaxPrep continuation log

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

93 backend checks passed; 2 Tesseract image checks skipped. Production frontend build passed. Local browser journey: synthetic account -> new 2025 return -> synthetic name -> citizen residency -> income $45,000, withholding $4,200 federal/$1,400 CA, age 30 -> $925 federal / $617 CA refunds -> PDF download -> sign-out/sign-in -> saved results resumed. No real taxpayer information was used. API/PDF tests cover additional scenarios, not every tax situation.

## Genuine blocker

Neon OAuth is at GitHub's **Authorize Neon Console**, asking read-only access to email addresses. It was not approved. User confirmation is required for this new access and any subsequent legally binding account terms. Screenshot saved to the chat outputs folder. Existing Vercel account is accessible. No backend or persistent database was created, and no secrets were committed.

Once authorized: create Neon Free project, configure Vercel FastAPI project, set backend-only persistent secrets and exact CORS, connect frontend via NEXT_PUBLIC_API_URL, deploy, and execute hosted synthetic E2E. See WEBSITE.md for settings and release gates. Tax correctness and security reviews remain incomplete, and the app is not production-ready.
