"""Loads TY-versioned rule packs. Tax law lives in YAML, never in code.

Each year directory may contain meta.yaml with a release `status`
(draft / preview / released). Draft years are hidden unless the
ALLOW_DRAFT_TAX_YEARS environment variable is set, so a half-finished
year can be committed without becoming selectable in production.
"""
import functools, os, pathlib, re, yaml

RULES_DIR = pathlib.Path(__file__).resolve().parents[2] / "rules"
DEFAULT_YEAR = 2025
STATUSES = ("draft", "preview", "released")

@functools.lru_cache(maxsize=None)
def load_rules(pack: str, year: int = DEFAULT_YEAR) -> dict:
    if not re.fullmatch(r"[a-z0-9_]{1,40}", pack or ""):
        raise FileNotFoundError(f"Invalid rule pack name '{pack}'")
    path = RULES_DIR / str(year) / f"{pack}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No rule pack '{pack}' for tax year {year}")
    with open(path) as f:
        return yaml.safe_load(f)

def year_meta(year: int) -> dict:
    """Release metadata for a year. A year without meta.yaml is treated as draft."""
    path = RULES_DIR / str(year) / "meta.yaml"
    if not path.exists():
        return {"year": year, "status": "draft"}
    with open(path) as f:
        meta = yaml.safe_load(f) or {}
    if meta.get("status") not in STATUSES:
        raise ValueError(f"rules/{year}/meta.yaml: status must be one of {STATUSES}")
    return meta

def year_status(year: int) -> str:
    return year_meta(year)["status"]

def _drafts_allowed() -> bool:
    return os.getenv("ALLOW_DRAFT_TAX_YEARS", "").lower() not in ("", "0", "false")

def all_years():
    return sorted(int(p.name) for p in RULES_DIR.iterdir() if p.is_dir() and p.name.isdigit())

def available_years(include_drafts: bool | None = None):
    """Years the API may offer. Drafts only when explicitly allowed."""
    if include_drafts is None:
        include_drafts = _drafts_allowed()
    return [y for y in all_years() if include_drafts or year_status(y) != "draft"]
