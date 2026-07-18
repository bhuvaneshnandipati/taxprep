"""Form renderers. Each takes taxpayer info + computed lines and draws
the form onto a shared canvas, replicating the official layout.

f1040       -> Form 1040 / 1040-NR (shared line structure, NR variants)
f8843       -> Form 8843 Part I + Part III
ca540       -> California Form 540 / 540NR
build_package -> cover summary + explanations + checklist + all forms, one PDF
"""
import io
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.pagesizes import letter
from .base import FormPage, money, W, H, ML, MR

FS_LABELS = {"single": "Single", "mfj": "Married filing jointly",
             "mfs": "Married filing separately", "hoh": "Head of household",
             "qss": "Qualifying surviving spouse"}


def f1040(c, taxpayer: dict, fed: dict, year: int):
    is_nr = fed["form"] == "1040-NR"
    L = fed["lines"]
    p = FormPage(c)
    p.header(fed["form"],
             "U.S. Nonresident Alien Income Tax Return" if is_nr else "U.S. Individual Income Tax Return",
             year, "Department of the Treasury—Internal Revenue Service",
             omb="OMB No. 1545-0074")
    p.id_block([
        ("Your first name and middle initial", taxpayer.get("first_name", "")),
        ("Last name", taxpayer.get("last_name", "")),
        ("Your social security number / ITIN", taxpayer.get("ssn", "")),
        ("Home address (number and street)", taxpayer.get("address", "")),
        ("City, state, ZIP", taxpayer.get("city_state_zip", "")),
        ("Foreign country (if applicable)", taxpayer.get("country", "") if is_nr else ""),
    ], cols=3)
    fs = fed["filing_status"]
    opts = [("Single", fs == "single"), ("MFS", fs == "mfs"), ("QSS", fs == "qss")] if is_nr else \
           [("Single", fs == "single"), ("MFJ", fs == "mfj"), ("MFS", fs == "mfs"),
            ("HOH", fs == "hoh"), ("QSS", fs == "qss")]
    p.checks("Filing Status:", opts)

    p.section("Income")
    p.line("1a", "Total amount from Form(s) W-2, box 1", L["1a_wages"])
    p.line("2b", "Taxable interest", L["2b_interest"])
    p.line("3b", "Ordinary dividends", L["3b_dividends"])
    p.line("7", "Capital gain or (loss). Attach Schedule D if required", L["7_capital_gain"])
    p.line("8", "Additional income from Schedule 1", L["8_other_income"])
    p.line("9", "Add lines 1a through 8. This is your total income", L["9_total_income"], bold=True)
    p.line("10", "Adjustments to income from Schedule 1", L["10_adjustments"])
    p.line("11", "Subtract line 10 from line 9. This is your adjusted gross income", L["11_agi"], bold=True)
    treaty_std = bool((fed.get("treaty") or {}).get("standard_deduction"))
    p.line("12", "Itemized deductions (Schedule A, Form 1040-NR)" if (is_nr and not treaty_std)
           else "Standard deduction or itemized deductions", L["12_deduction"])
    p.line("15", "Subtract line 12 from line 11. This is your taxable income", L["15_taxable_income"], bold=True)

    p.section("Tax and Credits")
    p.line("16", "Tax (see instructions)", L["16_tax"])
    p.line("19", "Child tax credit or credit for other dependents", L["19_ctc_odc"])
    p.line("20", "Other credits (Schedule 3)", L["20_other_credits"])
    p.line("22", "Subtract credits from line 16", L["22_after_credits"], bold=True)
    p.line("23", "Other taxes, including self-employment tax (Schedule 2)", L["23_other_taxes"])
    p.line("24", "Add lines 22 and 23. This is your total tax", L["24_total_tax"], bold=True)

    p.section("Payments")
    p.line("25", "Federal income tax withheld from Forms W-2 and 1099", L["25_withholding"])
    if not is_nr:
        p.line("27", "Earned income credit (EIC)", L["27_eitc"])
        p.line("28", "Additional child tax credit", L["28_actc"])
        p.line("29", "American opportunity credit (Form 8863, line 8)", L["29_aotc_refundable"])
    p.line("33", "Total payments", L["33_total_payments"], bold=True)

    refund = L["refund"]
    p.section("Refund / Amount You Owe")
    if refund >= 0:
        p.line("34", "Amount you overpaid — this is your refund", refund, bold=True)
        p.line("37", "Amount you owe", 0)
    else:
        p.line("34", "Amount you overpaid", 0)
        p.line("37", "Amount you owe", abs(refund), bold=True)

    if is_nr and fed.get("treaty") and fed["treaty"].get("articles"):
        p.section("Schedule OI — Treaty Information (excerpt)")
        p.text(f"Country: {fed['treaty']['country']}    Treaty article(s): {fed['treaty']['articles']}", size=8)
        exempt = fed["treaty"]["wage_exempt"] + fed["treaty"]["scholarship_exempt"]
        if exempt:
            p.text(f"Exempt income claimed under treaty: ${exempt:,.0f}", size=8)

    p.signature()
    p.footer(fed["form"], 1, 1)
    c.showPage()


def f8843(c, taxpayer: dict, profile: dict, year: int):
    p = FormPage(c)
    p.header("8843", "Statement for Exempt Individuals and Individuals With a Medical Condition",
             year, "Department of the Treasury—Internal Revenue Service",
             sub="For use by alien individuals only.", omb="OMB No. 1545-0074")
    p.id_block([
        ("Your first name and initial", taxpayer.get("first_name", "")),
        ("Last name", taxpayer.get("last_name", "")),
        ("U.S. taxpayer identification number, if any", taxpayer.get("ssn", "")),
    ], cols=3)

    p.section("Part I — General Information")
    p.free_field("1a  Type of U.S. visa and date you entered the United States",
                 f"{profile.get('visa','')} — first entry {profile.get('first_entry_year','')}")
    p.free_field("1b  Current nonimmigrant status", profile.get("visa", ""))
    p.free_field("2   Country of citizenship during the tax year", profile.get("country", ""))
    p.line("4a", f"Days present in the United States during {year}", None,
           text_value=str(profile.get("days_current", "")))
    p.line("4a", f"Days present during {year-1}", None, text_value=str(profile.get("days_prior1", "")))
    p.line("4a", f"Days present during {year-2}", None, text_value=str(profile.get("days_prior2", "")))
    p.line("4b", f"Days in {year} you claim you can exclude", None,
           text_value=str(profile.get("days_current", "")))

    p.section("Part III — Students")
    p.free_field("9   Academic institution attended during " + str(year),
                 taxpayer.get("school", ""))
    p.checks("12  Were you present in the U.S. as a student for any part of more than 5 calendar years?",
             [("Yes", False), ("No", True)])
    p.signature("This form is filed by exempt individuals to exclude days of presence for the Substantial Presence Test.")
    p.footer("8843", 1, 1)
    c.showPage()


STATE_META = {
    "CA": {"agency": "Franchise Tax Board — State of California",
           "titles": {"540": "California Resident Income Tax Return",
                       "540NR": "California Nonresident or Part-Year Resident Income Tax Return"},
           "labels": {"17": "California adjusted gross income", "18": "CA standard deduction or itemized deductions",
                       "19": "Taxable income", "31": "Tax", "32": "Exemption credits",
                       "64": "Total tax", "71": "California income tax withheld"},
           "refund_line": ("115", "111")},
    "NY": {"agency": "Department of Taxation and Finance — State of New York",
           "titles": {"IT-201": "New York Resident Income Tax Return",
                       "IT-203": "New York Nonresident and Part-Year Resident Income Tax Return"},
           "labels": {"19": "Federal adjusted gross income", "34": "Standard deduction and dependent exemptions",
                       "37": "Taxable income", "39": "New York State tax",
                       "46": "Total New York State taxes", "72": "Total New York State tax withheld"},
           "refund_line": ("78", "80")},
}


def state_form(c, taxpayer: dict, state: dict, fed: dict, year: int):
    L = state["lines"]
    form = state["form"]
    code = state.get("state", "CA")
    meta = STATE_META.get(code, STATE_META["CA"])
    p = FormPage(c)
    p.header(form, meta["titles"].get(form, f"{code} Income Tax Return"), year, meta["agency"])
    p.id_block([
        ("First name", taxpayer.get("first_name", "")),
        ("Last name", taxpayer.get("last_name", "")),
        ("SSN or ITIN", taxpayer.get("ssn", "")),
        ("Address", taxpayer.get("address", "")),
        ("City, State, ZIP", taxpayer.get("city_state_zip", "")),
        ("Filing status", FS_LABELS.get(fed["filing_status"], "")),
    ], cols=3)

    p.section("Taxable Income / Tax / Payments")
    labels = meta["labels"]
    for key, val in L.items():
        if key == "refund":
            continue
        num = key.split("_", 1)[0]
        label = labels.get(num, key.split("_", 1)[1].replace("_", " ").capitalize())
        p.line(num, label, val, bold=num in ("19", "37", "64", "46"))

    refund = L["refund"]
    rl_refund, rl_owe = meta["refund_line"]
    p.section("Refund / Tax Due")
    if refund >= 0:
        p.line(rl_refund, "REFUND — amount overpaid", refund, bold=True)
    else:
        p.line(rl_owe, "AMOUNT YOU OWE", abs(refund), bold=True)

    p.signature()
    p.footer(form, 1, 1)
    c.showPage()


def _cover(c, taxpayer, result, year):
    p = FormPage(c)
    fed, st, checklist = result["federal"], result["state"], result["checklist"]
    p.header("PKG", "Tax Return Filing Package", year, "Prepared with TaxPrep",
             sub=f"Prepared for {taxpayer.get('first_name','')} {taxpayer.get('last_name','')}")

    p.section("Refund Summary")
    fr, sr = fed["lines"]["refund"], st["lines"]["refund"]
    p.line("FED", f"Federal ({fed['form']}): " + ("refund" if fr >= 0 else "amount you owe"), abs(fr), bold=True)
    st_code = st.get("state", "CA")
    if st["form"] == "none":
        p.line(st_code, f"{st_code}: no state income tax return required", 0, bold=True)
    else:
        p.line(st_code, f"{st_code} ({st['form']}): " + ("refund" if sr >= 0 else "amount you owe"), abs(sr), bold=True)

    p.section("Residency Determination")
    p.text(result["residency"]["label"], bold=True, size=8.5)
    for chunk in _wrap(result["residency"]["explanation"], 118):
        p.text(chunk, size=7.5, gap=9.5)

    p.section("How Your Tax Was Calculated")
    for e in fed["explanations"] + st["explanations"]:
        for i, chunk in enumerate(_wrap(("• " if True else "") + e, 118)):
            p.text(chunk if i == 0 else "   " + chunk, size=7.5, gap=9.5)

    p.section("Filing Checklist")
    for item in checklist:
        p.checks("", [(item, False)])

    p.section("Mailing Addresses & Payment")
    if fed["form"] == "1040-NR":
        p.text("Federal: Department of the Treasury, Internal Revenue Service, Austin, TX 73301-0215", size=8)
    elif fr >= 0:
        p.text("Federal (refund): Department of the Treasury, Internal Revenue Service, Fresno, CA 93888-0002", size=8)
    else:
        p.text("Federal (payment): Internal Revenue Service, P.O. Box 802501, Cincinnati, OH 45280-2501", size=8)
        p.text("Pay online at irs.gov/payments, or enclose a check payable to 'United States Treasury' with Form 1040-V.", size=8)
    if st["form"] != "none":
        if st_code == "NY":
            if sr >= 0:
                p.text("New York (refund): State Processing Center, PO Box 61000, Albany, NY 12261-0001", size=8)
            else:
                p.text("New York (payment): State Processing Center, PO Box 15555, Albany, NY 12212-5555", size=8)
        else:
            if sr >= 0:
                p.text("California (refund): Franchise Tax Board, PO Box 942840, Sacramento, CA 94240-0001", size=8)
            else:
                p.text("California (payment): Franchise Tax Board, PO Box 942867, Sacramento, CA 94267-0001", size=8)
                p.text("Pay online at ftb.ca.gov/pay, or enclose a check payable to 'Franchise Tax Board' with Form FTB 3582.", size=8)
    p.text("Track your federal refund at irs.gov/refunds; your state refund on the state tax agency website.", size=8)
    p.footer("PKG", 1, 1)
    c.showPage()


def _wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def build_package(taxpayer: dict, profile: dict, result: dict, year: int = 2025) -> bytes:
    """Assemble the complete filing package as a single PDF (bytes)."""
    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=letter)
    c.setTitle(f"Tax Return Filing Package — TY{year}")
    _cover(c, taxpayer, result, year)
    f1040(c, taxpayer, result["federal"], year)
    if result["residency"].get("form_8843_required"):
        f8843(c, taxpayer, profile, year)
    if result["state"]["form"] != "none":
        state_form(c, taxpayer, result["state"], result["federal"], year)
    c.save()
    return buf.getvalue()
