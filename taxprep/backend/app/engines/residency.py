"""Residency engine: Green Card Test, Substantial Presence Test, exempt-individual rules."""
from dataclasses import dataclass
from .rules_loader import load_rules, DEFAULT_YEAR

STUDENT_VISAS = {"F-1", "J-1 Student", "M-1", "OPT", "STEM OPT", "CPT"}
TEACHER_VISAS = {"J-1 Non-student"}

@dataclass
class ResidencyResult:
    status: str          # citizen | resident | nonresident
    label: str
    form: str            # 1040 | 1040-NR
    explanation: str
    form_8843_required: bool = False
    weighted_days: float = 0.0
    dual_status_possible: bool = False

def determine_residency(*, citizen: bool, green_card: bool, visa: str = "",
                        first_entry_year: int = 0, days_current: int = 0,
                        days_prior1: int = 0, days_prior2: int = 0,
                        tax_year: int = DEFAULT_YEAR) -> ResidencyResult:
    if citizen:
        return ResidencyResult("citizen", "U.S. Citizen", "1040",
                               "U.S. citizens file Form 1040 regardless of residence.")
    if green_card:
        return ResidencyResult("resident", "Resident Alien", "1040",
                               "Green Card Test met: lawful permanent residents are resident aliens.")

    years_in = tax_year - first_entry_year + 1 if first_entry_year else 99
    if visa in STUDENT_VISAS and years_in <= 5:
        return ResidencyResult(
            "nonresident", "Nonresident Alien (Exempt Individual)", "1040-NR",
            f"F/J/M student exempt-individual rule: calendar years 1-5 ({first_entry_year}"
            f"-{first_entry_year + 4}) are excluded from the Substantial Presence Test. "
            f"This is year {years_in}. Form 8843 required.",
            form_8843_required=True)
    if visa in TEACHER_VISAS and years_in <= 2:
        return ResidencyResult(
            "nonresident", "Nonresident Alien (Exempt Individual)", "1040-NR",
            f"J-1 teacher/researcher exempt rule: first 2 calendar years excluded from the SPT. "
            f"This is year {years_in}. Form 8843 required.",
            form_8843_required=True)

    cfg = load_rules("federal", tax_year)
    weighted = days_current + days_prior1 / 3 + days_prior2 / 6
    passes = days_current >= 31 and weighted >= 183
    calc = (f"Substantial Presence Test: {days_current} + {days_prior1}/3 + {days_prior2}/6 "
            f"= {weighted:.1f} weighted days (need >=183 and >=31 current-year days).")
    if passes:
        dual = first_entry_year == tax_year and days_current < 365
        note = (" You arrived during the tax year, so you may be a dual-status alien for your "
                "first year; this return is prepared as full-year resident, the more common election."
                if dual else "")
        return ResidencyResult("resident", "Resident Alien", "1040", calc + " Test met." + note,
                               weighted_days=weighted, dual_status_possible=dual)
    return ResidencyResult("nonresident", "Nonresident Alien", "1040-NR",
                           calc + " Test not met.",
                           form_8843_required=visa in STUDENT_VISAS | TEACHER_VISAS,
                           weighted_days=weighted)
