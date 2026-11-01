# Tax-year update kit — November 1, 2026

## Summary
This kit lets the next AI assistant (or a person) move TaxPrep to a new tax year, such as TY2026 filed in 2027, by following one playbook:

- **AI instructions:** `CLAUDE.md` / `AGENTS.md` at the repository root point to `.claude/skills/tax-year-update/SKILL.md`. Claude Code loads these automatically.
- **Commands:** in `taxprep/backend/tools/taxyear/`.
- **Watcher:** a monthly GitHub workflow that opens an issue when new forms are published.

If an official form can't be downloaded, the assistant is told to ask you to upload it.

## Pieces
| Piece | What it does |
|---|---|
| `rules/<year>/meta.yaml` | Release status: `draft` (hidden from the API), `preview` (synthetic data only), `released` (approved for real returns). 2025 is `preview`. |
| `app/engines/rules_loader.py` | `available_years()` hides draft years unless `ALLOW_DRAFT_TAX_YEARS=1`. `/interview/rules/{pack}` refuses unavailable years. |
| `tools/taxyear/new_year.py` | Copies last year's rule packs into a new draft year and writes `SOURCES.md`, a ledger with one row per value (210 for 2025→2026), all marked TODO. |
| `tools/taxyear/check_forms.py` | Downloads official IRS/FTB/NY PDFs from `forms_manifest.yaml`. Reads each PDF to confirm it is printed for the requested year and is not a draft. Anything it can't get is reported as `ASK_USER`. |
| `tools/taxyear/import_form.py` | Adds a PDF the user supplied, under the file name the code expects, after the same year/draft checks. |
| `tools/taxyear/pdf_fields.py` | Diffs form field names between years and flags removed fields that `app/pdf/*.py` still uses. |
| `tools/taxyear/validate.py` | Checks year values, packs and keys against last year, ledger completeness and sources, PDF presence, and hard-coded previous-year strings. `--target released` shows what still blocks a release. |
| `.github/workflows/tax-form-watch.yml` | On the 3rd of each month (or run by hand), checks next year's forms and opens or updates an issue titled "Tax forms published for tax year N". It never changes code. |

Every command writes a log to `taxprep/backend/logs/` (git-ignored).

## How you use it
1. Wait for the "Tax forms published for tax year 2026" issue. Or, from about mid-December, ask an assistant: *"Update TaxPrep for tax year 2026."*
2. The assistant follows the playbook. It downloads forms, asks you for any it can't fetch, updates values with sources, fixes PDF mappings, adds tests and opens a PR.
3. You review the PR. Only you decide when a year moves from draft to preview to released.

## Verification (November 1, 2026)
- Backend suite: **100 passed**, 2 skipped (OCR image tests need Tesseract). This includes 5 new kit tests that run on a temporary copy of `rules/`.
- `check_forms --year 2025` found all 11 official PDFs. `--year 2026` correctly reports nothing final yet: IRS current PDFs are still 2025, and the FTB/NY 2026 addresses return 404.
- A dry run of new_year → validate → import_form (a 2025 PDF was correctly rejected as 2026) → pdf_fields passed. The trial 2026 files were removed afterwards.
- The workflow YAML parses, and its check step was simulated locally. It has not run on GitHub yet: use **Actions → Tax form watch → Run workflow** once after merging.

## Still needed before you can file a real 2026 return
- Final 2026 forms and instructions (expected December 2026 – February 2027), then the playbook steps.
- **Year threading:** engines still read the default year. The playbook's step 5 must be done before 2026 can go live next to 2025.
- The release blockers in `TAX_YEAR_HANDOFF.md`: missing schedules and credits, treaty and dual-status review, a security/privacy review, and independent tax review. The kit doesn't remove these.
