"""Compare fillable field names between two years' official PDFs.

    python -m tools.taxyear.pdf_fields --from 2025 --to 2026

Agencies often rename or renumber AcroForm fields between years. For every
template present in both years this lists fields that disappeared or appeared,
and flags removed field names that app/pdf/*.py still references - those
mappings MUST be fixed before the year can be released. Exit 2 if any
referenced field is missing.
"""
from __future__ import annotations
import argparse, re, sys
import pymupdf
from .common import PDF_CODE, TEMPLATES, get_logger, load_manifest


def fields(path) -> dict[str, str]:
    out = {}
    with pymupdf.open(path) as doc:
        for page in doc:
            for w in page.widgets() or []:
                out[w.field_name] = w.field_type_string
    return out


def referenced_names() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in PDF_CODE.glob("*.py"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="frm", type=int, required=True)
    ap.add_argument("--to", type=int, required=True)
    a = ap.parse_args(argv)
    log = get_logger("pdf_fields")
    code = referenced_names()
    broken = 0
    for f in load_manifest():
        old = TEMPLATES / str(a.frm) / f["template"].format(year=a.frm)
        new = TEMPLATES / str(a.to) / f["template"].format(year=a.to)
        if not new.exists():
            log.info(f"[missing] {f['title']}: no templates/{a.to}/{new.name} yet"); continue
        if not old.exists():
            log.info(f"[new]     {f['title']}: nothing to compare in {a.frm}"); continue
        fo, fn = fields(old), fields(new)
        gone, added = sorted(set(fo) - set(fn)), sorted(set(fn) - set(fo))
        retyped = sorted(k for k in set(fo) & set(fn) if fo[k] != fn[k])
        # Field names appear in code as their short form, e.g. f1_01[0]; match on the last segment.
        used_gone = [g for g in gone if re.search(re.escape(g.split(".")[-1]), code)]
        broken += len(used_gone)
        state = "SAME" if not (gone or added or retyped) else ("BROKEN" if used_gone else "CHANGED")
        log.info(f"[{state.lower():<7}] {f['title']}: {len(fo)} -> {len(fn)} fields, -{len(gone)} +{len(added)} ~{len(retyped)}")
        for g in used_gone:
            log.info(f"      referenced in app/pdf but removed: {g}")
        for g in gone:
            log.debug("removed %s", g)
        for n in added:
            log.debug("added %s", n)
        for r in retyped:
            log.debug("type changed %s %s->%s", r, fo[r], fn[r])
    log.info("Full field lists are in the log file. Even when names match, check every line label on the new PDF:"
             " the IRS sometimes keeps a field name but moves it to a different line.")
    return 2 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
