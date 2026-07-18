"""Tax treaty engine: looks up country benefits from the versioned treaty pack."""
from .rules_loader import load_rules

def apply_treaty(country: str, *, is_student: bool, wages: float, scholarship: float) -> dict:
    out = {"country": country, "wage_exempt": 0.0, "scholarship_exempt": 0.0,
           "standard_deduction": False, "articles": "", "form_8833_required": False, "notes": []}
    rules = load_rules("treaties").get("treaties", {})
    arts = []
    for b in rules.get(country, []):
        applies = ("student" in b["applies_to"] and is_student) or ("employee" in b["applies_to"])
        if not applies:
            continue
        if b["benefit"] == "standard_deduction":
            out["standard_deduction"] = True
        elif b["benefit"] == "wage_exemption":
            out["wage_exempt"] = min(wages, b["amount"] or wages)
        elif b["benefit"] == "wage_exemption_threshold":
            if wages <= (b["amount"] or 0):
                out["wage_exempt"] = wages
        elif b["benefit"] == "scholarship_exemption":
            out["scholarship_exempt"] = scholarship if b["amount"] is None else min(scholarship, b["amount"])
        arts.append(b["article"])
        out["form_8833_required"] |= bool(b.get("form_8833_required"))
        out["notes"].append(b["note"])
    out["articles"] = ", ".join(f"Art. {a}" for a in arts)
    return out
