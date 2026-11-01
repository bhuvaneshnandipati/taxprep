"""Import New York State and New York City tax tables (taxable income under $65,000) from tax.ny.gov.

    python -m tools.taxyear.ny_tables --year 2025
    python -m tools.taxyear.ny_tables --year 2025 --file saved_page.htm   # if the user downloaded the page

Writes rules/<year>/newyork_tables.yaml with rows [at_least, less_than, single/MFS, MFJ/QSS, HOH].
NY's tables cannot be reproduced exactly from the rate schedule (a few rows differ by $1),
so the engine looks up these published rows. Source page: tax.ny.gov/pit/file/tax-tables/it201i-<year>.htm
"""
from __future__ import annotations
import argparse, re, sys, urllib.request
import yaml
from .common import RULES, get_logger

URL = "https://www.tax.ny.gov/pit/file/tax-tables/it201i-{year}.htm"


def parse(html: str):
    k = html.find("New York City Tax Table")
    if k < 0:
        raise ValueError("page has no 'New York City Tax Table' section")

    def rows(part):
        out = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", part, re.S):
            c = [re.sub("<[^>]+>", "", x).replace("$", "").replace(",", "").strip()
                 for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
            if len(c) == 5 and all(re.fullmatch(r"\d+", x) for x in c):
                out.append([int(x) for x in c])
        return out
    return rows(html[:k]), rows(html[k:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--file")
    a = ap.parse_args(argv)
    log = get_logger("ny_tables")
    if a.file:
        html = open(a.file, encoding="utf-8", errors="ignore").read()
    else:
        req = urllib.request.Request(URL.format(year=a.year), headers={"User-Agent": "TaxPrep-ny-tables/1.0"})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
    nys, nyc = parse(html)
    for name, rows in (("NYS", nys), ("NYC", nyc)):
        if len(rows) < 1000 or rows[-1][1] != 65000:
            log.error("%s table looks incomplete (%d rows, last %s); ask the user for the page", name, len(rows), rows[-1:])
            return 1
    out = RULES / str(a.year) / "newyork_tables.yaml"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# NYS and NYC tax tables for taxable income under $65,000, tax year {a.year}.\n"
                f"# Source: {URL.format(year=a.year)} (imported by tools/taxyear/ny_tables.py)\n"
                f"# Row: [at least, less than, single or MFS, MFJ or QSS, head of household]\n")
        yaml.safe_dump({"year": a.year, "nys": nys, "nyc": nyc}, f, default_flow_style=None, width=200)
    log.info("wrote %s (%d NYS rows, %d NYC rows)", out, len(nys), len(nyc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
