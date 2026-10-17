"""Low-level AcroForm filling for the official IRS / FTB / NY fill-in PDFs (PyMuPDF).

Templates live in app/pdf/templates/<year>/ exactly as published by the agencies.
Each filled form is *flattened* (widgets baked into page content) before being merged, because
the agencies reuse the same field names across forms (e.g. IRS "f1_01[0]") and merged AcroForms
would otherwise overwrite each other's values.
"""
from __future__ import annotations
import pathlib, re
import pymupdf

TEMPLATES = pathlib.Path(__file__).resolve().parent / "templates"


def template_path(year: int, name: str) -> pathlib.Path:
    p = TEMPLATES / str(year) / name
    if not p.exists():
        raise FileNotFoundError(f"Official form template missing: {p.name} (tax year {year})")
    return p


def has_template(year: int, name: str) -> bool:
    return (TEMPLATES / str(year) / name).exists()


# ------------------------------------------------------------------ formatting helpers
def money(v, commas: bool = True, blank_zero: bool = True, parens: bool = True) -> str:
    """Whole-dollar amount as the agencies want it. Losses in parentheses."""
    if v is None:
        return ""
    n = int(round(float(v)))
    if n == 0 and blank_zero:
        return ""
    s = f"{abs(n):,}" if commas else str(abs(n))
    if n < 0:
        return f"({s})" if parens else f"-{s}"
    return s


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def ssn_dashed(s: str) -> str:
    d = digits(s)
    return f"{d[:3]}-{d[3:5]}-{d[5:]}" if len(d) == 9 else (s or "")


def mmddyyyy(iso: str, sep: str = "/") -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(2)}{sep}{m.group(3)}{sep}{m.group(1)}" if m else ""


# ------------------------------------------------------------------ fill / flatten
def _short(name: str) -> str:
    """'topmostSubform[0].Page1[0].f1_47[0]' -> 'f1_47[0]'."""
    return name.rsplit(".", 1)[-1]


def fill_pdf(path: pathlib.Path, values: dict, *, radios: dict | None = None,
             flatten: bool = True) -> pymupdf.Document:
    """values: {field (full or short name): str | bool}.  For checkbox / radio *widgets that share a
    name* (e.g. IRS 'c1_8[0]' appears twice), pass radios={short_or_full_name: on_state} instead —
    the widget whose on-state matches is turned on and the rest off.
    Unknown names raise KeyError so a template change can never silently drop a value."""
    doc = pymupdf.open(path)
    radios = dict(radios or {})
    pending = {k: v for k, v in values.items() if v not in (None, "", False)}
    found: set = set()
    for page in doc:
        for w in page.widgets():
            full, short = w.field_name, _short(w.field_name)
            key = full if full in pending else short if short in pending else None
            rkey = full if full in radios else short if short in radios else None
            if rkey is not None and w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX,
                                                    pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON):
                found.add(rkey)
                if str(w.on_state()) == str(radios[rkey]):      # only touch the chosen button
                    w.field_value = True if w.field_type == pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON else w.on_state()
                    w.update()
                continue
            if key is None:
                continue
            found.add(key)
            v = pending[key]
            if w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON):
                w.field_value = w.on_state() if v else "Off"
            else:
                text = str(v)
                if w.text_maxlen and len(text) > w.text_maxlen:
                    text = text[: w.text_maxlen]
                w.field_value = text
            w.update()
    missing = (set(pending) | set(radios)) - found
    if missing:
        raise KeyError(f"{path.name}: unknown field(s) {sorted(missing)[:8]}")
    if flatten:
        doc.bake(annots=True, widgets=True)
    return doc


def stamp(doc: pymupdf.Document, page: int, text: str, x: float, y: float, size: float = 11,
          color=(0.75, 0, 0)):
    """Write free text on a page (e.g. 'DUAL-STATUS RETURN' across the top of Form 1040)."""
    doc[page].insert_text((x, y), text, fontsize=size, fontname="helv", color=color)
