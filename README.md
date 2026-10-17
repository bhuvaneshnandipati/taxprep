# TaxPrep

Tax year 2025 federal and CA/NY return preparation for international students and visa holders.
Application source is in `taxprep/`.

## Use as a hosted website

An existing frontend is at https://taxprep-mu.vercel.app. Its hosted backend and database are not yet verified. Use synthetic test data only. [Website setup](WEBSITE.md) documents the free Vercel + Neon personal-preview route and the pending Neon authorization. Render is excluded.

## Run locally

Install Python 3.12 and Node.js 22 (including npm). In PowerShell,
from the repository root:

```powershell
cd taxprep
powershell -ExecutionPolicy Bypass -File .\Start-TaxPrep.ps1 -Setup
```

Open http://localhost:3000. The API is at http://localhost:8000/docs.
On later runs, use the same command without `-Setup`. Keep the terminal open;
press Ctrl+C to stop the app. The launcher uses SQLite, installs backend packages
in a virtual environment, and saves reusable encryption/session keys in
`taxprep/backend/.local-secrets.json` (excluded from Git). Back up that file with
`taxprep/backend/taxprep.db`; losing the key makes saved identifiers unreadable.
Tesseract is optional for manual entry and required for image OCR uploads.

## Use the application

1. Choose **Create account**, then sign in.
2. Select **Start 2025 return** on the dashboard.
3. Enter your taxpayer details and select **Save & continue**.
4. Complete visa, arrival, and days-present information for the residency determination.
5. Answer the interview and enter income, withholding, deductions, and state details.
   If uploading documents, review the extracted values before applying them.
6. Select **Calculate my return** and review the results and warnings.
7. Select **Download filing package (PDF)**. Review its checklist and any attachments
   marked as not generated. Sign and follow the filing instructions after completing
   those missing attachments. The application does not e-file.
8. Reopen a saved return from the dashboard to continue. After editing income,
   calculate again and download a fresh package.

## This update

- Restores the saved tax-engine, return-resume, official-form, and security fixes.
- Generates the official 2025 Schedule 2 for calculated self-employment tax,
  Additional Medicare Tax, and net investment income tax. Required supporting
  Schedule SE / Forms 8959 and 8960 remain listed as missing when applicable.
- Makes the backend test setup work on Windows; OCR image tests require Tesseract.
- Upgrades Next.js to 16.4.2 and React to 19.3.1, with a verified webpack production build.

See [audit and remaining limitations](taxprep/FIXES.md) and
[deployment instructions](taxprep/DEPLOY.md). This application currently prepares TY2025 only.

## Validation and remaining work

October 16, 2026: 95 backend checks passed; 2 image-OCR checks skipped without Tesseract. The suite covers engine examples, API authorization, encrypted identifiers, PDF field mapping, and new production-configuration/password/finite-money protections. Frontend production build passed. A local browser E2E using synthetic data verified registration, profile/residency, calculation, PDF download, sign-out/sign-in, and saved-return resume. The $45,000 single-citizen sample produced $925 federal and $617 CA refunds.

Hosted E2E, independent full tax correctness, broader security review and production readiness remain unverified. See [remaining limitations](taxprep/FIXES.md). Generated PDFs are marked as synthetic test previews, not filing-ready returns.
