"""TEMPLATE for a new state engine — copy to <state>.py (e.g. newjersey.py) and fill in.
Not registered; see docs/ADDING_A_STATE.md for every file a new state touches.

Contract: compute(inp: StateInput, fed) -> StateResult
  - inp: withholding (W-2 box 17 for this state), full_year_resident, state_source_income,
         dependents, itemized, fed_input (the FederalInput, for states that start from wages
         or that do not follow federal treaty exclusions)
  - fed: FederalResult (fed.lines["agi"], fed.filing_status, ...)
  - lines must include: agi (state AGI), taxable_income, total_tax, withholding, refund
    (positive = refund, negative = amount owed). Keep every number in rules/<year>/<state>.yaml.
"""
from .registry import StateInput, StateResult
from ..rules_loader import load_rules
from ..federal import marginal_tax, rnd

STATE = "XX"          # two-letter code
PACK = "statename"    # rules/<year>/<PACK>.yaml


def compute(inp: StateInput, fed) -> StateResult:
    R = load_rules(PACK)
    fs = fed.filing_status
    ex, warn = [], []
    agi = fed.lines["agi"]                      # 1. state AGI: start point + state additions/subtractions
    deduction = R["standard_deduction"][fs]     # 2. deductions / exemptions
    taxable = max(0.0, agi - deduction)
    tax = marginal_tax(taxable, R["brackets"][fs])   # 3. tax (use the state's tax table if it requires one)
    if not inp.full_year_resident:              # 4. part-year / nonresident method (varies by state)
        ratio = min(1.0, (inp.state_source_income or 0.0) / agi) if agi else 0.0
        tax *= ratio
        ex.append(f"Nonresident/part-year: tax prorated by state-source income ({ratio:.1%}).")
    credits = 0.0                               # 5. credits
    total = max(0.0, tax - credits)
    lines = {"agi": rnd(agi), "deduction": rnd(deduction), "taxable_income": rnd(taxable),
             "total_tax": rnd(total), "withholding": rnd(inp.withholding),
             "refund": rnd(inp.withholding - total)}
    return StateResult(state=STATE, form="FORM-ID", lines=lines, explanations=ex, warnings=warn)
