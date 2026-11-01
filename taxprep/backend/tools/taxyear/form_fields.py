"""List the fillable fields of an official PDF with their tooltips, to write or fix a mapping.

    python -m tools.taxyear.form_fields app/pdf/templates/2025/f1040sa.pdf
    python -m tools.taxyear.form_fields app/pdf/templates/2025/f1040sa.pdf --grep "line 5"

Prints: page, short field name (what app/pdf/official.py uses), type, and the agency's
tooltip (usually the line number and label). When a PDF has no tooltips, the printed
words to the left of the field are shown instead, prefixed with "~". IRS tooltips are the most reliable way to
match a field to a line, because field numbers (f1_07...) shift between years.
"""
from __future__ import annotations
import argparse, re, sys
import pymupdf


def _context(words, r, n=14):
    """Printed words on the same row, left of the field (line number + label), when the
    PDF has no tooltip."""
    cy = (r.y0 + r.y1) / 2
    row = [w for w in words if w[1] - 2 <= cy <= w[3] + 2 and w[2] <= r.x0 + 1]
    row.sort(key=lambda w: w[0])
    return " ".join(w[4] for w in row[-n:])


def rows(path):
    with pymupdf.open(path) as doc:
        for pno, page in enumerate(doc, 1):
            words = page.get_text("words")
            for w in sorted(page.widgets() or [], key=lambda w: (round(w.rect.y0), w.rect.x0)):
                label = " ".join((w.field_label or "").split()) or "~ " + _context(words, w.rect)
                yield pno, w.field_name.rsplit(".", 1)[-1], w.field_type_string, \
                    label, (w.on_state() if w.field_type in (2, 5) else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--grep", help="only fields whose tooltip matches this regex (case-insensitive)")
    a = ap.parse_args(argv)
    for pno, name, typ, label, on in rows(a.pdf):
        if a.grep and not re.search(a.grep, label, re.I):
            continue
        print(f"p{pno} {name:<12} {typ:<9} {('on=' + str(on)) if on else '':<8} {label[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
