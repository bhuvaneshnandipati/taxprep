"""Loads TY-versioned rule packs. Tax law lives in YAML, never in code."""
import functools, pathlib, yaml

RULES_DIR = pathlib.Path(__file__).resolve().parents[2] / "rules"
DEFAULT_YEAR = 2025

@functools.lru_cache(maxsize=None)
def load_rules(pack: str, year: int = DEFAULT_YEAR) -> dict:
    path = RULES_DIR / str(year) / f"{pack}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No rule pack '{pack}' for tax year {year}")
    with open(path) as f:
        return yaml.safe_load(f)

def available_years():
    return sorted(int(p.name) for p in RULES_DIR.iterdir() if p.is_dir() and p.name.isdigit())
