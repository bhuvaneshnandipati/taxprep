"""Find, verify and (optionally) download the official PDFs for a tax year.

    python -m tools.taxyear.check_forms --year 2026            # report only
    python -m tools.taxyear.check_forms --year 2026 --download # save into app/pdf/templates/2026/
    python -m tools.taxyear.check_forms --year 2026 --json     # machine-readable (CI watcher)

For each form in forms_manifest.yaml it tries the year-specific URL (and, for
IRS forms, the "current revision" URL), opens the PDF and reads which tax year
it is printed for. A PDF counts as found only if it names the requested year
and is not a draft. Forms that cannot be fetched are listed as ASK_USER: the
person must supply the official PDF (see SKILL instructions).
Run from taxprep/backend. Exit code 0 = every form found, 2 = some missing.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys, urllib.error, urllib.request
import pymupdf
from .common import TEMPLATES, get_logger, load_manifest

UA = {"User-Agent": "TaxPrep-form-check/1.0 (+https://github.com/bhuvaneshnandipati/taxprep)"}


def fetch(url: str, log) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        if not data.startswith(b"%PDF"):
            log.debug("not a PDF: %s", url); return None
        return data
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.debug("fetch failed %s: %s", url, e); return None


def printed_year(data: bytes) -> tuple[int | None, bool]:
    """(tax year printed on page 1, looks like a draft)."""
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        text = doc[0].get_text()[:4000] if len(doc) else ""
    draft = bool(re.search(r"\bDRAFT\b|Draft as of", text))
    years = [int(y) for y in re.findall(r"\b(20[2-4]\d)\b", text)]
    # The form's own year is the most common 20xx near the top of page 1.
    year = max(set(years), key=years.count) if years else None
    return year, draft


def check(year: int, download: bool, log) -> list[dict]:
    out = []
    dest = TEMPLATES / str(year)
    for f in load_manifest():
        template = f["template"].format(year=year)
        urls = [f["url"].format(year=year)]
        if f.get("prior_url"):
            urls.append(f["prior_url"].format(year=year))
        row = {"id": f["id"], "title": f["title"], "agency": f["agency"], "template": template,
               "status": "ASK_USER", "url": None, "sha256": None, "printed_year": None,
               "in_repo": (dest / template).exists()}
        for url in urls:
            data = fetch(url, log)
            if not data:
                continue
            py, draft = printed_year(data)
            log.debug("%s %s -> printed_year=%s draft=%s", f["id"], url, py, draft)
            if f.get("undated") and not draft:
                py = year      # revision-dated form: the current revision is the one to use
            elif py is None and "{year}" in f["url"] and url == f["url"].format(year=year):
                py = year      # no readable year (e.g. NY prints it in a barcode); the year-specific URL decides
            if py != year:
                row["status"], row["printed_year"] = "NOT_YET_PUBLISHED", py
                continue
            if draft:
                row["status"], row["url"], row["printed_year"] = "DRAFT_ONLY", url, py
                continue
            row.update(status="FOUND", url=url, printed_year=py, sha256=hashlib.sha256(data).hexdigest())
            if download:
                dest.mkdir(parents=True, exist_ok=True)
                (dest / template).write_bytes(data)
                row["in_repo"] = True
                log.info("saved %s", dest / template)
            break
        if row["status"] != "FOUND" and row["in_repo"]:
            row["status"] = "IN_REPO_UNVERIFIED"
        out.append(row)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    log = get_logger("check_forms")
    rows = check(a.year, a.download, log)
    if a.json:
        print(json.dumps({"year": a.year, "forms": rows}, indent=2))
    else:
        log.info(f"Official forms for tax year {a.year}:")
        for r in rows:
            log.info(f"  {r['status']:<20} {r['title']:<32} -> templates/{a.year}/{r['template']}"
                     + (f"  ({r['url']})" if r["url"] else ""))
        missing = [r for r in rows if r["status"] != "FOUND"]
        if missing:
            log.info("\nNot available online as a final %s PDF: %s", a.year, ", ".join(r["title"] for r in missing))
            log.info("ASK THE USER to upload these official PDFs, or wait until the agency publishes them.")
    return 0 if all(r["status"] == "FOUND" for r in rows) else 2


if __name__ == "__main__":
    sys.exit(main())
