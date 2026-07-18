"""Document OCR service.

Pluggable extractor interface: TesseractExtractor runs locally; DocumentAI /
Textract adapters can be swapped in via OCR_PROVIDER env for production.

Pipeline: bytes (pdf/jpg/png) -> page images -> OCR text -> document-type
field parser -> {field: {value, confidence, raw}} for user review/edit.
"""
from __future__ import annotations
import io, os, re, subprocess, tempfile

# ---------- extraction backends ----------

class BaseExtractor:
    def extract_text(self, image_bytes: bytes) -> str:
        raise NotImplementedError


class TesseractExtractor(BaseExtractor):
    def extract_text(self, image_bytes: bytes) -> str:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        # upscale small images for better OCR
        if img.width < 1400:
            ratio = 1400 / img.width
            img = img.resize((1400, int(img.height * ratio)))
        return pytesseract.image_to_string(img, config="--psm 6")


def get_extractor() -> BaseExtractor:
    provider = os.getenv("OCR_PROVIDER", "tesseract")
    # Production adapters (documentai / textract) plug in here.
    return TesseractExtractor()


# ---------- file handling ----------

def to_page_images(data: bytes, filename: str) -> list[bytes]:
    """Normalize any supported upload (pdf/jpg/png/heic*) to PNG page images."""
    name = filename.lower()
    if name.endswith(".pdf"):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "in.pdf")
            open(src, "wb").write(data)
            subprocess.run(["pdftoppm", "-png", "-r", "200", src, os.path.join(td, "pg")],
                           check=True, capture_output=True)
            pages = sorted(f for f in os.listdir(td) if f.startswith("pg"))
            return [open(os.path.join(td, p), "rb").read() for p in pages]
    return [data]  # jpg/png pass through; PIL opens both


# ---------- field parsing ----------

MONEY = re.compile(r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+\.\d{2})")
EIN = re.compile(r"\b(\d{2}\s?-\s?\d{7})\b")
SSN = re.compile(r"\b(\d{3}-\d{2}-\d{4})\b")

W2_FIELDS = {
    # field -> keyword variants searched per line (case-insensitive)
    "wages":              ["wages, tips, other", "wages tips other", "box 1"],
    "fed_withholding":    ["federal income tax withheld", "federal tax withheld"],
    "ss_wages":           ["social security wages"],
    "ss_tax":             ["social security tax withheld"],
    "medicare_wages":     ["medicare wages"],
    "medicare_tax":       ["medicare tax withheld"],
    "state_withholding":  ["state income tax", "state tax"],
    "retirement_401k":    ["401k", "401(k)", "12a"],
}

F1099_FIELDS = {
    "1099-INT": {"interest": ["interest income", "box 1"]},
    "1099-NEC": {"nonemployee_comp": ["nonemployee compensation", "box 1"]},
    "1099-DIV": {"dividends": ["total ordinary dividends", "ordinary dividends", "box 1a"]},
}


def _monies(line: str) -> list[tuple[int, float]]:
    """All money-like tokens on a line as (char_offset, value). Skips ID-like long digit runs."""
    out = []
    for m in MONEY.finditer(line):
        tok = m.group(1)
        digits = tok.replace(",", "").replace(".", "")
        if "," not in tok and "." not in tok and len(digits) >= 7:
            continue  # looks like an EIN/SSN/account number, not an amount
        if "," not in tok and "." not in tok and len(digits) <= 2:
            continue  # bare 1-2 digit token is a box number, not an amount
        out.append((m.start(), float(tok.replace(",", ""))))
    return out


def _find(lines: list[str], keywords: list[str]) -> tuple[float | None, str, float]:
    """Position-aware lookup: forms lay boxes in columns, so the amount for a
    label sits at roughly the same character offset on the same or next line.
    """
    for i, line in enumerate(lines):
        low = line.lower()
        for kw in keywords:
            pos = low.find(kw)
            if pos < 0:
                continue
            after = _monies(line[pos + len(kw):])
            if after:
                return after[0][1], line.strip(), 0.9
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                cands = _monies(nxt)
                if cands:
                    # relative-position matching: OCR collapses whitespace, so
                    # compare position ratios within each line rather than offsets
                    kw_ratio = (pos + len(kw) / 2) / max(len(line), 1)
                    best = min(cands, key=lambda c: abs(c[0] / max(len(nxt), 1) - kw_ratio))
                    dist = abs(best[0] / max(len(nxt), 1) - kw_ratio)
                    conf = 0.85 if dist <= 0.12 else 0.55
                    return best[1], nxt.strip(), conf
    return None, "", 0.0


def detect_doc_type(text: str) -> str:
    t = text.lower()
    if "1099-int" in t or ("interest income" in t and "payer" in t):
        return "1099-INT"
    if "1099-nec" in t or "nonemployee compensation" in t:
        return "1099-NEC"
    if "1099-div" in t or "ordinary dividends" in t:
        return "1099-DIV"
    if "w-2" in t or "wage and tax statement" in t:
        return "W-2"
    return "unknown"


def parse_document(text: str, doc_type: str | None = None) -> dict:
    lines = [l for l in text.splitlines() if l.strip()]
    dtype = doc_type or detect_doc_type(text)
    fields: dict = {}

    ein = EIN.search(text)
    if ein:
        fields["ein"] = {"value": ein.group(1).replace(" ", ""), "confidence": 0.95, "raw": ein.group(0)}

    spec = W2_FIELDS if dtype == "W-2" else F1099_FIELDS.get(dtype, {})
    for field, kws in spec.items():
        v, raw, conf = _find(lines, kws)
        if v is not None:
            fields[field] = {"value": v, "confidence": conf, "raw": raw}

    # employer name heuristic: first non-numeric line near EIN line
    if dtype == "W-2" and ein:
        for l in lines[:12]:
            if len(l.strip()) > 3 and not MONEY.search(l) and not EIN.search(l) \
               and not SSN.search(l) and not any(k in l.lower() for k in ("wage", "form", "omb", "copy")):
                fields["employer"] = {"value": l.strip()[:60], "confidence": 0.5, "raw": l.strip()}
                break

    low_conf = [k for k, f in fields.items() if f["confidence"] < 0.8]
    return {"doc_type": dtype, "fields": fields, "needs_review": bool(low_conf) or dtype == "unknown",
            "low_confidence_fields": low_conf}


def process_upload(data: bytes, filename: str) -> dict:
    extractor = get_extractor()
    text = "\n".join(extractor.extract_text(p) for p in to_page_images(data, filename))
    out = parse_document(text)
    out["ocr_chars"] = len(text)
    return out
