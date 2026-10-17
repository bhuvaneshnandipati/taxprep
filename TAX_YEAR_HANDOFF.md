# TaxPrep: 2025 status and 2026 conversion guide

Updated October 17, 2026 (America/Los_Angeles). This is the main handoff for maintaining the 2025 build and preparing a **separate, reviewed** tax-year 2026 release. It records what was implemented and tested; it is not a tax opinion or certification for real taxpayer use. Do not use real taxpayer data in the current public preview.

## Current 2025 deployment

| Part | Address / location | Purpose |
| --- | --- | --- |
| Frontend | https://taxprep-mu.vercel.app, Vercel project `taxprep` | Next.js 16 interview and results |
| API | https://taxprep-api.vercel.app, Vercel project `taxprep-api` | FastAPI, calculations, PDF generation |
| Database | Neon Free project `taxprep-2025-preview`, AWS US East 2 | Persistent synthetic accounts and returns |
| Source | https://github.com/bhuvaneshnandipati/taxprep | `main` is deployed by both Vercel projects |

Frontend root is `taxprep/frontend`; backend root is `taxprep/backend`. Both use Vercel Hobby, with no Render dependency. The portfolio website is a separate project. Free-tier limits can queue builds or pause service. The 2025 frontend is connected to the API; public sign-in and calculations work with synthetic data.

Backend environment variables: private `DATABASE_URL` (Neon PostgreSQL URL with TLS), `JWT_SECRET`, `DATA_KEY`; configuration `PRODUCTION=1`, `DB_SSLMODE=require`, `CORS_ORIGINS=https://taxprep-mu.vercel.app`. Frontend Production and Preview Config variables: `NEXT_PUBLIC_API_URL=https://taxprep-api.vercel.app`, `NEXT_PUBLIC_ENABLE_API=true`. Never copy private values into `NEXT_PUBLIC_` variables or Markdown. Redeploy after variable changes. Maintain independent encrypted backups before changing or rotating `DATA_KEY`; losing it makes protected identifiers unreadable. Do not put a backup or credentials in Git.

The application prepares only TY2025. The usual federal 2025 filing date was April 15, 2026; exceptions, extensions, and late filing require case-specific review. The preview deliberately omits mailing and signing directions and marks the PDF as synthetic-only. [IRS filing timing](https://www.irs.gov/filing/individuals/when-to-file), [2025 Form 1040-NR instructions](https://www.irs.gov/instructions/i1040nr).

## What was verified

- Backend: 95 checks pass; two image-OCR checks skip without Tesseract. These cover tax examples, access control, encrypted identifiers, and PDF field mappings, but cannot prove complete tax correctness.
- Frontend: production build passes. A hosted browser journey registered a synthetic account, created and saved a 2025 return, calculated it, signed out and back in, and found the saved return. A $45,000 wage example with $4,200 federal and $1,400 California withholding yielded $925 federal and $677 California refunds **with** the $60 renter credit; the API-only example without that credit yielded $617 California. These are regression examples, not tax advice.
- Hosted API: health, exact-origin CORS, registration, cross-account return isolation, save/resume, calculation, and PDF download passed using synthetic data. The final public result page and generated PDF no longer provide mailing or signing instructions.
- The portfolio contact form and its email delivery are unrelated to TaxPrep.

`WORK_LOG.md` records the chronological work. `WEBSITE.md` records current hosting. `taxprep/FIXES.md` records known tax and form limitations. `taxprep/DEPLOY.md` has provider setup details; prefer this handoff and `WEBSITE.md` if older instructions conflict.

## Release blockers for real 2025 returns

Do **not** remove the synthetic-only notices or invite real taxpayer data merely because the site is reachable. A qualified tax reviewer must validate the supported scenarios against official 2025 instructions and sample returns. The current calculation does not cover all cases: supplemental schedules are missing; California health-coverage penalty and certain credits are not computed; New York local taxes, some credits and higher-income recapture are not computed; treaty time limits and dual-status income allocation need review. Some known unsupported cases are blocked, but the block list is not exhaustive. See `taxprep/FIXES.md`.

A security/privacy release review must cover authentication abuse controls, account verification and recovery, session handling (bearer token currently sits in browser `localStorage`), encryption and backups, retention/deletion, upload scanning and limits, access logging, incident response, and privacy/legal notices. Server-side OCR of scanned images is unverified on Vercel; manual entry works. The app does not e-file. Before any real-data launch, commission independent federal, treaty, California, and New York review and run a hosted end-to-end test matrix with synthetic cases plus document/PDF inspection. Do not mark the product filing-ready until each supported path passes and unsupported paths stop before producing a misleading result.

## Year-specific source map for 2026

Do not change a single `2025` constant and assume the app is updated. Copy the 2025 implementation into a separate 2026 work branch, then review each item below against **final** 2026 agency publications. As of this handoff, the IRS has a [draft forms page](https://www.irs.gov/draft-tax-forms); draft forms and preliminary thresholds are not a final release source.

| Review area | Files to change or verify | What to check |
| --- | --- | --- |
| Tax-year selection | `taxprep/backend/app/core/config.py`, `taxprep/backend/app/db/models.py`, `taxprep/backend/app/engines/rules_loader.py`, `taxprep/backend/app/api/returns.py`, `taxprep/backend/app/api/interview.py` | Default year, return creation, available rule packs, legacy 2025 return behavior. Do not silently recalculate saved 2025 returns under 2026 rules. |
| Federal values | `taxprep/backend/rules/2025/federal.yaml` → new `rules/2026/federal.yaml`; `taxprep/backend/app/engines/federal.py` | Standard and additional deductions; ordinary/capital-gain brackets; Tax Table/EIC Table behavior; CTC/ODC, education and EITC thresholds; SALT and Schedule 1-A; Social Security wage base, Medicare/NIIT; withholding and treaty treatment. Review hard-coded eligibility and thresholds in the engine as well as YAML. |
| Residency and treaties | `taxprep/backend/app/engines/residency.py`, `taxprep/backend/app/engines/treaty.py`, `taxprep/backend/rules/2025/treaties.yaml`, `questions.yaml` | Three-year presence window, exempt-individual history, dual-status start, treaty text/rates/time limits and Form 8833 requirements, interview wording. Verify with 2026 Pub. 519, Pub. 901 and treaty texts. |
| California | `taxprep/backend/rules/2025/california.yaml`, `taxprep/backend/app/engines/california.py`, `taxprep/backend/app/engines/states/california.py` | FTB 540/540NR tax tables and schedules, deductions, exemption credits/phaseouts, renter credit, nonconformity, sourced income, health mandate and credits. Current engine uses a rate schedule in some cases where the FTB says to use a tax table; resolve before filing use. |
| New York | `taxprep/backend/rules/2025/newyork.yaml`, `taxprep/backend/app/engines/states/newyork.py` | IT-201/203 tables, deductions, exemptions, tax-benefit recapture, NY-source percentage, NYC/Yonkers taxes and credits. |
| Other states | `taxprep/backend/app/engines/states/registry.py` | Recheck the list of states with no broad wage income tax; reject unsupported states explicitly. |
| Official PDFs | `taxprep/backend/app/pdf/templates/2025/` → new `templates/2026/`; `taxprep/backend/app/pdf/official.py`, `forms.py`, `fill.py` | Get final fillable IRS/FTB/NY forms from the agencies. Field names, line numbers, radio values, schedules, instructions, flattening and page order can change. `official.py` contains 2025-specific California dollar amounts and field names despite accepting a `year` argument. Never reuse its mapping without page-by-page review. |
| Mailing and deadlines | `taxprep/backend/rules/2025/mailing.yaml`, `taxprep/backend/app/pdf/forms.py` and frontend result pages | Check current IRS/FTB/NY addresses, payment and filing dates, extensions and exceptions. The public synthetic preview should continue to omit filing directions until released for real use. |
| Frontend copy and validation | `taxprep/frontend/app/layout.tsx`, `page.tsx`, `dashboard/page.tsx`, `return/[id]/page.tsx`, `components/Ledger.tsx`, `lib/api.ts` | Year labels, interview dates/trips, estimated payments, result labels, PDF filename, API year selection and preview warning. Avoid hard-coded 2025 text when adding multiple years. |
| Examples/tests/docs | `taxprep/backend/tests/`, `taxprep/backend/BUILD_LOG.txt`, `README.md`, `WEBSITE.md`, `WORK_LOG.md`, `taxprep/FIXES.md`, `taxprep/DEPLOY.md` | Add independent 2026 expected values and cases; keep 2025 regression tests. Replace year-specific screenshots, instructions and claims only after verification. |

Official sources to recheck when final 2026 materials appear: [IRS forms and instructions](https://www.irs.gov/forms-instructions-and-publications), [IRS tax tables](https://www.irs.gov/publications/p1040), [IRS 1040-NR](https://www.irs.gov/forms-pubs/about-form-1040-nr), [California forms](https://www.ftb.ca.gov/forms/), [California tables](https://www.ftb.ca.gov/file/personal/tax-calculator-tables-rates.asp), [New York forms](https://www.tax.ny.gov/forms/). For 2025 baselines, compare the [FTB 540 booklet](https://www.ftb.ca.gov/forms/2025/2025-540-booklet.html) and [NY IT-201 instructions](https://www.tax.ny.gov/pdf/2025/inc/it201i_2025.pdf). Record retrieval date and document revision for every number; official publications can be revised.

## Safe 2026 upgrade order

1. Preserve 2025 as a working baseline. Create a `codex/2026-tax-year` branch; do not overwrite `rules/2025` or official 2025 templates. Keep current 2025 returns tagged `tax_year=2025` in the database.
2. Gather final 2026 IRS, FTB, and NY forms/instructions and any corrections. Build a source ledger in Markdown with the URL, revision date, page/line, new value, reviewer and verification date for each changed rule. If final sources are unavailable, keep 2026 disabled.
3. Add `rules/2026` and official `templates/2026`; update code-only values and field mappings in the table above. Make frontend and API select the year of each return rather than assuming a global year. Design database migration/backfill before deploying year choice.
4. Add side-by-side 2025/2026 tests at bracket edges, tax-table bands, filing status, age, dependents, residency changes, treaty cases, state residency and credits. Compare independent agency examples and at least two hand-reviewed returns per supported filing path. Read generated PDFs back and visually inspect every included form, warning and attachment list.
5. Run `taxprep/backend/.venv/Scripts/python.exe -m pytest -q` (Windows) and the frontend production build. Repeat browser tests against a **separate 2026 staging environment and database** with synthetic accounts. Verify cross-account isolation, encryption, CORS, resume, recalculation, PDF download and mobile layouts.
6. Complete the release blockers above, independent tax/security reviews, and a rollback/backup drill. Only then enable 2026 in production, update notices and documentation, and monitor errors. Keep 2025 returns accessible with 2025 rules and forms.

## Operations and privacy notes

The 2025 database currently contains synthetic test records only. Do not migrate unknown historical taxpayer records or paste production credentials into chat, logs, screenshots, Git or Markdown. Check Vercel deployment status for **both** projects after each `main` push; one project can queue while the other builds. The `/health` endpoint proves service availability, not database correctness or tax accuracy. Rotate secrets through the provider UI and document the effect on sessions and encrypted data. Preserve the uncommitted local Render manifest edits (`render.yaml`, `taxprep/render.yaml`) unless their owner decides to discard them; the active hosted route does not use Render.
