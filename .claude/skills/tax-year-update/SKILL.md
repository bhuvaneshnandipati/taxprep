---
name: tax-year-update
description: Update TaxPrep for a new tax year or for revised IRS / California FTB / New York forms. Use when asked to add tax year 2026 (or later), refresh tax forms, update brackets/deductions/credits, handle a "Tax forms published" issue, or when the user supplies new official form PDFs.
---

# Tax-year update playbook

TaxPrep keeps tax law in YAML (`taxprep/backend/rules/<year>/`) and official fill-in PDFs in
`taxprep/backend/app/pdf/templates/<year>/`. The kit in `taxprep/backend/tools/taxyear/` does
the mechanical work; you do the reading and mapping. Run every command from `taxprep/backend`
with the project's Python (`.venv`), e.g. `python -m tools.taxyear.validate --year 2026`.
Each command writes a log to `taxprep/backend/logs/` (git-ignored).

## Ground rules
- Never edit `rules/<old year>/` or `templates/<old year>/` to make a new year work. Old returns keep their year's rules.
- Every number must come from a final agency publication for that year (IRS Rev. Proc./instructions, FTB booklet/tables, NY instructions). Drafts and news articles are not sources. Record each one in `rules/<year>/SOURCES.md`.
- A new year stays `status: draft` in `rules/<year>/meta.yaml` (hidden from the API). Only the user may approve `preview` or `released`; never set `released` yourself.
- Keep the synthetic-data notices until the user confirms the release blockers in `TAX_YEAR_HANDOFF.md` are closed.

## Steps
1. **Start the year** (once): `python -m tools.taxyear.new_year --to <year>`. It copies last year's packs as a draft and writes `SOURCES.md` with every value marked TODO.
2. **Get the official PDFs**: `python -m tools.taxyear.check_forms --year <year> --download`.
   It only accepts a PDF printed for that year and not marked draft.
   - For every form reported as `ASK_USER`, `NOT_YET_PUBLISHED` or `DRAFT_ONLY`, **ask the user** to upload the final official PDF, naming the form and the agency page (FTB: ftb.ca.gov/forms, NY: tax.ny.gov/forms, IRS: irs.gov/forms-instructions). If none are final yet, stop here and say when they are expected; do not use drafts.
   - Import an uploaded file with `python -m tools.taxyear.import_form --year <year> --id <form id> --file <path>` (ids are in `tools/taxyear/forms_manifest.yaml`).
3. **New York tax tables**: `python -m tools.taxyear.ny_tables --year <year>` imports the NYS and NYC tables (taxable income under $65,000) into `rules/<year>/newyork_tables.yaml`. If the page is not up yet, wait or ask the user for it (`--file`).
4. **Update rule values**: read the year's official sources (list in `forms_manifest.yaml` → `references`). For each row in `SOURCES.md`, set the YAML value, copy it into the `<year> value` column, set status `CHANGED` or `CONFIRMED`, and fill the source URL, where (page/line/table) and checked date. If a value cannot be found, leave it TODO and ask the user.
5. **Fix form mappings**: `python -m tools.taxyear.pdf_fields --from <prev> --to <year>`. Fix every `BROKEN` field in `app/pdf/official.py` / `forms.py`, then open each new PDF and compare its line labels with the mapping, since a field name can stay the same while its line moves. Handle year-specific file names (for example, `official.py` hard-codes `2025-540nr.pdf`).
6. **Code that assumes one year**: the validator lists hard-coded previous-year strings. The engines call `load_rules(pack)` with the default year. Before the first second-year release, pass each return's `tax_year` through `app/api/returns.py` → engines → `load_rules(pack, year)` → PDF builders, and make the frontend read the year from the return instead of `TAX_YEAR = 2025`. New tax-law features (new credits, schedules, changed formulas) need engine code plus tests, not only YAML.
7. **Tests**: add `<year>` cases to `taxprep/backend/tests/` with expected values worked from the official instructions/examples (bracket edges, each filing status, 1040-NR + treaty, dual-status, CA 540/540NR, NY IT-201/203). Keep all earlier-year tests passing. Run `python -m pytest -q` and `npm run build` in `taxprep/frontend`.
8. **Validate**: `python -m tools.taxyear.validate --year <year> --target preview`. Fix every ERROR and review the warnings.
9. **Hand off**: commit on a branch, open a PR, update `WORK_LOG.md`, and report to the user what changed, what is still TODO, which forms you still need from them, and that a person must review before raising the status.
