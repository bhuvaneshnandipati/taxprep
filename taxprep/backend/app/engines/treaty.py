"""Tax treaty engine: looks up country benefits from the versioned treaty pack (rules/<year>/treaties.yaml).

Benefit codes
  standard_deduction        India Art. 21(2): students may claim the standard deduction on 1040-NR
  wage_exemption            first $N of personal-services income exempt (student articles)
  wage_exemption_threshold  all employment income exempt if total <= $N (e.g. Canada Art. XV)
  scholarship_exemption     scholarship/fellowship grants exempt (amount null = unlimited)

Resident aliens (by SPT) can keep a benefit only where the treaty's saving clause has an
exception for it (`resident_alien_ok: true`, e.g. China Art. 20) — Form 8833 is then required.
"""
from .rules_loader import load_rules

_ALIASES = {"korea": "South Korea", "republic of korea": "South Korea", "prc": "China",
            "people's republic of china": "China", "peoples republic of china": "China",
            "usa": "", "united states": ""}


def _norm(country: str) -> str:
    c = (country or "").strip()
    return _ALIASES.get(c.lower(), c)


def _lookup(pack: dict, country: str):
    c = _norm(country)
    for k, v in pack.items():
        if k.lower() == c.lower():
            return k, v
    return c, []


def apply_treaty(country: str, *, is_student: bool, wages: float, scholarship: float,
                 resident_alien: bool = False, years_in_us: int = 0) -> dict:
    out = {"country": _norm(country), "wage_exempt": 0.0, "scholarship_exempt": 0.0,
           "standard_deduction": False, "articles": "", "form_8833_required": False,
           "notes": [], "warnings": []}
    rules = load_rules("treaties")
    name, benefits = _lookup(rules.get("treaties", {}), country)
    out["country"] = name
    arts = []
    for b in benefits:
        applies = ("student" in b["applies_to"] and is_student) or ("employee" in b["applies_to"])
        if not applies:
            continue
        if resident_alien and not b.get("resident_alien_ok"):
            continue
        max_years = b.get("max_years")
        if max_years and years_in_us and years_in_us > max_years:
            out["warnings"].append(f"{name} Art. {b['article']} is limited to {max_years} years; "
                                   f"benefit not applied (year {years_in_us} in the U.S.).")
            continue
        used = False
        if b["benefit"] == "standard_deduction":
            out["standard_deduction"] = used = True
        elif b["benefit"] == "wage_exemption":
            amt = min(wages, b["amount"]) if b["amount"] else wages
            if amt > 0:
                out["wage_exempt"] = max(out["wage_exempt"], amt); used = True
        elif b["benefit"] == "wage_exemption_threshold":
            if 0 < wages <= (b["amount"] or 0):
                out["wage_exempt"] = wages; used = True
        elif b["benefit"] == "scholarship_exemption":
            amt = scholarship if b["amount"] is None else min(scholarship, b["amount"])
            if amt > 0:
                out["scholarship_exempt"] = amt; used = True
        if used:
            arts.append(b["article"])
            out["notes"].append(b["note"])
            if resident_alien or b.get("form_8833_required"):
                out["form_8833_required"] = True
    out["articles"] = ", ".join(f"Art. {a}" for a in dict.fromkeys(arts))
    if arts and not resident_alien:
        out["warnings"].append("Most treaty student articles have time limits and conditions (IRS Pub. 901). "
                               "Confirm you still qualify, and give your employer Form 8233 next year.")
    return out


def fdap_dividend_rate(country: str, default: float = 0.30) -> float:
    rates = load_rules("treaties").get("dividend_rates", {}) or {}
    name, _ = _lookup({k: None for k in rates}, country)
    for k, v in rates.items():
        if k.lower() == name.lower():
            return float(v)
    return default
