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

## November 1, 2026: UI redesign

- Restyled the frontend into a "ledger" design: new tokens, fonts, header/footer, hero with an example 1040 card, dashboard cards, and a wizard progress bar with step pills. No API, tax-engine or route changes.
- Type check and production build passed. Desktop and mobile screenshots (mocked API) in `docs/ui-redesign/`. Details are in `docs/UI_REDESIGN.md`.

## November 1, 2026: tax-year update kit

- Added release status per year (`rules/<year>/meta.yaml`; 2025 = preview) and draft-year gating in the rules loader and API.
- Added `taxprep/backend/tools/taxyear/` (new_year, check_forms, import_form, pdf_fields, validate, forms manifest), an AI playbook (`.claude/skills/tax-year-update/SKILL.md`, `CLAUDE.md`, `AGENTS.md`) and a monthly form-watch workflow. Details are in `docs/TAX_YEAR_UPDATE_KIT.md`.
- Backend: 100 passed, 2 skipped. 2026 final forms are not published yet; the watcher will open an issue when they are.

## November 1, 2026: real-filing release (branch `real-filing`)

- **Security for real data:**
  - invite-only sign-up, sign-in lockout;
  - HttpOnly cookie sessions with real sign-out, CSRF guard;
  - whole-return encryption, masked SSNs (taxpayer and dependents);
  - account deletion, CSP/HSTS;
  - same-origin `/api` proxy.

  See `docs/SECURITY.md`.
- **Filing package:**
  - preview stamp removed;
  - cover page with mailing addresses (USPS plus UPS/FedEx street addresses, verified on irs.gov, ftb.ca.gov and tax.ny.gov on 2026-11-01), payment notes and due dates;
  - "Where to mail" card on the results page.
- **Federal forms added:** Schedules A (1040 and 1040-NR), B, C, D, SE, 1-A, 3, 8812; Forms 8959, 8960, 8833, 1040-V; dependents on Form 1040.
- **Engine:**
  - 65+ standard and senior deductions;
  - Additional Medicare withholding and excess Social Security credits;
  - 8812 Part II-B;
  - Schedule A detail;
  - Schedule 1-A rounding fix (down, per the form).
- **Website:** new entry screens for all of the above.
- **Tools and docs:** `tools.taxyear.form_fields` lists a PDF's fields with their line labels; `docs/ADDING_A_STATE.md` plus an engine template.
- **Verification:**
  - backend 117 passed, 2 skipped;
  - frontend build passed;
  - local browser run (sign-up → return with SSN and a dependent → calculate → PDF → sign-out/in → resume) with no console errors;
  - filled forms rendered and checked line by line for Schedules A, 3, D, 8812, Form 8959, Form 8960 and the dependents grid.
- **Remaining:** see "Current coverage" in `taxprep/FIXES.md`.

## November 1, 2026: Forms 8949 and 8863, California and New York additions

- **Federal:**
  - Form 8949: per-sale entry, boxes A–L including 1099-DA crypto, 11 rows per page; box totals go to Schedule D.
  - Form 8863: Parts I–III, phase-out ratio to 3 decimals. The under-24 AOTC rule is now asked (line 7) instead of blocked.
- **California:**
  - FTB Tax Table up to $100,000, verified against all 1,000 booklet rows.
  - CA itemized deductions: no state income tax, no SALT cap, high-income limitation.
  - Schedule CA (540) generated.
- **New York:**
  - Published NYS and NYC tax tables, imported by the new `tools/taxyear/ny_tables.py`. The rate schedule alone is off by $1 on some rows.
  - NYC resident tax, NYC school tax credits (lines 69/69a), Yonkers surcharge, W-2 boxes 18–20.
  - IT-201 lines 47–58 and 69–74 filled.
- **Kit:** check_forms accepts year-specific URLs for barcode-dated NY PDFs; the playbook has a NY-tables step.
- **Verification:**
  - Backend: 125 passed, 2 skipped.
  - Frontend: build passed.
  - Local browser run: sign-up → return → calculate → PDF → sign-out/in → resume, with no errors.
  - Rendered checks: Forms 8949, 8863, Schedule CA (540), IT-201 page 3.
- **Still not computed** (listed in `taxprep/FIXES.md` and on the PDF cover):
  - California: Schedule CA (540NR), CalEITC/YCTC, health-coverage penalty.
  - New York: NY/NYC EITC and household credits, Empire State child credit, part-year NYC/Yonkers.
