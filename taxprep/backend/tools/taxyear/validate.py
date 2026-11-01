"""Check whether a tax year is consistent and ready for a release status.

    python -m tools.taxyear.validate --year 2026                     # check against its own status
    python -m tools.taxyear.validate --year 2026 --target released   # could it be released?

Checks, in order:
  1. meta.yaml status, and every rule pack's `year:` value
  2. same rule packs and value structure as the previous year (missing keys break the engine)
  3. SOURCES.md ledger: one row per value, ledger value == YAML value,
     no TODO rows and a source URL + check date for preview/released
  4. every official PDF template from forms_manifest.yaml is present (preview/released)
  5. code that still hard-codes the previous year (warnings to review)
Exit 0 = OK for the target status, 1 = errors. Warnings never fail the run.
"""
from __future__ import annotations
import argparse, re, sys
from .common import (BACKEND, LEDGER_PACKS, RULES, TEMPLATES, get_logger, load_manifest, load_yaml,
                     pack_leaves, previous_year, show)

ORDER = {"draft": 0, "preview": 1, "released": 2}
ROW = re.compile(r"^\|\s*(?P<pack>[a-z0-9_]+)\s*\|\s*(?P<path>.+?)\s*\|\s*(?P<old>.*?)\s*\|\s*(?P<new>.*?)\s*\|"
                 r"\s*(?P<status>TODO|CONFIRMED|CHANGED)\s*\|\s*(?P<url>.*?)\s*\|\s*(?P<where>.*?)\s*\|\s*(?P<checked>.*?)\s*\|\s*$")


def unescape(s: str) -> str:
    return s.replace("\\|", "|")


def read_ledger(path):
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            d = {k: unescape(v) for k, v in m.groupdict().items()}
            rows[(d["pack"], d["path"])] = d
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--target", choices=list(ORDER), help="status to check readiness for (default: current status)")
    a = ap.parse_args(argv)
    log = get_logger("validate")
    errors, warnings = [], []
    ydir = RULES / str(a.year)
    if not ydir.is_dir():
        log.error("rules/%d does not exist. Start it with: python -m tools.taxyear.new_year --to %d", a.year, a.year)
        return 1

    # 1. meta and year fields
    meta = load_yaml(ydir / "meta.yaml") if (ydir / "meta.yaml").exists() else {}
    status = meta.get("status", "draft")
    if status not in ORDER:
        errors.append(f"meta.yaml status '{status}' is not one of {list(ORDER)}")
        status = "draft"
    target = a.target or status
    for f in sorted(ydir.glob("*.yaml")):
        if f.name == "meta.yaml":
            continue
        y = (load_yaml(f) or {}).get("year")
        if y != a.year:
            errors.append(f"{f.name}: year is {y}, expected {a.year}")

    # 2. structure vs previous year
    prev = previous_year(a.year)
    if prev:
        prev_packs = {p.stem for p in (RULES / str(prev)).glob("*.yaml")} - {"meta"}
        packs = {p.stem for p in ydir.glob("*.yaml")} - {"meta"}
        for p in sorted(prev_packs - packs):
            errors.append(f"rule pack {p}.yaml exists in {prev} but not in {a.year}")
        for pack in LEDGER_PACKS:
            if pack not in packs or pack not in prev_packs:
                continue
            old, new = pack_leaves(prev, pack), pack_leaves(a.year, pack)
            for k in sorted(set(old) - set(new)):
                errors.append(f"{pack}: '{k}' missing (present in {prev}; the engine may read it)")
            for k in sorted(set(new) - set(old)):
                warnings.append(f"{pack}: new key '{k}' - make sure the engine uses it")
            for k in sorted(set(old) & set(new)):
                if old[k] is not None and new[k] is not None and type(old[k]) is not type(new[k]) \
                        and not {type(old[k]), type(new[k])} <= {int, float}:
                    errors.append(f"{pack}: '{k}' changed type {type(old[k]).__name__} -> {type(new[k]).__name__}")

    # 3. ledger
    ledger_path = ydir / meta.get("sources_ledger", "SOURCES.md")
    todo = changed = confirmed = 0
    if not ledger_path.exists():
        (errors if ORDER[target] >= 2 else warnings).append(f"no source ledger {ledger_path.name}")
    else:
        ledger = read_ledger(ledger_path)
        for pack in LEDGER_PACKS:
            if not (ydir / f"{pack}.yaml").exists():
                continue
            for k, v in pack_leaves(a.year, pack).items():
                row = ledger.get((pack, k))
                if not row:
                    errors.append(f"SOURCES.md has no row for {pack} {k}"); continue
                if row["new"] != show(v):
                    errors.append(f"SOURCES.md {pack} {k}: ledger says {row['new']} but YAML is {show(v)}")
                if row["status"] == "TODO":
                    todo += 1
                    continue
                changed += row["status"] == "CHANGED"; confirmed += row["status"] == "CONFIRMED"
                if not row["url"].startswith("http") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["checked"]):
                    errors.append(f"SOURCES.md {pack} {k}: {row['status']} needs a source URL and a YYYY-MM-DD check date")
        log.info(f"Ledger: {confirmed} confirmed, {changed} changed, {todo} still TODO")
        if todo and ORDER[target] >= 1:
            errors.append(f"{todo} ledger rows are still TODO (all must be checked for {target})")

    # 4. templates
    missing = [f["template"].format(year=a.year) for f in load_manifest()
               if not (TEMPLATES / str(a.year) / f["template"].format(year=a.year)).exists()]
    if missing:
        msg = f"official PDFs missing in templates/{a.year}: {', '.join(missing)} (run check_forms --download or ask the user)"
        (errors if ORDER[target] >= 1 else warnings).append(msg)

    # 5. hard-coded previous year in code
    if prev:
        for p in sorted((BACKEND / "app").rglob("*.py")) + sorted((BACKEND.parent / "frontend").glob("[!n]*/**/*.ts*")):
            if "node_modules" in p.parts:
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if str(prev) in line and not line.lstrip().startswith(("#", "//")):
                    warnings.append(f"hard-coded {prev}: {p.relative_to(BACKEND.parent)}:{i}: {line.strip()[:100]}")

    for w in warnings:
        log.info("WARN  %s", w)
    for e in errors:
        log.info("ERROR %s", e)
    ok = not errors
    log.info(f"\nTax year {a.year}: status={status}, checked for '{target}': {'OK' if ok else f'{len(errors)} error(s)'}"
             f", {len(warnings)} warning(s)")
    if ok and ORDER[target] > ORDER[status]:
        log.info(f"Ready to set status: {target} in rules/{a.year}/meta.yaml (after tests pass and a person approves).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
