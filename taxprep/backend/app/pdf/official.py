"""Builders that map calculation results onto the official 2025 forms.

Field names were taken from the agencies' own fill-in PDFs (see BUILD_LOG.txt, "official form
field maps") and every mapping is covered by tests/test_pdf.py, which reads the values back.
"""
from __future__ import annotations
from datetime import date
from .fill import fill_pdf, template_path, has_template, money, digits, ssn_dashed, mmddyyyy, stamp

FS_1040 = {"single": "1", "mfj": "2", "mfs": "3", "hoh": "4", "qss": "5"}
FS_1040NR = {"single": "1", "mfs": "2", "qss": "3"}


def _name(tp):
    first = " ".join(filter(None, [tp.get("first_name", ""), tp.get("middle_initial", "")]))
    return first, tp.get("last_name", "")


def schedule_2(year, tp, fed):
    """2025 Schedule 2 for the additional taxes currently computed by the engine."""
    L = fed["lines"]
    first, last = _name(tp)
    return fill_pdf(template_path(year, "f1040s2.pdf"), {
        "f1_01[0]": " ".join(filter(None, [first, last])),
        "f1_02[0]": ssn_dashed(tp.get("ssn", "")),
        "f1_15[0]": money(L.get("se_tax", 0)),  # line 4
        "f1_22[0]": money(L.get("addl_medicare", 0)),  # line 11
        "f1_23[0]": money(L.get("niit", 0)),  # line 12
        "f2_24[0]": money(L["other_taxes"], blank_zero=False),  # line 21
    })


def _city(tp):
    if tp.get("city") or tp.get("state") or tp.get("zip"):
        return tp.get("city", ""), tp.get("state", ""), tp.get("zip", "")
    return tp.get("city_state_zip", ""), "", ""


def _yes_no(prefix: str, yes: bool) -> dict:
    """IRS yes/no checkbox pairs: [0] = Yes, [1] = No."""
    return {f"{prefix}[0]": "1" if yes else "Off", f"{prefix}[1]": "Off" if yes else "2"}


# ======================================================================= Form 1040 / 1040-NR
def form_1040(year, tp, fed, dual=False):
    L = fed["lines"]
    first, last = _name(tp)
    city, st, zp = _city(tp)
    v = {
        "f1_14[0]": first, "f1_15[0]": last, "f1_16[0]": digits(tp.get("ssn", "")),
        "f1_20[0]": tp.get("address", ""), "f1_21[0]": tp.get("apt", ""),
        "f1_22[0]": city, "f1_23[0]": st, "f1_24[0]": zp,
        "f1_25[0]": tp.get("foreign_country", ""), "f1_26[0]": tp.get("foreign_province", ""),
        "f1_27[0]": tp.get("foreign_postal", ""),
        "f1_47[0]": money(L["wages"]), "f1_57[0]": money(L["wages"]),
        "f1_59[0]": money(L["taxable_interest"]), "f1_60[0]": money(L["qualified_dividends"]),
        "f1_61[0]": money(L["ordinary_dividends"]), "f1_70[0]": money(L["capital_gain"]),
        "f1_72[0]": money(L["other_income"]), "f1_73[0]": money(L["total_income"], blank_zero=False),
        "f1_74[0]": money(L["adjustments"]), "f1_75[0]": money(L["agi"], blank_zero=False),
        # page 2
        "f2_01[0]": money(L["agi"], blank_zero=False), "f2_02[0]": money(L["deduction"], blank_zero=False),
        "f2_04[0]": money(L["sched1a_total"]), "f2_05[0]": money(L["total_deductions"], blank_zero=False),
        "f2_06[0]": money(L["taxable_income"], blank_zero=False),
        "f2_08[0]": money(L["tax"], blank_zero=False), "f2_10[0]": money(L["tax"], blank_zero=False),
        "f2_11[0]": money(L["ctc_odc"]), "f2_12[0]": money(L["education_credit"]),
        "f2_13[0]": money(L["total_credits"]), "f2_14[0]": money(L["tax_after_credits"], blank_zero=False),
        "f2_15[0]": money(L["other_taxes"]), "f2_16[0]": money(L["total_tax"], blank_zero=False),
        "f2_17[0]": money(L["withholding_w2"]), "f2_18[0]": money(L.get("withholding_1099", 0)),
        "f2_19[0]": money(L.get("withholding_other", L["withholding_1042s"])),
        "f2_20[0]": money(L["withholding_total"]), "f2_21[0]": money(L["estimated_payments"]),
        "f2_23[0]": money(L["eitc"]), "f2_24[0]": money(L["actc"]), "f2_25[0]": money(L["aotc_refundable"]),
        "f2_27[0]": money(L.get("sch3_refundable", 0)),
        "f2_28[0]": money(L["eitc"] + L["actc"] + L["aotc_refundable"] + L.get("sch3_refundable", 0)),
        "f2_29[0]": money(L["total_payments"], blank_zero=False),
        "f2_30[0]": money(L["overpaid"]), "f2_31[0]": money(L["overpaid"]), "f2_35[0]": money(L["owed"]),
        "f2_40[0]": tp.get("occupation", ""), "f2_44[0]": tp.get("phone", ""), "f2_45[0]": tp.get("email", ""),
    }
    deps = fed.get("_dependents_list") or []
    for i, d in enumerate(deps[:4]):
        v[f"f1_{31 + i}[0]"] = d.get("first_name", "")
        v[f"f1_{35 + i}[0]"] = d.get("last_name", "")
        v[f"f1_{39 + i}[0]"] = digits(d.get("ssn", ""))       # 9-box comb field
        v[f"f1_{43 + i}[0]"] = d.get("relationship", "")
        v[f"c1_{12 + 2 * i}[0]"] = bool(d.get("lived_with_you"))
        v[f"c1_{13 + 2 * i}[0]"] = bool(d.get("lived_with_you") and d.get("lived_in_us"))
        v[f"c1_{20 + 2 * i}[0]"] = bool(d.get("full_time_student"))
        v[f"c1_{21 + 2 * i}[0]"] = bool(d.get("disabled"))
    if len(deps) > 4:
        v["c1_11[0]"] = True
    dep_radios = {f"c1_{28 + i}[{0 if d.get('credit') == 'ctc' else 1}]": ("1" if d.get("credit") == "ctc" else "2")
                  for i, d in enumerate(deps[:4]) if d.get("credit") in ("ctc", "odc")}
    radios = {**dep_radios, "c1_8[0]": FS_1040[fed["filing_status"]], "c1_8[1]": FS_1040[fed["filing_status"]],
              "c1_8[2]": FS_1040[fed["filing_status"]],
              **_yes_no("c1_10", False), "c2_17[0]": "Off", "c2_17[1]": "2"}
    doc = fill_pdf(template_path(year, "f1040.pdf"), v, radios=radios)
    if dual:
        stamp(doc, 0, "DUAL-STATUS RETURN", 36, 22, 12)
        stamp(doc, 0, f"Resident alien from {mmddyyyy(fed.get('_residency_start', ''))} - dual-status statement attached",
              200, 21, 7.5)
    return doc


def form_1040nr(year, tp, fed):
    L = fed["lines"]
    first, last = _name(tp)
    city, st, zp = _city(tp)
    v = {
        "f1_14[0]": first, "f1_15[0]": last, "f1_16[0]": digits(tp.get("ssn", "")),
        "f1_17[0]": tp.get("address", ""), "f1_18[0]": tp.get("apt", ""),
        "f1_19[0]": city, "f1_20[0]": st, "f1_21[0]": zp,
        "f1_22[0]": tp.get("foreign_country", ""), "f1_23[0]": tp.get("foreign_province", ""),
        "f1_24[0]": tp.get("foreign_postal", ""),
        "f1_42[0]": money(L["wages"]), "f1_53[0]": money(L["treaty_exempt_income"]),
        "f1_54[0]": money(L["wages"]),
        "f1_56[0]": money(L["taxable_interest"]), "f1_57[0]": money(L["qualified_dividends"]),
        "f1_58[0]": money(L["ordinary_dividends"]), "f1_66[0]": money(L["capital_gain"]),
        "f1_68[0]": money(L["other_income"]), "f1_69[0]": money(L["total_income"], blank_zero=False),
        "f1_70[0]": money(L["adjustments"]), "f1_71[0]": money(L["agi"], blank_zero=False),
        # page 2
        "f2_01[0]": money(L["agi"], blank_zero=False), "f2_02[0]": money(L["deduction"], blank_zero=False),
        "f2_05[0]": money(L["sched1a_total"]), "f2_06[0]": money(L["total_deductions"], blank_zero=False),
        "f2_07[0]": money(L["taxable_income"], blank_zero=False),
        "f2_09[0]": money(L["tax"], blank_zero=False), "f2_11[0]": money(L["tax"], blank_zero=False),
        "f2_12[0]": money(L["ctc_odc"]), "f2_14[0]": money(L["total_credits"]),
        "f2_15[0]": money(L["tax_after_credits"], blank_zero=False),
        "f2_16[0]": money(L["nec_tax"]), "f2_17[0]": money(L["other_taxes"]),
        "f2_19[0]": money(L["nec_tax"] + L["other_taxes"]),
        "f2_20[0]": money(L["total_tax"], blank_zero=False),
        "f2_21[0]": money(L["withholding_w2"]), "f2_22[0]": money(L.get("withholding_1099", 0)),
        "f2_23[0]": money(L.get("addl_medicare_withheld", 0)),
        "f2_24[0]": money(L["withholding_w2"] + L.get("withholding_1099", 0) + L.get("addl_medicare_withheld", 0)),
        "f2_27[0]": money(L["withholding_1042s"]), "f2_28[0]": money(L["estimated_payments"]),
        "f2_33[0]": money(L.get("sch3_refundable", 0)), "f2_34[0]": money(L.get("sch3_refundable", 0)),
        "f2_35[0]": money(L["total_payments"], blank_zero=False),
        "f2_36[0]": money(L["overpaid"]), "f2_37[0]": money(L["overpaid"]), "f2_42[0]": money(L["owed"]),
        "f2_47[0]": tp.get("occupation", ""), "f2_49[0]": tp.get("phone", ""), "f2_50[0]": tp.get("email", ""),
    }
    fs = FS_1040NR.get(fed["filing_status"], "1")
    radios = {"c1_5[0]": fs, "c1_5[1]": fs, "c1_5[2]": fs, **_yes_no("c1_6", False),
              "c2_7[0]": "Off", "c2_7[1]": "2"}
    return fill_pdf(template_path(year, "f1040nr.pdf"), v, radios=radios)


# ======================================================================= Schedule 1
def schedule_1(year, tp, fed):
    L = fed["lines"]
    first, last = _name(tp)
    v = {"f1_01[0]": f"{first} {last}".strip(), "f1_02[0]": digits(tp.get("ssn", "")),
         "f1_07[0]": money(L["sched1_business"]), "f1_30[0]": money(L["sched1_scholarship"]),
         "f1_37[0]": money(L["sched1_scholarship"]), "f1_38[0]": money(L["other_income"]),
         "f2_05[0]": money(L["adj_half_se"]), "f2_13[0]": money(L["adj_student_loan"]),
         "f2_30[0]": money(L["adjustments"])}
    return fill_pdf(template_path(year, "f1040s1.pdf"), v)


# ======================================================================= Schedule OI
def schedule_oi(year, tp, profile, fed, residency):
    first, last = _name(tp)
    t = fed.get("treaty") or {}
    L = fed["lines"]
    country = profile.get("country", "")
    changed = bool(profile.get("first_nonexempt_day")) or (
        profile.get("visa") not in ("F-1", "J-1 Student", "M-1", "OPT", "STEM OPT", "CPT") and
        (profile.get("exempt_days_current") or 0) > 0)
    v = {"f1_1[0]": f"{first} {last}".strip(), "f1_2[0]": digits(tp.get("ssn", "")),
         "f1_3[0]": country, "f1_4[0]": profile.get("tax_residence_country") or country,
         "f1_5[0]": profile.get("visa", ""),
         "f1_6[0]": (f"{mmddyyyy(profile.get('first_nonexempt_day', ''))} changed to {profile.get('visa', '')}"
                     if changed else ""),
         "f1_23[0]": str(profile.get("days_prior2", "")), "f1_24[0]": str(profile.get("days_prior1", "")),
         "f1_25[0]": str(profile.get("days_current", "")),
         "f1_26[0]": profile.get("prior_return_info", "") if profile.get("filed_prior_return") else ""}
    # Item G: entry/exit dates (up to 8 trips: 4 rows in each of two tables)
    cells = ["f1_7[0]", "f1_8[0]", "f1_9[0]", "f1_10[0]", "f1_11[0]", "f1_12[0]", "f1_13[0]", "f1_14[0]",
             "f1_15[0]", "f1_16[0]", "f1_17[0]", "f1_18[0]", "f1_19[0]", "f1_20[0]", "f1_21[0]", "f1_22[0]"]
    for i, trip in enumerate((profile.get("trips") or [])[:8]):
        v[cells[2 * i]] = mmddyyyy(trip.get("entered", ""))[:6] + mmddyyyy(trip.get("entered", ""))[-2:] \
            if trip.get("entered") else ""
        v[cells[2 * i + 1]] = mmddyyyy(trip.get("departed", ""))[:6] + mmddyyyy(trip.get("departed", ""))[-2:] \
            if trip.get("departed") else ""
    exempt = L.get("treaty_exempt_income", 0)
    if t.get("articles") and exempt:
        v.update({"f1_27[0]": t.get("country", country), "f1_28[0]": t["articles"].replace("Art. ", ""),
                  "f1_29[0]": str(profile.get("treaty_prior_months", 0) or 0), "f1_30[0]": money(exempt),
                  "f1_39[0]": money(exempt)})
    radios = {**_yes_no("c1_1", bool(profile.get("applied_green_card"))),
              **_yes_no("c1_2", False), **_yes_no("c1_3", False), **_yes_no("c1_4", changed),
              **_yes_no("c1_6", bool(profile.get("filed_prior_return"))), **_yes_no("c1_7", False),
              **_yes_no("c1_9", L.get("wages", 0) >= 250000)}
    if t.get("articles") and exempt:
        radios.update({**_yes_no("c1_11", False), **_yes_no("c1_12", False)})
    return fill_pdf(template_path(year, "f1040nro.pdf"), v, radios=radios)


# ======================================================================= Schedule NEC
def schedule_nec(year, tp, fed):
    L = fed["lines"]
    first, last = _name(tp)
    v = {"f1_1[0]": f"{first} {last}".strip(), "f1_2[0]": digits(tp.get("ssn", ""))}
    cols = {0.10: 0, 0.15: 1, 0.30: 2}
    line1a = ["f1_5[0]", "f1_6[0]", "f1_7[0]", "f1_8[0]", "f1_9[0]"]
    line13 = ["f1_89[0]", "f1_90[0]", "f1_91[0]", "f1_92[0]", "f1_93[0]"]
    line14 = ["f1_94[0]", "f1_95[0]", "f1_96[0]", "f1_97[0]", "f1_98[0]"]
    tot = [0.0] * 5
    rates = [0.10, 0.15, 0.30, None, None]
    div, rate = L.get("nec_dividends", 0), float(L.get("nec_dividend_rate") or 0.30)
    if div:
        c = cols.get(round(rate, 2), 3)
        if c == 3:
            v["f1_3[0]"] = f"{rate * 100:g}"
            rates[3] = rate
        v[line1a[c]] = money(div)
        tot[c] += div
    cg = L.get("nec_capital_gains", 0)
    if cg:
        v["f1_67[0]"] = money(cg)
        tot[2] += cg
        v.update({"f1_100[0]": "Various securities (see broker statements)", "f1_101[0]": "Various",
                  "f1_102[0]": "Various", "f1_106[0]": money(cg), "f1_136[0]": money(cg), "f1_137[0]": money(cg)})
    total_tax = 0.0
    for i, amt in enumerate(tot):
        if amt:
            v[line13[i]] = money(amt)
            tax = round(amt * rates[i])
            v[line14[i]] = money(tax)
            total_tax += tax
    v["f1_99[0]"] = money(total_tax)
    return fill_pdf(template_path(year, "f1040nrn.pdf"), v)


# ======================================================================= Form 8843
def form_8843(year, tp, profile, residency):
    first, last = _name(tp)
    vb = profile.get("visa_by_year") or {}
    student = profile.get("visa") not in ("J-1 Non-student", "J-1 Researcher", "J-1 Scholar", "J-1 Teacher", "Q-1")
    v = {"f1_04[0]": first, "f1_05[0]": last, "f1_06[0]": ssn_dashed(tp.get("ssn", "")),
         "f1_09[0]": " ".join(filter(None, [profile.get("visa", ""), mmddyyyy(profile.get("visa_entry_date", ""))])),
         "f1_10[0]": profile.get("visa", "") + (
             f" (changed {mmddyyyy(profile.get('first_nonexempt_day', ''))}; previously {profile.get('previous_visa') or 'F-1'})"
             if profile.get("first_nonexempt_day") else ""),
         "f1_11[0]": profile.get("country", ""),
         "f1_12[0]": profile.get("passport_country") or profile.get("country", ""),
         "f1_13[0]": profile.get("passport_number", ""),
         "f1_14[0]": str(profile.get("days_current", "")), "f1_15[0]": str(profile.get("days_prior1", "")),
         "f1_16[0]": str(profile.get("days_prior2", "")),
         "f1_17[0]": str(residency.get("exempt_days_current", 0))}
    years = [str(y) for y in range(year - 6, year)]          # 2019 .. 2024
    if student:
        v["f1_26[0]"] = ", ".join(filter(None, [tp.get("school", ""), tp.get("school_address", ""),
                                                 profile.get("school_phone", "")]))
        v["f1_27[0]"] = profile.get("program_director", "")
        for fld, y in zip(["f1_28[0]", "f1_29[0]", "f1_30[0]", "f1_31[0]", "f1_32[0]", "f1_33[0]"], years):
            v[fld] = vb.get(y, "")
        radios = {**_yes_no("c1_2", bool(residency.get("student_exempt_more_than_5_years"))),
                  **_yes_no("c1_3", bool(profile.get("applied_green_card")))}
    else:
        v["f1_18[0]"] = ", ".join(filter(None, [tp.get("school", ""), tp.get("school_address", "")]))
        v["f1_19[0]"] = profile.get("program_director", "")
        for fld, y in zip(["f1_20[0]", "f1_21[0]", "f1_22[0]", "f1_23[0]", "f1_24[0]", "f1_25[0]"], years):
            v[fld] = vb.get(y, "")
        radios = _yes_no("c1_1", (residency.get("exempt_years_used") or 0) >= 2)
    doc = fill_pdf(template_path(year, "f8843.pdf"), v, radios=radios)
    if doc.page_count > 2:
        doc.delete_pages(2, doc.page_count - 1)      # pages 3-4 are instructions, not part of the form
    return doc


# ======================================================================= California
CA_FS = {"single": "1#20.#20Single.", "mfj": "2#20.#20Married", "mfs": "3#20.#20Married",
         "hoh": "4#20.#20Head", "qss": "5#20.#20Qualifying"}


def _ca_header(prefix, tp):
    first, last = tp.get("first_name", ""), tp.get("last_name", "")
    city, st, zp = _city(tp)
    return {f"{prefix}_form_1003": first, f"{prefix}_form_1004": tp.get("middle_initial", ""),
            f"{prefix}_form_1005": last, f"{prefix}_form_1007": ssn_dashed(tp.get("ssn", "")),
            f"{prefix}_form_1015": tp.get("address", ""), f"{prefix}_form_1016": tp.get("apt", ""),
            f"{prefix}_form_1018": city, f"{prefix}_form_1019": st, f"{prefix}_form_1020": zp,
            f"{prefix}_form_1021": tp.get("foreign_country", ""), f"{prefix}_form_1024": mmddyyyy(tp.get("date_of_birth", "")),
            f"{prefix}_form_2001": f"{first} {last}".strip(), f"{prefix}_form_2002": ssn_dashed(tp.get("ssn", ""))}


def _radio_value(path, field, prefix_value):
    """Find the full on-state of a radio group whose on-state starts with prefix_value."""
    import pymupdf
    with pymupdf.open(path) as d:
        for p in d:
            for w in p.widgets():
                if w.field_name == field and str(w.on_state()).startswith(prefix_value):
                    return w.on_state()
    raise KeyError(f"{field}: no option starting {prefix_value}")


def ca_540(year, tp, fed, st, ca_inputs):
    L = st["lines"]
    path = template_path(year, "2025-540.pdf" if year == 2025 else f"{year}-540.pdf")
    m = lambda x, bz=True: money(x, commas=False, blank_zero=bz)
    fs = fed["filing_status"]
    personal = 2 if fs == "mfj" else 1
    deps = ca_inputs.get("dependents", 0)
    fed_agi = fed["lines"]["agi"]
    diff = L["ca_agi"] - fed_agi
    pers_amt = 153 * personal
    v = {**_ca_header("540", tp),
         "540_form_1029 CB": True,
         "540_form_1041": str(personal), "540_form_1042": m(pers_amt),
         "540_form_2015": str(deps) if deps else "", "540_form_2016": m(475 * deps),
         "540_form_2017": m(pers_amt + 475 * deps),
         "540_form_2018": m(ca_inputs.get("state_wages", 0)),
         "540_form_2019": m(fed_agi, False), "540_form_2020": m(-diff if diff < 0 else 0),
         "540_form_2021": m(fed_agi - (-diff if diff < 0 else 0), False), "540_form_2022": m(diff if diff > 0 else 0),
         "540_form_2023": m(L["ca_agi"], False), "540_form_2024": m(L["deduction"], False),
         "540_form_2025": m(L["taxable_income"], False),
         "540_form_2026 CB" if L["taxable_income"] <= 100000 else "540_form_2027 CB": True,
         "540_form_2030": m(L["tax"], False), "540_form_2031": m(L["exemption_credits"]),
         "540_form_2032": m(L["tax"] - L["exemption_credits"], False),
         "540_form_2036": m(L["tax"] - L["exemption_credits"], False),
         "540_form_3004": m(L["renters_credit"]), "540_form_3005": m(L["renters_credit"]),
         "540_form_3006": m(L["total_tax"], False), "540_form_3010": m(L["total_tax"], False),
         "540_form_3011": m(L["withholding"]), "540_form_3018": m(L["withholding"], False),
         "540_form_3019": "0", "540_form_3021 CB": bool(ca_inputs.get("health_coverage", True)),
         "540_form_3023": m(L["withholding"], False), "540_form_3025": m(L["withholding"], False),
         "540_form_3027": m(L["overpaid"]), "540_form_4004": m(L["overpaid"]),
         "540_form_4005": m(L["owed"]), "540_form_5002": m(L["owed"]), "540_form_5007": m(L["overpaid"])}
    radios = {"540_form_1036 RB": _radio_value(path, "540_form_1036 RB", CA_FS[fs]),
              "540_form_3020 RB": "0"}
    return fill_pdf(path, v, radios=radios)


def ca_540nr(year, tp, fed, st, ca_inputs):
    L = st["lines"]
    path = template_path(year, "2025-540nr.pdf")
    m = lambda x, bz=True: money(x, commas=False, blank_zero=bz)
    fs = fed["filing_status"]
    personal = 2 if fs == "mfj" else 1
    deps = ca_inputs.get("dependents", 0)
    fed_agi = fed["lines"]["agi"]
    diff = L["total_agi"] - fed_agi
    total_ex = 153 * personal + 475 * deps
    rate = f"{L['ca_tax_rate']:.4f}"
    pct = f"{L['exemption_credit_pct']:.4f}"
    v = {**_ca_header("540NR", tp),
         "540NR_form_1034": str(personal), "540NR_form_1035": m(153 * personal),
         "540NR_form_1052": str(deps) if deps else "", "540NR_form_1053": m(475 * deps),
         "540NR_form_2003": m(total_ex), "540NR_form_2004": m(ca_inputs.get("state_wages", 0)),
         "540NR_form_2005": m(fed_agi, False), "540NR_form_2006": m(-diff if diff < 0 else 0),
         "540NR_form_2007": m(fed_agi - (-diff if diff < 0 else 0), False),
         "540NR_form_2008": m(diff if diff > 0 else 0), "540NR_form_2009": m(L["total_agi"], False),
         "540NR_form_2010": m(L["deduction"], False), "540NR_form_2011": m(L["total_taxable_income"], False),
         "540NR_form_2012 CB" if L["total_taxable_income"] <= 100000 else "540NR_form_2013 CB": True,
         "540NR_form_2016": m(L["total_tax_all_income"], False), "540NR_form_2017": m(L["ca_agi"], False),
         "540NR_form_2018": m(L["ca_taxable_income"], False),
         "540NR_form_2019": rate.split(".")[0], "540NR_form_2020": rate.split(".")[1],
         "540NR_form_2021": m(L["tax"], False),
         "540NR_form_2022": pct.split(".")[0], "540NR_form_2023": pct.split(".")[1],
         "540NR_form_2024": m(L["exemption_credits"]), "540NR_form_2025": m(L["tax"] - L["exemption_credits"], False),
         "540NR_form_2029": m(L["tax"] - L["exemption_credits"], False),
         "540NR_form_3008": m(L["renters_credit"]), "540NR_form_3009": m(L["renters_credit"]),
         "540NR_form_3010": m(L["total_tax"], False), "540NR_form_3014": m(L["total_tax"], False),
         "540NR_form_3015": m(L["withholding"]), "540NR_form_3022": m(L["withholding"], False),
         "540NR_form_3023 CB": bool(ca_inputs.get("health_coverage", True)),
         "540NR_form_3025": m(L["withholding"], False), "540NR_form_3027": m(L["overpaid"]),
         "540NR_form_3029": m(L["overpaid"]), "540NR_form_4003": m(L["owed"]),
         "540NR_form_5001": m(L["owed"]), "540NR_form_5007": m(L["overpaid"])}
    radios = {"540NR_form_1029 RB": _radio_value(path, "540NR_form_1029 RB", "Line#20" + CA_FS[fs][0])}
    return fill_pdf(path, v, radios=radios)


# ======================================================================= New York
NY_FS = {"single": "1#20Single", "mfj": "2#20Married", "mfs": "3#20Married", "hoh": "Head", "qss": "Qualifying"}


def _ny_radio(path, field, prefix):
    import pymupdf
    with pymupdf.open(path) as d:
        for p in d:
            for w in p.widgets():
                if w.field_name == field and str(w.on_state()).startswith(prefix):
                    return w.on_state()
    raise KeyError(f"{field}: no option starting {prefix}")


def ny_it201(year, tp, fed, st, ny_inputs):
    L, F = st["lines"], fed["lines"]
    path = template_path(year, "it201_fill_in.pdf")
    m = lambda x, bz=True: money(x, commas=False, blank_zero=bz)
    city, s, zp = _city(tp)
    first, last = tp.get("first_name", ""), tp.get("last_name", "")
    v = {"TP_first_name": first, "TP_MI": tp.get("middle_initial", ""), "TP_last_name": last,
         "TP_DOB": digits(mmddyyyy(tp.get("date_of_birth", ""))), "TP_SSN": digits(tp.get("ssn", "")),
         "TP_mail_address": tp.get("address", ""), "TP_mail_apt": tp.get("apt", ""), "TP_mail_city": city,
         "TP_mail_state": s, "TP_mail_zip": zp, "TP_home_address": tp.get("address", ""),
         "TP_home_apt": tp.get("apt", ""), "TP_home_city": city, "TP_home_zip": zp,
         "Line1": m(F["wages"]), "Line2": m(F["taxable_interest"]), "Line3": m(F["ordinary_dividends"]),
         "Line6": m(F["sched1_business"]), "Line7": m(F["capital_gain"]),
         "Line16": m(F["sched1_scholarship"]), "15_identify": "",
         "Line17": m(F["total_income"], False), "Line18": m(F["adjustments"]), "Line19": m(F["agi"], False),
         "Line24": m(F["agi"], False), "Line33": m(L["ny_agi"], False), "Line34": m(L["deduction"], False),
         "Line35": m(max(0, L["ny_agi"] - L["deduction"]), False), "Line36": m(L["dependent_exemptions"]),
         "Line37": m(L["taxable_income"], False), "Line38": m(L["taxable_income"], False),
         "Line39": m(L["tax"], False), "Line44": m(L["tax"], False), "Line46": m(L["tax"], False),
         "Line59": "0", "Line61": m(L["tax"], False), "Line62": m(L["tax"], False),
         "Line72": m(L["withholding"]), "Line76": m(L["withholding"], False),
         "Line77": m(L["overpaid"]), "Line78": m(L["overpaid"]), "Line78b": m(L["overpaid"]),
         "Line80": m(L["owed"]), "TP_occupation": tp.get("occupation", "")}
    if F["sched1_scholarship"]:
        v["18_identify"] = ""
    radios = {"Filing_status": _ny_radio(path, "Filing_status", NY_FS[fed["filing_status"]]),
              "34Deduction": "Standard" if L["deduction"] <= ny_inputs.get("std", 0) else "Itemized",
              "Itemized": "yes" if F.get("deduction_type") == "itemized" else "no",
              "3rd_party_box": "no"}
    if L["overpaid"]:
        radios["Line78_refund"] = "check"
    return fill_pdf(path, v, radios=radios)


def ny_it203(year, tp, fed, st, ny_inputs):
    L, F = st["lines"], fed["lines"]
    path = template_path(year, "it203_fill_in.pdf")
    m = lambda x, bz=True: money(x, commas=False, blank_zero=bz)
    city, s, zp = _city(tp)
    pct = L.get("income_percentage", 1.0)
    ny_src = L.get("ny_source_income", L["ny_agi"])
    v = {"Your first name": " ".join(filter(None, [tp.get("first_name", ""), tp.get("middle_initial", "")])),
         "Your last name": tp.get("last_name", ""), "Your DOB": digits(mmddyyyy(tp.get("date_of_birth", ""))),
         "Your SSN": digits(tp.get("ssn", "")), "Mailing address": tp.get("address", ""),
         "Apartment number 1": tp.get("apt", ""), "City, village or post office 1": city,
         "State 1": s, "ZIP code 1": zp,
         "federal 1 dollars": m(F["wages"]), "nys 1 dollars": m(min(F["wages"], ny_src)),
         "federal 2 dollars": m(F["taxable_interest"]), "federal 3 dollars": m(F["ordinary_dividends"]),
         "federal 6 dollars": m(F["sched1_business"]), "federal 7 dollars": m(F["capital_gain"]),
         "federal 16 dollars": m(F["sched1_scholarship"]),
         "federal 17 dollars": m(F["total_income"], False), "nys 17 dollars": m(ny_src, False),
         "federal 18 dollars": m(F["adjustments"]),
         "federal 19 dollars": m(F["agi"], False), "nys 19 dollars": m(ny_src, False),
         "federal 24 dollars": "", "federal 31 dollars": m(F["agi"], False), "nys 31 dollars": m(ny_src, False),
         "32 dollars": m(F["agi"], False), "33 dollars": m(L["deduction"], False),
         "34 dollars": m(max(0, F["agi"] - L["deduction"]), False), "35 dollars": m(L["dependent_exemptions"]),
         "36 dollars": m(L["taxable_income"], False), "37 dollars": m(L["taxable_income"], False),
         "38 dollars": m(L["base_tax"], False), "40 dollars": m(L["base_tax"], False),
         "42 dollars": m(L["base_tax"], False), "44 dollars": m(L["base_tax"], False),
         "45nys dollars": m(ny_src, False), "45 federal dollars": m(F["agi"], False),
         "45 dollars": f"{pct:.4f}".lstrip("0") if pct < 1 else "1.0000",
         "46 dollars": m(L["tax"], False), "48 dollars": m(L["tax"], False), "50 dollars": m(L["tax"], False),
         "56 dollars": "0", "58 dollars": m(L["tax"], False), "59 dollars": m(L["tax"], False),
         "62 dollars": m(L["withholding"]), "66 dollars": m(L["withholding"], False),
         "67 dollars": m(L["overpaid"]), "68 dollars": m(L["overpaid"]), "68b dollars": m(L["overpaid"]),
         "70 dollars": m(L["owed"]), "Occupation": tp.get("occupation", "")}
    radios = {"Filing Status": _ny_radio(path, "Filing Status", NY_FS[fed["filing_status"]]),
              "deduction": "Standard" if L["deduction"] <= ny_inputs.get("std", 0) else "Itemized",
              "BoxB": "yes" if F.get("deduction_type") == "itemized" else "no",
              "3rd Party Discuss": "no"}
    if L["overpaid"]:
        radios["line 68"] = "debit#20card"
    return fill_pdf(path, v, radios=radios)


# ======================================================================= supplemental federal forms
def _head(tp, ssn_fmt=digits):
    first, last = _name(tp)
    return " ".join(filter(None, [first, last])), ssn_fmt(tp.get("ssn", ""))


def schedule_a(year, tp, fed):
    """Schedule A (Form 1040), itemized deductions."""
    L = fed["lines"]
    name, ssn = _head(tp)
    taxes = L["salt_deduction"]
    gifts = L["sa_gifts"]
    return fill_pdf(template_path(year, "f1040sa.pdf"), {
        "f1_1[0]": name, "f1_2[0]": ssn,
        "f1_3[0]": money(L["sa_medical_paid"]), "f1_4[0]": money(L["agi"], blank_zero=False) if L["sa_medical_paid"] else "",
        "f1_5[0]": money(round(L["agi"] * 0.075)) if L["sa_medical_paid"] else "", "f1_6[0]": money(L["sa_medical"]),
        "f1_7[0]": money(L["sa_state_income_tax"]), "f1_8[0]": money(L["sa_real_estate_tax"]),
        "f1_10[0]": money(L["sa_salt_paid"]), "f1_11[0]": money(taxes), "f1_14[0]": money(taxes),
        "f1_15[0]": money(L["sa_mortgage"]), "f1_20[0]": money(L["sa_mortgage"]), "f1_22[0]": money(L["sa_mortgage"]),
        "f1_23[0]": money(L["sa_gifts_cash"]), "f1_24[0]": money(L["sa_gifts_noncash"]), "f1_26[0]": money(gifts),
        "f1_28[0]": "See statement" if L["sa_other"] else "", "f1_29[0]": money(L["sa_other"]),
        "f1_30[0]": money(L["sa_total"], blank_zero=False),
    })


def schedule_a_nr(year, tp, fed):
    """Schedule A (Form 1040-NR), itemized deductions for nonresident aliens."""
    L = fed["lines"]
    name, ssn = _head(tp)
    return fill_pdf(template_path(year, "f1040nra.pdf"), {
        "f1_1[0]": name, "f1_2[0]": ssn,
        "f1_3[0]": money(L["sa_state_income_tax"]), "f1_4[0]": money(L["salt_deduction"]),
        "f1_5[0]": money(L["sa_gifts_cash"]), "f1_6[0]": money(L["sa_gifts_noncash"]),
        "f1_8[0]": money(L["sa_gifts"]), "f1_12[0]": money(L["sa_total"], blank_zero=False),
    })


def schedule_3(year, tp, fed):
    L = fed["lines"]
    name, ssn = _head(tp)
    return fill_pdf(template_path(year, "f1040s3.pdf"), {
        "f1_01[0]": name, "f1_02[0]": ssn,
        "f1_05[0]": money(L["education_credit"]), "f1_25[0]": money(L["education_credit"]),
        "f1_28[0]": money(L.get("excess_ss_credit", 0)), "f1_37[0]": money(L.get("sch3_refundable", 0)),
    })


def form_8959(year, tp, fed, fs_threshold):
    L = fed["lines"]
    name, ssn = _head(tp)
    mw, se = L.get("medicare_wages", 0), L.get("medicare_se_wages", 0)
    p1 = max(0, mw - fs_threshold)
    rem = max(0, fs_threshold - mw)
    p2 = max(0, se - rem)
    box6 = L.get("medicare_tax_withheld", 0)
    reg = round(mw * 0.0145)
    return fill_pdf(template_path(year, "f8959.pdf"), {
        "f1_1[0]": name, "f1_2[0]": ssn,
        "f1_3[0]": money(mw), "f1_6[0]": money(mw), "f1_7[0]": money(fs_threshold, blank_zero=False),
        "f1_8[0]": money(p1), "f1_9[0]": money(round(p1 * 0.009)),
        "f1_10[0]": money(se), "f1_11[0]": money(fs_threshold, blank_zero=False) if se else "",
        "f1_12[0]": money(mw) if se else "", "f1_13[0]": money(rem) if se else "", "f1_14[0]": money(p2),
        "f1_15[0]": money(round(p2 * 0.009)),
        "f1_20[0]": money(L.get("addl_medicare", 0)),
        "f1_21[0]": money(box6), "f1_22[0]": money(mw) if box6 else "", "f1_23[0]": money(reg) if box6 else "",
        "f1_24[0]": money(L.get("addl_medicare_withheld", 0)), "f1_26[0]": money(L.get("addl_medicare_withheld", 0)),
    })


def form_8960(year, tp, fed, threshold):
    L = fed["lines"]
    name, ssn = _head(tp)
    nii = L.get("net_investment_income", 0)
    over = max(0, L["agi"] - threshold)
    return fill_pdf(template_path(year, "f8960.pdf"), {
        "f1_1[0]": name, "f1_2[0]": ssn,
        "f1_3[0]": money(L["taxable_interest"]), "f1_4[0]": money(L["ordinary_dividends"]),
        "f1_9[0]": money(max(0, L["capital_gain"])), "f1_12[0]": money(max(0, L["capital_gain"])),
        "f1_15[0]": money(nii), "f1_22[0]": money(nii),
        "f1_23[0]": money(L["agi"]), "f1_24[0]": money(threshold, blank_zero=False), "f1_25[0]": money(over),
        "f1_26[0]": money(min(nii, over)), "f1_27[0]": money(L.get("niit", 0)),
    })


def schedule_se(year, tp, fed, ss_wage_base):
    L = fed["lines"]
    name, ssn = _head(tp, ssn_dashed)
    profit = L["sched1_business"]
    ne = L.get("se_net_earnings", 0)
    wages = L["wages"]
    room = max(0, ss_wage_base - wages)
    ss_part = min(ne, room)
    return fill_pdf(template_path(year, "f1040sse.pdf"), {
        "f1_1[0]": name, "f1_2[0]": ssn,
        "f1_5[0]": money(profit), "f1_6[0]": money(profit), "f1_7[0]": money(ne), "f1_9[0]": money(ne),
        "f1_12[0]": money(ne), "f1_14[0]": money(wages), "f1_17[0]": money(wages),
        "f1_18[0]": money(room), "f1_19[0]": money(round(ss_part * 0.124)), "f1_20[0]": money(round(ne * 0.029)),
        "f1_21[0]": money(L["se_tax"]), "f1_22[0]": money(L["adj_half_se"]),
    })


def schedule_1a(year, tp, fed, fs):
    """Schedule 1-A: tips (Part II), overtime (Part III) and seniors (Part V)."""
    import math
    L = fed["lines"]
    name, ssn = _head(tp)
    magi = L["agi"]
    v = {"f1_01[0]": name, "f1_02[0]": ssn, "f1_03[0]": money(magi, blank_zero=False),
         "f1_09[0]": money(magi, blank_zero=False)}
    lim = 300000 if fs == "mfj" else 150000
    over = max(0, magi - lim)
    steps = math.floor(over / 1000)

    def part(raw, cap, ded, f):   # f = field numbers for: input, total, capped, magi, limit, excess, steps, x100, result
        capped = min(raw, cap)
        v.update({f[0]: money(raw), f[1]: money(raw), f[2]: money(capped), f[3]: money(magi, blank_zero=False),
                  f[4]: money(lim, blank_zero=False), f[5]: money(over), f[6]: str(steps) if over else "",
                  f[7]: money(steps * 100), f[8]: money(ded)})
    if L.get("sched1a_tips"):
        part(L["tips_raw"], 25000, L["sched1a_tips"],
             ["f1_12[0]", "f1_14[0]", "f1_15[0]", "f1_16[0]", "f1_17[0]", "f1_18[0]", "f1_19[0]", "f1_20[0]", "f1_21[0]"])
    if L.get("sched1a_overtime"):
        part(L["overtime_raw"], 25000 if fs == "mfj" else 12500, L["sched1a_overtime"],
             ["f1_22[0]", "f1_24[0]", "f1_25[0]", "f1_26[0]", "f1_27[0]", "f1_28[0]", "f1_29[0]", "f1_30[0]", "f1_31[0]"])
    if L.get("sched1a_senior"):
        base = 150000 if fs == "mfj" else 75000
        sover = max(0, magi - base)
        each = max(0, 6000 - round(sover * 0.06))
        v.update({"f2_15[0]": money(magi, blank_zero=False), "f2_16[0]": money(base, blank_zero=False),
                  "f2_17[0]": money(sover), "f2_18[0]": money(round(sover * 0.06)), "f2_19[0]": money(each),
                  "f2_20[0]": money(L["senior_self"]), "f2_21[0]": money(L["senior_spouse"]),
                  "f2_22[0]": money(L["sched1a_senior"])})
    v["f2_23[0]"] = money(L["sched1a_total"])
    return fill_pdf(template_path(year, "f1040s1a.pdf"), v)


def form_1040v(year, tp, amount):
    first, last = _name(tp)
    city, st, zp = _city(tp)
    return fill_pdf(template_path(year, "f1040v.pdf"), {
        "f1_1[0]": ssn_dashed(tp.get("ssn", "")), "f1_3[0]": money(amount, blank_zero=False),
        "f1_5[0]": first, "f1_6[0]": last, "f1_9[0]": tp.get("address", ""), "f1_10[0]": tp.get("apt", ""),
        "f1_11[0]": city, "f1_12[0]": st, "f1_13[0]": zp,
        "f1_14[0]": tp.get("foreign_country", ""), "f1_15[0]": tp.get("foreign_province", ""),
        "f1_16[0]": tp.get("foreign_postal", ""),
    })


def form_8833(year, tp, fed, payers: str = ""):
    """Treaty-based return position disclosure (resident aliens using a saving-clause exception)."""
    t = fed.get("treaty") or {}
    L = fed["lines"]
    first, last = _name(tp)
    city, st, zp = _city(tp)
    us_addr = ", ".join(filter(None, [tp.get("address", ""), tp.get("apt", ""), city, st, zp]))
    amounts = []
    if t.get("wage_exempt"):
        amounts.append(f"wages ${t['wage_exempt']:,.0f}")
    if t.get("scholarship_exempt"):
        amounts.append(f"scholarship/fellowship ${t['scholarship_exempt']:,.0f}")
    expl = (f"The taxpayer is a resident of {t.get('country', '')} who came to the United States as a student "
            f"and became a U.S. resident alien under the substantial presence test. Under {t.get('articles', '')} of the "
            f"U.S.-{t.get('country', '')} income tax treaty, which is an exception to the saving clause, the following "
            f"income is exempt from U.S. tax: {', '.join(amounts) or 'see return'}. Total exempt amount "
            f"${L.get('treaty_exempt_income', 0):,.0f}.")
    v = {"f1_1[0]": " ".join(filter(None, [first, last])), "f1_2[0]": ssn_dashed(tp.get("ssn", "")),
         "f1_4[0]": tp.get("foreign_country", ""), "f1_5[0]": us_addr,
         "f1_6[0]": t.get("country", ""), "f1_7[0]": t.get("articles", ""),
         "f1_8[0]": "IRC sections 61 and 871 (inclusion of the income in gross income)",
         "f1_9[0]": payers[:120], "f1_10[0]": "Not applicable"}
    for i, line in enumerate(_chunks(expl, 105)[:24]):
        v[f"f1_{13 + i}[0]"] = line
    return fill_pdf(template_path(year, "f8833.pdf"), v,
                    radios={"c1_1[0]": "1", "c1_3[0]": "1", "c1_4[0]": "Off", "c1_4[1]": "2"})


def _chunks(text, n):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    return out + ([line] if line else [])


def schedule_b(year, tp, inc, fed):
    L = fed["lines"]
    name, ssn = _head(tp)
    v = {"f1_01[0]": name, "f1_02[0]": ssn}
    ip = [p for p in inc.get("interest_payers") or [] if p.get("amount")] or \
        ([{"name": "Interest (see Forms 1099-INT)", "amount": L["taxable_interest"]}] if L["taxable_interest"] else [])
    for i, p in enumerate(ip[:14]):
        v[f"f1_{3 + 2 * i:02d}[0]"] = p["name"]; v[f"f1_{4 + 2 * i:02d}[0]"] = money(p["amount"])
    v["f1_31[0]"] = money(L["taxable_interest"]); v["f1_33[0]"] = money(L["taxable_interest"])
    dp = [p for p in inc.get("dividend_payers") or [] if p.get("amount")] or \
        ([{"name": "Dividends (see Forms 1099-DIV)", "amount": L["ordinary_dividends"]}] if L["ordinary_dividends"] else [])
    for i, p in enumerate(dp[:15]):
        v[f"f1_{34 + 2 * i}[0]"] = p["name"]; v[f"f1_{35 + 2 * i}[0]"] = money(p["amount"])
    v["f1_64[0]"] = money(L["ordinary_dividends"])
    fa = bool(inc.get("foreign_accounts"))
    radios = {**_yes_no("c1_1", fa), **_yes_no("c1_3", bool(inc.get("foreign_trust")))}
    if fa:
        radios.update(_yes_no("c1_2", bool(inc.get("fbar_required"))))
        v["f1_65[0]"] = inc.get("foreign_account_countries", "")
    return fill_pdf(template_path(year, "f1040sb.pdf"), v, radios=radios)


def schedule_d(year, tp, inc, fed):
    """Schedule D using 1099-B totals (basis reported to the IRS, no adjustments): lines 1a and 8a."""
    L = fed["lines"]
    name, ssn = _head(tp)
    st_h = inc.get("st_proceeds", 0) - inc.get("st_basis", 0) + inc.get("capital_gain_st", 0)
    lt_h = inc.get("lt_proceeds", 0) - inc.get("lt_basis", 0) + inc.get("capital_gain_lt", 0)
    st_net = st_h - inc.get("st_loss_carryover", 0)
    lt_net = lt_h - inc.get("lt_loss_carryover", 0)
    total = st_net + lt_net
    v = {"f1_1[0]": name, "f1_2[0]": ssn}
    if st_h or inc.get("st_proceeds"):
        v.update({"f1_3[0]": money(inc.get("st_proceeds", 0)), "f1_4[0]": money(inc.get("st_basis", 0)),
                  "f1_6[0]": money(st_h, blank_zero=False)})
    v.update({"f1_21[0]": money(inc.get("st_loss_carryover", 0), parens=False), "f1_22[0]": money(st_net)})
    if lt_h or inc.get("lt_proceeds"):
        v.update({"f1_23[0]": money(inc.get("lt_proceeds", 0)), "f1_24[0]": money(inc.get("lt_basis", 0)),
                  "f1_26[0]": money(lt_h, blank_zero=False)})
    v.update({"f1_42[0]": money(inc.get("lt_loss_carryover", 0), parens=False), "f1_43[0]": money(lt_net),
              "f2_1[0]": money(total, blank_zero=False)})
    radios = {**_yes_no("c1_1", False)}
    if total > 0:
        both = lt_net > 0
        radios.update(_yes_no("c2_1", both))
        if both:
            radios.update(_yes_no("c2_2", True))      # lines 18 and 19 are zero
    elif total < 0:
        v["f2_4[0]"] = money(L["capital_gain"])
        radios.update(_yes_no("c2_3", bool(L["qualified_dividends"])))
    return fill_pdf(template_path(year, "f1040sd.pdf"), v, radios=radios)


def schedule_c(year, tp, biz):
    name, ssn = _head(tp, ssn_dashed)
    b = biz
    v = {"f1_1[0]": name, "f1_2[0]": ssn, "f1_3[0]": b.get("description", ""), "f1_4[0]": digits(b.get("code", "")),
         "f1_5[0]": b.get("name", ""), "f1_6[0]": digits(b.get("ein", "")),
         "f1_10[0]": money(b["gross_receipts"]), "f1_11[0]": money(b["returns"]),
         "f1_12[0]": money(b["gross_income"]), "f1_14[0]": money(b["gross_income"]), "f1_16[0]": money(b["gross_income"], blank_zero=False),
         "f1_17[0]": money(b["advertising"]), "f1_18[0]": money(b["car_truck"]), "f1_19[0]": money(b["commissions"]),
         "f1_20[0]": money(b["contract_labor"]), "f1_24[0]": money(b["insurance"]), "f1_27[0]": money(b["legal_professional"]),
         "f1_28[0]": money(b["office"]), "f1_33[0]": money(b["supplies"]), "f1_34[0]": money(b["taxes_licenses"]),
         "f1_35[0]": money(b["travel"]), "f1_36[0]": money(b["meals"]), "f1_37[0]": money(b["utilities"]),
         "f1_39[0]": money(b["other_expenses"]), "f1_41[0]": money(b["expenses"], blank_zero=False),
         "f1_42[0]": money(b["net_profit"], blank_zero=False), "f1_46[0]": money(b["net_profit"], blank_zero=False)}
    if b.get("other_expenses"):
        v.update({"f2_15[0]": b.get("other_description") or "Other business expenses",
                  "f2_16[0]": money(b["other_expenses"]), "f2_33[0]": money(b["other_expenses"])})
    radios = {"c1_1[0]": "1", "c1_2[0]": "Yes", **({"c1_7[0]": "1"} if b["net_profit"] < 0 else {})}
    return fill_pdf(template_path(year, "f1040sc.pdf"), v, radios=radios)


def schedule_8812(year, tp, fed):
    L = fed["lines"]
    S = L.get("s8812") or {}
    name, ssn = _head(tp)
    v = {"f1_1[0]": name, "f1_2[0]": ssn, "f1_3[0]": money(L["agi"], blank_zero=False),
         "f1_8[0]": money(L["agi"], blank_zero=False), "f1_9[0]": str(S.get("kids", 0)),
         "f1_10[0]": money(S.get("line5", 0)), "f1_11[0]": str(S["odc_count"]) if S.get("odc_count") else "",
         "f1_12[0]": money(S.get("line7", 0)), "f1_13[0]": money(S.get("line8", 0)),
         "f1_14[0]": money(S.get("line9", 0), blank_zero=False), "f1_15[0]": money(S.get("line10", 0)),
         "f1_16[0]": money(S.get("line11", 0)), "f1_17[0]": money(S.get("line12", 0)),
         "f1_18[0]": money(S.get("line13", 0)), "f1_19[0]": money(S.get("line14", 0))}
    # line 12: "Is line 8 more than line 11?" [0] = No, [1] = Yes
    radios = {"c1_1[1]": "2"} if S.get("line12") else {"c1_1[0]": "1"}
    if S.get("line16a") and S.get("kids"):
        v.update({"f2_2[0]": money(S["line16a"]), "f2_3[0]": str(S["kids"]), "f2_4[0]": money(S["line16b"]),
                  "f2_5[0]": money(S["line17"]), "f2_6[0]": money(S["line18a"]),
                  "f2_8[0]": money(S["line19"]), "f2_9[0]": money(S["line20"]), "f2_16[0]": money(S.get("line27", 0))})
        radios["c2_1[1]" if S["line18a"] > 2500 else "c2_1[0]"] = "2" if S["line18a"] > 2500 else "1"
        radios["c2_2[1]" if S["line16b"] >= 5100 else "c2_2[0]"] = "2" if S["line16b"] >= 5100 else "1"
        if "line25" in S:
            v.update({"f2_10[0]": money(S["line23"]), "f2_12[0]": money(S["line23"]), "f2_13[0]": money(S["line24"]),
                      "f2_14[0]": money(S["line25"]), "f2_15[0]": money(S["line26"])})
    return fill_pdf(template_path(year, "f1040s8.pdf"), v, radios=radios)
