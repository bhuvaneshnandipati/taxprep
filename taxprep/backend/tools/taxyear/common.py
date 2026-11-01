"""Shared helpers for the tax-year update kit. Every command writes a log file
to taxprep/backend/logs/ (git-ignored) so a run can be debugged afterwards."""
from __future__ import annotations
import datetime as _dt, json, logging, pathlib, sys
import yaml

BACKEND = pathlib.Path(__file__).resolve().parents[2]
RULES = BACKEND / "rules"
TEMPLATES = BACKEND / "app" / "pdf" / "templates"
PDF_CODE = BACKEND / "app" / "pdf"
MANIFEST = pathlib.Path(__file__).resolve().parent / "forms_manifest.yaml"
LOGS = BACKEND / "logs"
# Rule packs whose values must be traced to an official source in SOURCES.md.
LEDGER_PACKS = ("federal", "california", "newyork", "treaties", "mailing")


def get_logger(name: str) -> logging.Logger:
    LOGS.mkdir(exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log = logging.getLogger(f"taxyear.{name}")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        fh = logging.FileHandler(LOGS / f"taxyear-{name}-{stamp}.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        fh.setLevel(logging.DEBUG)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(message)s"))
        sh.setLevel(logging.INFO)
        log.addHandler(fh); log.addHandler(sh)
        log.debug("log file %s", fh.baseFilename)
    return log


def load_yaml(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_manifest() -> list[dict]:
    return load_yaml(MANIFEST)["forms"]


def flatten(obj, prefix: str = "") -> dict[str, object]:
    """Leaf paths of a rule pack. Lists are leaves (brackets, ranges) so one
    ledger row covers one table; dicts are walked."""
    out: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict) and v:
                out.update(flatten(v, p))
            else:
                out[p] = v
    else:
        out[prefix] = obj
    return out


def show(v) -> str:
    """Compact, stable text form of a leaf value for the ledger."""
    return json.dumps(v, separators=(",", ":"), ensure_ascii=False)


def pack_leaves(year: int, pack: str) -> dict[str, object]:
    data = load_yaml(RULES / str(year) / f"{pack}.yaml") or {}
    data.pop("year", None)
    return flatten(data)


def previous_year(year: int) -> int | None:
    years = sorted(int(p.name) for p in RULES.iterdir() if p.is_dir() and p.name.isdigit() and int(p.name) < year)
    return years[-1] if years else None
