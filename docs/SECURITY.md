# TaxPrep security and privacy — November 1, 2026

TaxPrep is set up for real returns by a limited number of users: anyone can sign up until the account limit is reached. This page records what protects the data, what changed, and the settings the owner must keep.

## Why the earlier version was not safe for real SSNs
| Earlier gap | Risk | Fix (this release) |
|---|---|---|
| Anyone on the internet could create unlimited accounts | Abuse of the free database | **Capped sign-up:** anyone may register until `MAX_USERS` accounts exist (default 25); at most `MAX_SIGNUPS_PER_IP_PER_DAY` (default 3) new accounts per network per day. Optional `REGISTRATION_EMAILS` restricts sign-up to listed emails. |
| Unlimited password guesses | Account takeover by guessing | **Lockout:** 5 failures per email (or 20 per IP) in 15 minutes blocks sign-in. Stored in the database, so it works on serverless. |
| Login token (JWT) kept in browser `localStorage` for 4 hours, and sign-out only cleared the browser | Any injected script could steal the token, and a stolen token stayed valid | **Server-side sessions** in an `HttpOnly; Secure; SameSite=Strict` cookie that page scripts cannot read. Sign-out deletes the session on the server. Sessions end after 60 minutes of inactivity and 12 hours at most. Only a SHA-256 hash of each token is stored. |
| No cross-site request protection was needed for bearer tokens, but cookies need it | Another site could submit requests with the user's cookie | **CSRF guard:** cookie-authenticated changes must carry an `X-TaxPrep` header, which other sites cannot add. |
| Only SSN and passport number were encrypted; names, addresses, DOB, wages, results and OCR output were plain JSON | A database leak would expose almost everything | **Whole-return encryption:** profile, answers, income, results, OCR output and the account name are Fernet-encrypted (AES-128-CBC + HMAC-SHA256) with `DATA_KEY`. Existing plaintext rows still open and are encrypted on their next save. |
| The full SSN was sent back to the browser on every resume | Exposure on shared screens, in browser memory and in logs | **Masked identifiers:** the API returns `***-**-1234`. Saving the masked value keeps the stored number, and the PDF still uses the real one. |
| No content-security policy on the website | Injected scripts could run and send data elsewhere | **CSP** (`connect-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`), HSTS, nosniff, no-referrer, Permissions-Policy. |
| No way to delete your data | Data kept forever | **Delete my account** on the dashboard removes the account, every return, every document and all sessions. |

Already in place before this release: bcrypt-SHA256 passwords, per-account return isolation, input validation, `no-store` caching, uploaded images are not stored (only reviewed values), and production start-up checks for secrets.

## How the website talks to the API
The browser only talks to the TaxPrep website. Calls to `/api/*` are forwarded by Next.js to the API (`API_ORIGIN`, falling back to `NEXT_PUBLIC_API_URL`). The cookie therefore belongs to the website's own address, and the browser never contacts the API directly.

## Settings to keep in Vercel
| Project | Variable | Value |
|---|---|---|
| taxprep-api | `MAX_USERS` (optional) | Maximum number of accounts; default 25. Set `0` to close sign-up. |
| taxprep-api | `DATA_KEY` | Already set. **Back it up somewhere safe outside Vercel** (e.g. a password manager). If it is lost, every encrypted return becomes unreadable. Never change it without a re-encryption plan. |
| taxprep-api | `JWT_SECRET`, `DATABASE_URL`, `PRODUCTION=1`, `CORS_ORIGINS` | Unchanged. |
| taxprep (frontend) | `API_ORIGIN` (optional) | `https://taxprep-api.vercel.app`. The existing `NEXT_PUBLIC_API_URL` already works as the fallback. |

Optional tuning: `MAX_SIGNUPS_PER_IP_PER_DAY`, `REGISTRATION_EMAILS`, `SESSION_IDLE_MINUTES`, `SESSION_MAX_HOURS`, `MAX_FAILED_PER_EMAIL`, `MAX_FAILED_PER_IP`, `LOCKOUT_MINUTES`.

## Remaining risks you accept by self-hosting
- **Backups:** Neon Free keeps limited history. Download your filed return PDFs and keep them; the IRS asks you to keep records for at least 3 years.
- **Forgotten password:** there is no email reset, because that would need an email service. An admin can delete the account so you can register again.
- **Provider access:** Vercel and Neon operate the servers. Data is encrypted with `DATA_KEY`, but that key is also stored in Vercel, so someone with full control of your Vercel account could read the data. Protect your Vercel and GitHub accounts with two-factor authentication.

## Verification
- Backend tests: 105 passed, 2 skipped (OCR images need Tesseract). These include the cookie flags, server-side sign-out, the CSRF block, lockout, invite-only sign-up, idle expiry, account deletion, whole-column encryption and SSN masking.
- Browser end-to-end run on a local stack: sign-up → return with SSN → calculate ($925 federal / $617 CA, matching the known example) → PDF → sign-out (API then returns 401) → sign-in → resume. The cookie was HttpOnly and SameSite=Strict, `localStorage` was empty, the SSN was shown masked, saving the masked SSN kept the real one, the PDF contained the real SSN, and there were no console errors.
