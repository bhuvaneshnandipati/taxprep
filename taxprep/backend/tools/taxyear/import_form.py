"""Add an official PDF the user supplied (e.g. downloaded by hand or uploaded in chat).

    python -m tools.taxyear.import_form --year 2026 --id it201 --file ~/Downloads/it201_2026_fill_in.pdf

Checks the file is a PDF printed for that tax year and not a draft, then copies
it to app/pdf/templates/<year>/ under the name the code expects (from
forms_manifest.yaml). Use --allow-draft only for local experiments; drafts must
never ship in a released year.
"""
from __future__ import annotations
import argparse, hashlib, pathlib, sys
from .check_forms import printed_year
from .common import TEMPLATES, get_logger, load_manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--id", required=True, help="form id from forms_manifest.yaml, e.g. f1040nr, ca540, it203")
    ap.add_argument("--file", required=True)
    ap.add_argument("--allow-draft", action="store_true")
    a = ap.parse_args(argv)
    log = get_logger("import_form")
    forms = {f["id"]: f for f in load_manifest()}
    if a.id not in forms:
        log.error("Unknown form id %s. Known: %s", a.id, ", ".join(forms)); return 1
    src = pathlib.Path(a.file).expanduser()
    data = src.read_bytes()
    if not data.startswith(b"%PDF"):
        log.error("%s is not a PDF", src); return 1
    py, draft = printed_year(data)
    if forms[a.id].get("undated"):
        py = a.year
    if py != a.year:
        log.error("%s appears to be for tax year %s, not %s", src.name, py, a.year); return 1
    if draft and not a.allow_draft:
        log.error("%s is marked DRAFT; get the final version from the agency", src.name); return 1
    dest = TEMPLATES / str(a.year) / forms[a.id]["template"].format(year=a.year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    log.info("saved %s (sha256 %s)%s", dest, hashlib.sha256(data).hexdigest(), " [DRAFT]" if draft else "")
    log.info("Next: python -m tools.taxyear.pdf_fields --from %d --to %d", a.year - 1, a.year)
    return 0


if __name__ == "__main__":
    sys.exit(main())
