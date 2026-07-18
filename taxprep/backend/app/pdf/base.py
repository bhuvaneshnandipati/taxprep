"""Shared drawing toolkit replicating IRS/FTB form visual language.

All renderers draw onto a reportlab canvas via FormPage. Layout constants
mirror official forms: header band, ruled amount boxes with line numbers,
dotted leaders, section bars.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as _canvas

W, H = letter
ML, MR = 36, 36          # margins
LINE_H = 15.5            # standard line-item height
AMT_W = 78               # amount box width
NUM_W = 20               # line-number box width


def money(v) -> str:
    if v is None:
        return ""
    v = round(float(v))
    return f"({abs(v):,})" if v < 0 else f"{v:,}"


class FormPage:
    def __init__(self, c: _canvas.Canvas):
        self.c = c
        self.y = H - 40

    # ---------- header ----------
    def header(self, form_no: str, title: str, year: int, agency: str,
               sub: str = "", omb: str = ""):
        c = self.c
        c.setLineWidth(1.6)
        c.line(ML, H - 34, W - MR, H - 34)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(ML, H - 44, "Form")
        c.setFont("Helvetica-Bold", 22)
        c.drawString(ML + 22, H - 56, form_no)
        c.setFont("Helvetica", 6.5)
        c.drawString(ML, H - 64, agency)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(W / 2, H - 48, title)
        if sub:
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(W / 2, H - 59, sub)
        c.setFont("Helvetica-Bold", 16)
        c.drawRightString(W - MR, H - 52, str(year))
        if omb:
            c.setFont("Helvetica", 6.5)
            c.drawRightString(W - MR, H - 62, omb)
        c.setLineWidth(1.2)
        c.line(ML, H - 70, W - MR, H - 70)
        self.y = H - 84

    # ---------- identity block ----------
    def id_block(self, fields: list[tuple[str, str]], cols: int = 2):
        """fields: [(label, value)] drawn as ruled boxes."""
        c = self.c
        col_w = (W - ML - MR) / cols
        row_h = 26
        x0, y0 = ML, self.y
        for i, (label, value) in enumerate(fields):
            r, col = divmod(i, cols)
            x = x0 + col * col_w
            y = y0 - r * row_h
            c.setLineWidth(0.5)
            c.rect(x, y - row_h, col_w, row_h)
            c.setFont("Helvetica", 6)
            c.drawString(x + 3, y - 8, label.upper())
            c.setFont("Helvetica", 9.5)
            c.drawString(x + 3, y - 21, str(value or ""))
        rows = -(-len(fields) // cols)
        self.y = y0 - rows * row_h - 8

    # ---------- section bar ----------
    def section(self, text: str):
        c = self.c
        self.y -= 4
        c.setFillGray(0.15)
        c.rect(ML, self.y - 13, W - ML - MR, 13, fill=1, stroke=0)
        c.setFillGray(1)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(ML + 4, self.y - 10, text)
        c.setFillGray(0)
        self.y -= 17

    # ---------- line item ----------
    def line(self, num: str, label: str, amount=None, *, bold=False,
             indent=0, text_value: str | None = None):
        c = self.c
        y = self.y
        c.setLineWidth(0.4)
        # line-number box
        c.rect(ML, y - LINE_H + 3, NUM_W, LINE_H - 3)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(ML + NUM_W / 2, y - LINE_H + 7.5, num)
        # label with dotted leader
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
        lx = ML + NUM_W + 5 + indent
        label_end_x = W - MR - AMT_W - 8
        c.drawString(lx, y - LINE_H + 7.5, label)
        tw = c.stringWidth(label, "Helvetica-Bold" if bold else "Helvetica", 8)
        dot_x = lx + tw + 4
        c.setFont("Helvetica", 8)
        while dot_x < label_end_x - 4:
            c.drawString(dot_x, y - LINE_H + 7.5, ".")
            dot_x += 6
        # amount box
        c.rect(W - MR - AMT_W, y - LINE_H + 3, AMT_W, LINE_H - 3)
        val = text_value if text_value is not None else money(amount)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8.5)
        c.drawRightString(W - MR - 4, y - LINE_H + 7.5, val)
        self.y -= LINE_H

    # ---------- checkbox row ----------
    def checks(self, prompt: str, options: list[tuple[str, bool]]):
        c = self.c
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(ML, self.y - 9, prompt)
        x = ML + c.stringWidth(prompt, "Helvetica-Bold", 7.5) + 10
        c.setFont("Helvetica", 7.5)
        for label, checked in options:
            c.rect(x, self.y - 11, 7, 7)
            if checked:
                c.setFont("Helvetica-Bold", 8)
                c.drawString(x + 1, self.y - 10, "X")
                c.setFont("Helvetica", 7.5)
            c.drawString(x + 10, self.y - 9.5, label)
            x += 20 + c.stringWidth(label, "Helvetica", 7.5)
        self.y -= 16

    def text(self, s: str, *, size=7.5, bold=False, gap=11):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(ML, self.y - 8, s)
        self.y -= gap

    def free_field(self, label: str, value: str, width: float | None = None):
        c = self.c
        width = width or (W - ML - MR)
        c.setLineWidth(0.5)
        c.rect(ML, self.y - 24, width, 24)
        c.setFont("Helvetica", 6)
        c.drawString(ML + 3, self.y - 8, label.upper())
        c.setFont("Helvetica", 9)
        c.drawString(ML + 3, self.y - 20, str(value or ""))
        self.y -= 30

    # ---------- signature block ----------
    def signature(self, extra: str = ""):
        c = self.c
        self.section("Sign Here")
        c.setFont("Helvetica", 6.5)
        c.drawString(ML, self.y - 8,
                     "Under penalties of perjury, I declare that I have examined this return and accompanying schedules and statements, and to the best of my")
        c.drawString(ML, self.y - 16,
                     "knowledge and belief, they are true, correct, and complete." + (" " + extra if extra else ""))
        self.y -= 28
        half = (W - ML - MR - 20) / 2
        c.setLineWidth(0.5)
        c.line(ML, self.y, ML + half, self.y)
        c.line(ML + half + 20, self.y, W - MR, self.y)
        c.setFont("Helvetica", 6)
        c.drawString(ML, self.y - 7, "Your signature")
        c.drawString(ML + half + 20, self.y - 7, "Date")
        self.y -= 20

    def footer(self, form_no: str, page: int, total: int):
        c = self.c
        c.setLineWidth(0.8)
        c.line(ML, 34, W - MR, 34)
        c.setFont("Helvetica", 6.5)
        c.drawString(ML, 25, f"Form {form_no} ({page} of {total})")
        c.drawRightString(W - MR, 25, "Generated by TaxPrep")
