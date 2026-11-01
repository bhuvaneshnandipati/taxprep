# Adding another state to TaxPrep

TaxPrep fully supports California (540 / 540NR) and New York (IT-201 / IT-203), plus the states with no wage income tax (`NO_INCOME_TAX` in `registry.py`). This guide lists every file a new state touches, in order, so a person or an AI assistant can add one, for example New Jersey (NJ-1040).

Use made-up data in all tests. Every number must come from the state's final instructions for that tax year.

## 1. Rules (numbers only, no code)
Create `taxprep/backend/rules/<year>/<pack>.yaml`, for example `newjersey.yaml`. It holds `year`, `state`, the brackets per filing status, the standard deduction or exemptions, credit amounts and limits, and comments with the source URL and page for each block. Copy the shape of `newyork.yaml` or `california.yaml`.

Add the pack name to `LEDGER_PACKS` in `taxprep/backend/tools/taxyear/common.py`. The yearly update kit then tracks and validates its values.

## 2. Engine
Copy `taxprep/backend/app/engines/states/_template.py` to `<pack>.py` and implement `compute()`:
- **State AGI.** What it starts from (federal AGI, wages), and its additions and subtractions. Does the state follow federal treaty exclusions? California does not; see `california.py`.
- **Deductions and exemptions.**
- **Tax.** If the instructions require a tax table below some income, compute the table midpoint, as `federal.table_midpoint` does.
- **Part-year and nonresident method.** States use income ratios, sourced income or prorated credits differently.
- **Credits:** dependents, renters, earned-income credit and others.
- **Lines** needed by the PDF and the results screen: `agi`, `taxable_income`, `total_tax`, `withholding`, `refund`.

Register it in `registry.py`: import the module in `compute_state` and add `"XX": module.compute` to `engines`.

## 3. Official PDF
1. Add the form to `taxprep/backend/tools/taxyear/forms_manifest.yaml` (id, title, template file name, URL with `{year}`).
2. Download it: `python -m tools.taxyear.check_forms --year <year> --download`. If it can't be downloaded, ask the user for the PDF and run `tools.taxyear.import_form`.
3. List its fields: `python -m tools.taxyear.form_fields app/pdf/templates/<year>/<file>.pdf`. This shows the line number or label next to each field.
4. Write a filler in `app/pdf/official.py` (copy `ny_it201`) and call it from `build_package` in `app/pdf/forms.py`, in the `if st["form"] != "none":` block.

## 4. Mailing
In `rules/<year>/mailing.yaml`, add `state.<XX>.no_payment` / `payment` (USPS) and `private_delivery.state.<XX>` (UPS/FedEx street address), plus `due_dates.<XX>` and `payment.<XX>`. Take these from the state's official "where to mail" page and record the URL and check date in a comment.

## 5. Website
In `taxprep/frontend/app/return/[id]/page.tsx`, add `["XX", "State name"]` to `STATES`. If the state needs extra questions (renter, county, city tax), add fields in the income step's state section and matching fields in `IncomeIn` (`app/schemas.py`) and `StateInput`.

## 6. Tests
Add `taxprep/backend/tests/test_<pack>.py` with:
- at least one full-year and one part-year case, with values worked by hand from the instructions or the state's own examples;
- a PDF test that builds the package and checks the key lines (see `tests/test_supplemental_forms.py`);
- bracket-edge cases.

Then run `cd taxprep/backend && python -m pytest -q` and `cd taxprep/frontend && npm run build`.

## 7. Docs
Update `README.md` (supported states), `taxprep/FIXES.md` (known limits for the new state) and `WORK_LOG.md`.

## Each new year
The yearly update kit (`.claude/skills/tax-year-update/SKILL.md`) covers every state in `LEDGER_PACKS` and every form in the manifest. A new state is then maintained like CA and NY.
