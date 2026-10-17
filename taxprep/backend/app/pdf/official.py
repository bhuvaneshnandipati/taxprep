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
        "f2_17[0]": money(L["withholding_w2"]), "f2_19[0]": money(L["withholding_1042s"]),
        "f2_20[0]": money(L["withholding_total"]), "f2_21[0]": money(L["estimated_payments"]),
        "f2_23[0]": money(L["eitc"]), "f2_24[0]": money(L["actc"]), "f2_25[0]": money(L["aotc_refundable"]),
        "f2_28[0]": money(L["eitc"] + L["actc"] + L["aotc_refundable"]),
        "f2_29[0]": money(L["total_payments"], blank_zero=False),
        "f2_30[0]": money(L["overpaid"]), "f2_31[0]": money(L["overpaid"]), "f2_35[0]": money(L["owed"]),
        "f2_40[0]": tp.get("occupation", ""), "f2_44[0]": tp.get("phone", ""), "f2_45[0]": tp.get("email", ""),
    }
    radios = {"c1_8[0]": FS_1040[fed["filing_status"]], "c1_8[1]": FS_1040[fed["filing_status"]],
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
        "f2_21[0]": money(L["withholding_w2"]), "f2_24[0]": money(L["withholding_w2"]),
        "f2_27[0]": money(L["withholding_1042s"]), "f2_28[0]": money(L["estimated_payments"]),
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
