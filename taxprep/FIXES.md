# TaxPrep — Audit & Fix Report (Oct 2026)

**Goal of the app:** prepare TY2025 returns for international students and visa holders. It covers the residency test, Form 8843, Form 1040-NR with tax treaties, dual-status returns, and CA/NY state returns. It produces the **official agency forms, filled in**, ready to sign and mail.

## 1. Tax-law bugs fixed (these caused wrong refunds)

| # | Area | Bug | Fix |
|---|------|-----|-----|
| 1 | Residency | Exempt (F/J/M/Q) days were only excluded for the current year. Prior-year student days counted toward the Substantial Presence Test. | Exempt days are excluded in all three look-back years. The 5-year student rule and the 2-of-6 teacher/trainee rule are applied per year. |
| 2 | Residency | F-1 → H-1B in the same year (the most common case) was treated as a full-year **resident**, even when the F-1 days were exempt. | The user enters the F/J/M/Q days for each year, and only non-exempt days are counted. Example: F-1 since 2021, H-1B Oct 1 2025 → 92 days → **nonresident** (was wrongly resident). |
| 3 | Residency | People who arrived mid-year were filed as **full-year residents**, with the standard deduction. That election only exists for people married to a U.S. resident. | True **dual-status** mode: Form 1040 marked "Dual-Status Return", no standard deduction, no joint/HOH, no EITC or education credits, plus an NR-period statement. |
| 4 | 1040-NR | Bank interest was taxed for nonresidents. | Excluded (IRC 871(i)/(h)). |
| 5 | 1040-NR | Capital gains were taxed at graduated/LTCG rates. | 30% on Schedule NEC if present 183+ days; otherwise not taxed. |
| 6 | 1040-NR | Dividends were dropped entirely ("handled on Schedule NEC", but they never were). | Schedule NEC at 30% or the treaty rate (e.g. India 25%, China 10%). |
| 7 | 1040-NR | 1099-NEC / self-employment income was **silently deleted**. | Taxed as effectively connected income, with no SE tax (nonresidents are exempt from it). |
| 8 | 1040-NR | 1042-S income and withholding weren't supported. | Treaty-exempt pay (codes 17-20), scholarship (code 16) and withholding (line 25g) added. No double exemption when the employer already applied the treaty. |
| 9 | 1040-NR | Itemized deductions had to be typed in by hand. | State tax withheld (W-2 box 17) is used automatically, plus U.S. charitable gifts. |
| 10 | Treaty | Canada flagged Form 8833 as required. | Not required for dependent-personal-services claims (Reg. 301.6114-1(c)(1)(ii)). |
| 11 | Treaty | China Art. 20 benefit was lost after becoming a resident alien. | Kept via the saving-clause exception, with Form 8833. |
| 12 | Federal | Tax used the exact formula, not the IRS **Tax Table**, so it was off by up to ~$4. Python's banker's rounding also made $x.50 round down. | Tax Table midpoint method below $100k, and half-up rounding everywhere. |
| 13 | Federal | Unlimited capital losses; LT gains weren't netted against ST losses. | $3,000 ($1,500 MFS) loss limit; net capital gain = min(LT, total). |
| 14 | Federal | Credit for Other Dependents could exceed the tax. Education credits were applied after the CTC. | Correct ordering and limits. |
| 15 | Federal | EITC for people with no children ignored the age 25-64 rule (most students are under 25). | Age checked. EIC table midpoint method. |
| 16 | Federal | SE tax was charged on net earnings under $400. | $400 threshold. |
| 17 | Federal | OBBBA items were missing. | SALT cap $40k (phase-down above $500k); Schedule 1-A tips and overtime deductions. |
| 18 | California | **CA ignored that it does not follow tax treaties.** Treaty-exempt wages and NRA-exempt interest/gains were left out of CA income. | CA AGI is rebuilt on a worldwide basis, with the add-back shown on line 16. |
| 19 | California | 2025 brackets, dependent credit ($480 → $475), renter's-credit limits and exemption phase-out were all wrong. | Replaced with FTB's published 2025 amounts. |
| 20 | California | 540NR used a simple income ratio, didn't prorate exemption credits, and the phase-out was a cliff. | Official 540NR method (tax on all income × CA rate, prorated credits); $6 per $2,500 phase-out. |
| 21 | New York | No tax-benefit recapture above $107,650 NY AGI. | First recapture tier added. Above it, the app shows a warning. |
| 22 | New York | NY-source income could exceed federal AGI. | Capped. |
| 23 | Mailing | 1040 refunds were sent to **Fresno**, which no longer processes paper returns. | Addresses for 2025 rechecked on irs.gov (CA → Ogden, NY → Kansas City, 1040-NR → Austin/Charlotte). |
| 24 | 8843 | Line 4b always equalled all days present, and line 12 was always "No". | Computed from the residency engine. |
| 25 | FICA | Not flagged. | Exempt F/J students who had Social Security/Medicare withheld get a Form 843/8316 refund item. |

## 2. Output: official forms instead of look-alikes

The old PDF *drew* look-alike forms, which the IRS and FTB won't accept. The app now fills the **real 2025 fill-in PDFs** published by the IRS, FTB and NY DTF (bundled in `backend/app/pdf/templates/2025/`):

- Form 1040
- Form 1040-NR
- Schedule 1
- Schedule NEC
- Schedule OI
- Form 8843
- CA 540
- CA 540NR
- NY IT-201
- NY IT-203

The package also includes a cover sheet with the explanation, checklist and mailing addresses, plus a dual-status statement when needed. Each form is flattened before merging, because the agencies reuse field names across forms. Every value is checked by tests that read the filled PDFs back.

## 3. App / security bugs fixed

- **Admin takeover:** anyone could register the `ADMIN_EMAILS` address first and become admin. That email now needs `ADMIN_SETUP_CODE` to register.
- **Code execution:** interview rules used `eval()` on admin-editable YAML. Replaced with a whitelisted expression evaluator, and rule edits are validated.
- **Encryption:** SSN/ITIN and passport number are encrypted at rest (`DATA_KEY`, Fernet).
- **Secrets:** the app refuses to start on Render with the default `JWT_SECRET`.
- **Session length:** login sessions now last 4 h (was 30 min, which lost work mid-return).
- **Validation:** inputs are checked (filing status enum, non-negative amounts, days ≤ 366). Rule-pack names are validated against path tricks.
- **OCR:**
  - `48250` used to be read as `482` + `50`.
  - HEIC uploads failed; they now work via pillow-heif.
  - Applying the same document twice duplicated the W-2.
- **Resume:** there was **no way to resume a return**. Opening a saved return showed blank defaults. Added `GET /returns/{id}`, `DELETE /returns/{id}`, and stale results are cleared when inputs change.
- **Interview:** it re-asked the residency questions and let the client set its own residency status. Residency is now injected server-side.
- **Frontend:**
  - Number fields lost focus on every keystroke (components were defined inside render).
  - Decimals and negative amounts couldn't be typed.
  - Labels said "CA" even for NY.
  - The download link was revoked before the click.
  - Wrong defaults were pre-filled (India, F-1, 2023, 365 days).
- **Docker:** `NEXT_PUBLIC_API_URL` was passed at run time, but it is baked in at build time. Added `.gitignore`.

## 4. Verification

- `pytest`: **78 tests pass**. The engine values are hand-computed from the 2025 Tax Table and the FTB/NY schedules (see `backend/BUILD_LOG.txt`).
- I rendered and visually checked four sample packages: India NRA + CA 540, China NRA + NY IT-203, citizen + CA 540NR, and H-1B dual-status + NY IT-201.
- `next build`: clean, with strict TypeScript.

## 5. Known limits (shown to the user in the app/PDF where relevant)

- **Supplemental forms not generated** (listed as "complete and attach yourself"):
  - Schedule A (1040 / 1040-NR)
  - Schedules 1-A, 2, 3, D, SE, 8812
  - Forms 8949, 8863, 8959, 8960, 8833
  - CA Schedule CA
- **California:**
  - CalEITC / YCTC not computed.
  - CA tax uses the rate schedule, which can be ±$1-2 vs the FTB tax table.
  - Health-coverage penalty not computed.
- **New York:** NYC/Yonkers tax, NY EITC, the household credit, and recapture above the first tier are not computed.
- **Dual-status:** non-wage income is assumed to be received in the resident period. The full-year-resident election (6013(g)/(h)) isn't prepared.
- **Treaty time limits** are not enforced per country; the user is warned to confirm with Pub. 901.
- **Other states:** only CA, NY and the no-income-tax states are supported. Other states return a clear error.
