# TaxPrep hosted preview

Status, October 17, 2026 (America/Los_Angeles): the separate Vercel Hobby frontend and FastAPI backend are connected to a Neon Free PostgreSQL database. This is a **synthetic-data preview only**, not a filing-ready or production tax service.

## Addresses and services

- Frontend: https://taxprep-mu.vercel.app (`taxprep`, root `taxprep/frontend`)
- API: https://taxprep-api.vercel.app (`taxprep-api`, root `taxprep/backend`)
- Database: Neon Free project `taxprep-2025-preview` in AWS US East 2. It holds only synthetic test accounts and returns from this work.
- Source: https://github.com/bhuvaneshnandipati/taxprep

No Render service is used. These are separate from the portfolio website. Vercel Hobby is for personal, non-commercial use and has usage limits; Neon Free also has quota and backup limits.

## Configuration

The backend has private `DATABASE_URL`, `JWT_SECRET`, and `DATA_KEY` values, plus `PRODUCTION=1`, `DB_SSLMODE=require`, and exact `CORS_ORIGINS=https://taxprep-mu.vercel.app`. Never put private values in frontend variables or source control. Its hosted rules are read-only; reviewed rule changes require a commit and redeployment.

The frontend has public Config variables `NEXT_PUBLIC_API_URL=https://taxprep-api.vercel.app` and `NEXT_PUBLIC_ENABLE_API=true` for Production and Preview. A frontend redeployment is needed after changing either variable.

## Verification and limits

Local checks passed: 95 backend tests, with two Tesseract image checks skipped, a production frontend build, and a synthetic local browser journey. Hosted API checks passed health, exact-origin CORS, registration, cross-account isolation, save/resume, calculation, and PDF download with synthetic wages of $45,000 and withholding of $4,200 federal/$1,400 California. The example produced $925 federal and $617 California refunds; these figures are test outputs, not a tax-correctness certification.

The public browser journey also passed synthetic registration, return creation and saving, and calculation. Selecting the California renter credit yielded $925 federal and $677 California refunds. The difference from the API-only state result is the $60 renter credit.

Scanned-image OCR is unverified on Vercel. Manual entry remains available. Provider request-size limits may be smaller than the app's upload limit. E-filing is unsupported. Authentication needs abuse controls, account recovery/verification, and a security/privacy review. Federal, treaty, dual-status, and state calculations and forms require independent review for current law and individual applicability before any real taxpayer data is used.

Only synthetic data may be entered or uploaded. The UI and PDFs label this preview accordingly.

The detailed 2025 release blockers, year-specific code map, official-source links and 2026 conversion steps are in [TAX_YEAR_HANDOFF.md](TAX_YEAR_HANDOFF.md).
