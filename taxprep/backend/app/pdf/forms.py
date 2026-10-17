"""Filing package = instruction/cover sheet (generated) + the OFFICIAL agency forms, filled in.

Order follows the IRS attachment-sequence numbers: Form 1040/1040-NR, Schedule 1 (seq. 01),
Schedule NEC (7B), Schedule OI (7C); Form 8843 is placed after the federal return; the state
return follows as a separate stapled set.
"""
from __future__ import annotations
import io
import pymupdf
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.pagesizes import letter
from .base import FormPage, H
from . import official
from .fill import has_template

FS_LABELS = {"single": "Single", "mfj": "Married filing jointly", "mfs": "Married filing separately",
             "hoh": "Head of household", "qss": "Qualifying surviving spouse"}


class _Pager(FormPage):
    def footer(self, form_no, page, total=None):
        c = self.c
        c.setLineWidth(0.8); c.line(36, 34, 576, 34)
        c.setFont("Helvetica", 6.5)
        c.drawString(36, 25, f"TaxPrep filing instructions - page {page} (not a tax form; do not mail)")

    """FormPage that starts a new page instead of running off the bottom."""
    def __init__(self, c, year):
        super().__init__(c)
        self.year, self.page = year, 1

    def need(self, h=20):
        if self.y - h < 50:
            self.footer("instructions", self.page)
            self.c.showPage()
            self.page += 1
            self.y = H - 50

    def text(self, s, **kw):
        self.need(12)
        super().text(s, **kw)

    def section(self, t):
        self.need(40)
        super().section(t)


def _wrap(s, n=118):
    out, line = [], ""
    for w in str(s).split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def _cover(taxpayer, result, year, included, missing) -> bytes:
    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=letter)
    c.setTitle(f"Tax Return Filing Package — TY{year}")
    p = _Pager(c, year)
    fed, st = result["federal"], result["state"]
    p.header("PKG", "Filing Instructions & Summary", year, "Prepared with TaxPrep — keep this page, do not mail it",
             sub=f"Prepared for {taxpayer.get('first_name', '')} {taxpayer.get('last_name', '')}")
    p.section("Result")
    fr = fed["lines"]["refund"]
    p.line("FED", f"Federal Form {fed['form']} ({FS_LABELS.get(fed['filing_status'], '')}): "
           + ("refund" if fr >= 0 else "amount you owe"), abs(fr), bold=True)
    if st["form"] != "none":
        sr = st["lines"]["refund"]
        p.line(st["state"], f"{st['state']} Form {st['form']}: " + ("refund" if sr >= 0 else "amount you owe"),
               abs(sr), bold=True)
    else:
        p.text(f"{st['state']}: no state income tax return required.", size=8)

    p.section("Residency determination")
    p.text(result["residency"]["label"], bold=True, size=8.5)
    for chunk in _wrap(result["residency"]["explanation"]):
        p.text(chunk, size=7.5, gap=9.5)

    warnings = (fed.get("warnings") or []) + (st.get("warnings") or [])
    if warnings or missing:
        p.section("Review before filing")
        for w in warnings:
            for i, chunk in enumerate(_wrap("! " + w, 116)):
                p.text(chunk if i == 0 else "   " + chunk, size=7.5, gap=9.5)
        for m in missing:
            for i, chunk in enumerate(_wrap(f"! Not generated — complete and attach yourself: {m}", 116)):
                p.text(chunk if i == 0 else "   " + chunk, size=7.5, gap=9.5)

    p.section("How your tax was calculated")
    for e in fed["explanations"] + st["explanations"]:
        for i, chunk in enumerate(_wrap("• " + e)):
            p.text(chunk if i == 0 else "   " + chunk, size=7.5, gap=9.5)

    p.section("What is in this package (official forms, filled in)")
    for f in included:
        p.text("• " + f, size=8)

    p.section("Filing checklist")
    for item in result["checklist"]:
        p.need(16)
        p.checks("", [(item, False)])

    p.section("Where and when to mail")
    mail = result.get("mailing") or {}
    if mail.get("federal"):
        p.text(f"Federal: {mail['federal']}", size=8)
    if mail.get("state"):
        p.text(f"{st['state']}: {mail['state']}", size=8)
    p.text("Federal due date: April 15, 2026 (June 15, 2026 for nonresident aliens who had no wages subject to "
           "U.S. withholding). Form 8843 filed alone: June 15, 2026.", size=7.5)
    p.text("Sign and date each return. Attach W-2 Copy B (and Forms 1042-S) to the federal return and W-2 Copy 2 "
           "to the state return. Keep copies of everything.", size=7.5)
    p.footer("instructions", p.page)
    c.showPage()
    c.save()
    return buf.getvalue()


def _dual_statement(taxpayer, result, year) -> bytes:
    """Dual-status statement page (Pub. 519, ch. 6): nonresident-period details."""
    buf = io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=letter)
    p = _Pager(c, year)
    fed, res = result["federal"], result["residency"]
    p.header("STMT", "Dual-Status Statement — attach to Form 1040", year,
             "Department of the Treasury—Internal Revenue Service",
             sub=f"{taxpayer.get('first_name', '')} {taxpayer.get('last_name', '')}   SSN/ITIN {taxpayer.get('ssn', '')}")
    p.section("Residency")
    p.text(f"Nonresident alien from January 1, {year} to the day before {res.get('residency_start')}; resident alien "
           f"from {res.get('residency_start')} to December 31, {year}.", size=8)
    p.section("Nonresident-period income (Form 1040-NR statement)")
    L = fed["lines"]
    p.line("1a", "Wages earned while a nonresident (effectively connected)", result.get("_wages_nr_period", 0))
    p.line("1k", "Treaty-exempt income (nonresident period)", L.get("treaty_exempt_income", 0))
    p.text("All other income shown on Form 1040 was received while a resident alien.", size=8)
    p.section("Notes")
    for t in ["Dual-status return: standard deduction not allowed; tax computed on combined taxable income "
              "using the rate schedules for your filing status.",
              "If you are married to a U.S. citizen/resident you may instead elect to be treated as a resident for "
              "the whole year and file jointly (IRC 6013(g)/(h)) — not prepared here."]:
        for chunk in _wrap(t):
            p.text(chunk, size=7.5, gap=9.5)
    p.signature()
    p.footer("STMT", 1, 1)
    c.showPage(); c.save()
    return buf.getvalue()


def build_package(taxpayer: dict, profile: dict, result: dict, year: int = 2025) -> bytes:
    fed, st, res = result["federal"], result["state"], result["residency"]
    out = pymupdf.open()
    included, missing = [], []
    parts: list[pymupdf.Document] = []

    def add(doc, label):
        parts.append(doc); included.append(label)

    mode = fed.get("mode", "resident")
    if mode == "nonresident":
        add(official.form_1040nr(year, taxpayer, fed), "Form 1040-NR")
    else:
        fed_d = dict(fed, _residency_start=res.get("residency_start", ""))
        add(official.form_1040(year, taxpayer, fed_d, dual=(mode == "dual_status")),
            "Form 1040" + (" (Dual-Status Return)" if mode == "dual_status" else ""))
    L = fed["lines"]
    if L.get("other_income") or L.get("adjustments"):
        add(official.schedule_1(year, taxpayer, fed), "Schedule 1 (Form 1040)")
    if "Schedule 2" in fed.get("schedules", []):
        add(official.schedule_2(year, taxpayer, fed), "Schedule 2 (Form 1040)")
    if mode == "nonresident":
        if L.get("nec_tax"):
            add(official.schedule_nec(year, taxpayer, fed), "Schedule NEC (Form 1040-NR)")
        add(official.schedule_oi(year, taxpayer, profile, fed, res), "Schedule OI (Form 1040-NR)")
    if mode == "dual_status":
        doc = pymupdf.open("pdf", _dual_statement(taxpayer, dict(result, _wages_nr_period=result.get("_wages_nr_period", 0)), year))
        add(doc, "Dual-status statement")
    if res.get("form_8843_required"):
        add(official.form_8843(year, taxpayer, profile, res), "Form 8843")

    # schedules the engine says are needed but that are not generated here
    generated = {"Schedule 1", "Schedule 2", "Schedule NEC (Form 1040-NR)", "Schedule OI (Form 1040-NR)",
                 "Form 1040-NR (dual-status statement)"}
    for s in fed.get("schedules", []):
        if s not in generated:
            missing.append(s)

    if st["form"] != "none":
        ca_in = {"dependents": result.get("_dependents", 0), "state_wages": result.get("_state_wages", 0),
                 "health_coverage": profile.get("health_coverage", True), "std": result.get("_state_std", 0)}
        if st["state"] == "CA":
            if st["form"] == "540":
                add(official.ca_540(year, taxpayer, fed, st, ca_in), "California Form 540")
            else:
                add(official.ca_540nr(year, taxpayer, fed, st, ca_in), "California Form 540NR")
            if abs(st["lines"].get("ca_agi", 0) - L["agi"]) >= 1 or st["form"] == "540NR":
                missing.append("California Schedule CA (" + ("540" if st["form"] == "540" else "540NR") +
                               ") — shows the adjustments on lines 14/16")
        elif st["state"] == "NY":
            if st["form"] == "IT-201":
                add(official.ny_it201(year, taxpayer, fed, st, ca_in), "New York Form IT-201")
            else:
                add(official.ny_it203(year, taxpayer, fed, st, ca_in), "New York Form IT-203")

    out.insert_pdf(pymupdf.open("pdf", _cover(taxpayer, result, year, included, missing)))
    for d in parts:
        out.insert_pdf(d)
    out.set_metadata({"title": f"Tax Return Filing Package — TY{year}", "producer": "TaxPrep"})
    return out.tobytes(garbage=3, deflate=True)
