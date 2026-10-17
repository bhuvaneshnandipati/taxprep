"""Residency engine: Green Card Test, Substantial Presence Test (SPT), exempt-individual rules,
dual-status detection.  References: IRC 7701(b); Pub. 519 (2025) ch. 1.

Key rules implemented
- Exempt individual days (F/J/M/Q student, J/Q teacher-trainee) are NOT counted for the SPT, in
  every one of the three look-back years (not only the current year).
- Student: not exempt in a year if already exempt as teacher/trainee/student for any part of more
  than 5 earlier calendar years.  Teacher/trainee: not exempt if exempt in any part of 2 of the
  6 preceding calendar years.  We assume continuous status since `first_entry_year` unless the
  caller supplies `prior_exempt_years` explicitly.
- If the SPT is met but the first non-exempt day of presence falls after Jan 1 of the tax year,
  the taxpayer is a dual-status alien (resident from the residency starting date).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from .rules_loader import DEFAULT_YEAR

STUDENT_VISAS = {"F-1", "J-1 Student", "M-1", "OPT", "STEM OPT", "CPT", "Q-1 Student"}
TEACHER_VISAS = {"J-1 Non-student", "J-1 Researcher", "J-1 Scholar", "J-1 Teacher", "Q-1"}
EXEMPT_VISAS = STUDENT_VISAS | TEACHER_VISAS


@dataclass
class ResidencyResult:
    status: str          # citizen | resident | nonresident | dual_status
    label: str
    form: str            # 1040 | 1040-NR | 1040 (dual-status)
    explanation: str
    form_8843_required: bool = False
    weighted_days: float = 0.0
    dual_status_possible: bool = False      # kept for API compatibility (== status == dual_status)
    residency_start: str = ""               # ISO date, dual-status only
    exempt_days_current: int = 0
    exempt_years_used: int = 0              # calendar years exempt before the tax year
    student_exempt_more_than_5_years: bool = False
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _is_exempt_year(kind: str, year: int, first_year: int, prior_exempt_years: int | None,
                    tax_year: int) -> bool:
    """Was the person an exempt individual in calendar `year` (given continuous status)?"""
    if not first_year or year < first_year:
        return False
    if prior_exempt_years is not None and year == tax_year:
        used = prior_exempt_years
    else:
        used = year - first_year                      # exempt years before `year`
    if kind == "student":
        return used < 5
    # teacher/trainee: exempt unless exempt in any part of 2 of the 6 preceding years
    return min(used, 6) < 2


def determine_residency(*, citizen: bool = False, green_card: bool = False, visa: str = "",
                        first_entry_year: int = 0, days_current: int = 0,
                        days_prior1: int = 0, days_prior2: int = 0,
                        exempt_days_current: int | None = None,
                        exempt_days_prior1: int | None = None,
                        exempt_days_prior2: int | None = None,
                        prior_exempt_years: int | None = None,
                        first_nonexempt_day: str = "",
                        tax_year: int = DEFAULT_YEAR, **_ignored) -> ResidencyResult:
    if citizen:
        return ResidencyResult("citizen", "U.S. Citizen", "1040",
                               "U.S. citizens file Form 1040 regardless of where they live.")
    if green_card:
        return ResidencyResult("resident", "Resident Alien", "1040",
                               "Green Card Test met: lawful permanent residents are resident aliens.")

    kind = "student" if visa in STUDENT_VISAS else "teacher" if visa in TEACHER_VISAS else ""
    warnings: list[str] = []

    # --- exempt days per look-back year --------------------------------------------------
    # Default when the caller does not split days by status: if the year-end visa is an
    # exempt (F/J/M/Q) visa, all days that year were in that status.
    def exempt_days(year: int, days: int, given: int | None) -> int:
        given_days = days if (given is None and kind) else (given or 0)
        given_days = max(0, min(given_days, days))
        k = kind or "student"   # someone now on H-1B etc. who was an F-1 earlier
        if given_days and _is_exempt_year(k, year, first_entry_year, prior_exempt_years, tax_year):
            return given_days
        return 0

    ex0 = exempt_days(tax_year, days_current, exempt_days_current)
    ex1 = exempt_days(tax_year - 1, days_prior1, exempt_days_prior1)
    ex2 = exempt_days(tax_year - 2, days_prior2, exempt_days_prior2)
    c0, c1, c2 = days_current - ex0, days_prior1 - ex1, days_prior2 - ex2

    used = prior_exempt_years if prior_exempt_years is not None else (
        max(0, tax_year - first_entry_year) if first_entry_year else 0)
    more_than_5 = kind == "student" and used >= 5
    exempt_now = ex0 > 0
    f8843 = exempt_now

    weighted = c0 + c1 / 3 + c2 / 6
    calc = (f"Substantial Presence Test counts only non-exempt days: {c0} + {c1}/3 + {c2}/6 = "
            f"{weighted:.1f} weighted days (need >= 183, and >= 31 in {tax_year}).")
    excl = ""
    if ex0 or ex1 or ex2:
        excl = (f" Days excluded as an exempt individual (F/J/M/Q): {tax_year}: {ex0}, "
                f"{tax_year-1}: {ex1}, {tax_year-2}: {ex2}.")

    passes = c0 >= 31 and weighted >= 183
    if not passes:
        label = "Nonresident Alien (Exempt Individual)" if exempt_now else "Nonresident Alien"
        why = ""
        if exempt_now and kind == "student":
            why = (f" As an F/J/M/Q student you are exempt from counting days for your first five "
                   f"calendar years in the U.S. ({first_entry_year}-{first_entry_year + 4}); "
                   f"{tax_year} is calendar year {tax_year - first_entry_year + 1}.")
        elif exempt_now and kind == "teacher":
            why = " As a J/Q teacher, trainee or researcher you are exempt for 2 of every 6 calendar years."
        return ResidencyResult("nonresident", label, "1040-NR",
                               calc + excl + " Test not met — you are a nonresident alien." + why
                               + (" File Form 8843 to claim the excluded days." if f8843 else ""),
                               form_8843_required=f8843, weighted_days=weighted,
                               exempt_days_current=ex0, exempt_years_used=used,
                               student_exempt_more_than_5_years=more_than_5, warnings=warnings)

    # --- SPT met: is the residency starting date after Jan 1? ---------------------------
    start: date | None = None
    if first_nonexempt_day:
        try:
            start = date.fromisoformat(first_nonexempt_day)
        except ValueError:
            warnings.append("Could not read the residency start date; assumed January 1.")
    # Present all year with no exempt days and not newly arrived -> full-year resident.
    days_in_year = 366 if (tax_year % 4 == 0 and (tax_year % 100 or tax_year % 400 == 0)) else 365
    mid_year = (ex0 > 0) or (first_entry_year == tax_year and days_current < days_in_year) or \
               (start is not None and start > date(tax_year, 1, 1))
    if mid_year:
        if start is None:
            # Approximation: non-exempt presence is assumed to be the last c0 days of the year.
            start = date.fromordinal(date(tax_year, 12, 31).toordinal() - c0 + 1)
            warnings.append("Residency starting date estimated from your non-exempt days; enter the exact "
                            "date (first day in the U.S. in non-exempt status) for an exact return.")
        return ResidencyResult(
            "dual_status", "Dual-Status Alien", "1040",
            calc + excl + f" Test met. Your residency starting date is {start.isoformat()} (first day present "
            f"in non-exempt status), so you are a nonresident alien before that date and a resident alien "
            f"from that date. You file a dual-status return: Form 1040 marked 'Dual-Status Return' with a "
            f"Form 1040-NR attached as a statement for the nonresident period. Dual-status filers cannot use "
            f"the standard deduction or file jointly (unless electing full-year residency with a U.S. spouse).",
            form_8843_required=f8843, weighted_days=weighted, dual_status_possible=True,
            residency_start=start.isoformat(), exempt_days_current=ex0, exempt_years_used=used,
            student_exempt_more_than_5_years=more_than_5, warnings=warnings)

    return ResidencyResult("resident", "Resident Alien", "1040", calc + excl + " Test met — you are a resident "
                           "alien for the whole year and file Form 1040 like a U.S. citizen.",
                           weighted_days=weighted, exempt_years_used=used,
                           student_exempt_more_than_5_years=more_than_5, warnings=warnings)
