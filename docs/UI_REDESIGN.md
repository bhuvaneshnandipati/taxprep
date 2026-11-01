# TaxPrep UI redesign — November 1, 2026

## Summary
The frontend was restyled from a plain form layout into a "ledger" look. It uses warm paper, white form sheets, an electric-blue primary action, a highlighter-yellow focus colour and monospace form-line numbers. Only styles and markup changed. API calls, tax logic, validation, routes and the synthetic-data notice are unchanged.

## What changed
| Area | Change |
|---|---|
| Design tokens (`tailwind.config.ts`) | New palette, Bricolage Grotesque / Geist / Geist Mono fonts, sheet shadows, a "post" animation. Existing token names (`formblue`, `refund`, `owe`, …) were kept, so page markup didn't need renaming. |
| Components (`app/globals.css`) | Pill buttons, rounded inputs with a yellow highlighter focus ring, sheet cards, segmented chips, `.mark` highlighter text. Respects `prefers-reduced-motion`. |
| Header/footer (`app/layout.tsx`) | Sticky header with logo, tax-year badge and nav. Skip link. Restyled yellow PREVIEW notice. Footer with source link. |
| Sign-in (`app/page.tsx`) | Two-column hero, with an example 1040 card whose lines "post" in turn. The account card has a segmented Sign in / Create account toggle. |
| Dashboard | Larger heading, hover-lift return cards, pill status badges, a new empty state. |
| Return wizard | Progress bar, numbered step pills (✓ on completed steps, "Step n / 5"), and the form sits on a white sheet. |
| Ledger | Refund/owe colours updated. Darker mobile ledger bar. |

The hero example ($45,000 wages, $15,750 standard deduction, $3,275 tax, $4,200 withheld, $925 refund) matches the synthetic single-filer test documented in `README.md`. It is decorative and labelled "Example".

## Verification
- `npx tsc --noEmit` passed. `npm run build` (Next.js 16.4.2, webpack) passed.
- Playwright screenshots at 1366×900 and 390×844, using a mocked API: no horizontal overflow. Screenshots are in `docs/ui-redesign/`.
- The backend was not touched, so no backend tests were re-run.

## Deployment
Merging to `main` lets Vercel redeploy https://taxprep-mu.vercel.app as before. Vercel builds a preview for the PR branch first.

## Open items
- The live sign-in → calculate → PDF flow was not re-run against the hosted API from this environment. Do a quick check on the Vercel preview URL before merging.
