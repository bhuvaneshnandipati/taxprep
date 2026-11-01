"""Start a new tax year from the previous one, as a hidden DRAFT.

    python -m tools.taxyear.new_year --to 2026            # copies from the latest earlier year
    python -m tools.taxyear.new_year --from 2025 --to 2026

Creates rules/<to>/ (copied rule packs with year updated, meta.yaml status
draft) and rules/<to>/SOURCES.md: one ledger row per rule value, pre-filled
with last year's value and status TODO. Nothing in the app changes until the
year is validated and its status is raised (see validate.py).
"""
from __future__ import annotations
import argparse, datetime as dt, re, sys
from .common import LEDGER_PACKS, RULES, get_logger, pack_leaves, previous_year, show

HEADER = """# Source ledger: tax year {to}

Every rule value used for TY{to} must be traced to an official source before release.
`python -m tools.taxyear.validate --year {to}` reads this table.

Status values: `TODO` (not checked yet), `CONFIRMED` (same as {frm}, re-checked in a {to} source),
`CHANGED` (new value from a {to} source). For CONFIRMED/CHANGED rows fill `Source URL`,
`Where` (page / line / table) and `Checked` (YYYY-MM-DD). `{to} value` must equal the YAML value.

Started {today} from rules/{frm}.

| Pack | Path | {frm} value | {to} value | Status | Source URL | Where | Checked |
| --- | --- | --- | --- | --- | --- | --- | --- |
"""


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="frm", type=int)
    ap.add_argument("--to", type=int, required=True)
    a = ap.parse_args(argv)
    log = get_logger("new_year")
    frm = a.frm or previous_year(a.to)
    src, dst = RULES / str(frm), RULES / str(a.to)
    if not frm or not src.is_dir():
        log.error("No source rules for %s", frm); return 1
    if dst.exists():
        log.error("%s already exists; refusing to overwrite", dst); return 1
    dst.mkdir()
    for f in sorted(src.glob("*.yaml")):
        text = f.read_text(encoding="utf-8")
        if f.name == "meta.yaml":
            continue
        text = re.sub(rf"^year:\s*{frm}\s*$", f"year: {a.to}", text, count=1, flags=re.M)
        (dst / f.name).write_text(text, encoding="utf-8")
        log.info("copied %s", f.name)
    (dst / "meta.yaml").write_text(
        f"# See rules/{frm}/meta.yaml for status meanings.\n"
        f"year: {a.to}\nstatus: draft\nsources_ledger: SOURCES.md\n"
        f"templates_dir: app/pdf/templates/{a.to}\nnotes: Started from {frm}. Values are last year's until checked.\n",
        encoding="utf-8")
    rows = []
    for pack in LEDGER_PACKS:
        if not (dst / f"{pack}.yaml").exists():
            continue
        for path, v in pack_leaves(a.to, pack).items():
            rows.append(f"| {pack} | {esc(path)} | {esc(show(v))} | {esc(show(v))} | TODO |  |  |  |")
    (dst / "SOURCES.md").write_text(
        HEADER.format(to=a.to, frm=frm, today=dt.date.today().isoformat()) + "\n".join(rows) + "\n", encoding="utf-8")
    log.info("wrote %s (%d values to check)", dst / "SOURCES.md", len(rows))
    log.info("Next: python -m tools.taxyear.check_forms --year %d --download", a.to)
    return 0


if __name__ == "__main__":
    sys.exit(main())
