"""OCR pipeline tests using a synthetic W-2 rendered with PIL."""
import io, os
from PIL import Image, ImageDraw, ImageFont

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
from app.ocr.service import parse_document, process_upload, detect_doc_type


def make_w2_png() -> bytes:
    img = Image.new("L", (1600, 1000), 255)
    d = ImageDraw.Draw(img)

    def box(x, y, w, h, label, value):
        d.rectangle([x, y, x + w, y + h], outline=0, width=2)
        d.text((x + 8, y + 6), label, fill=0, font=FONT)
        d.text((x + 8, y + 44), value, fill=0, font=FONT_B)

    d.text((40, 15), "Form W-2 Wage and Tax Statement 2025", fill=0, font=FONT_B)
    box(40, 60, 500, 90, "b Employer identification number (EIN)", "94-1234567")
    box(40, 160, 500, 120, "c Employer's name, address, and ZIP code",
        "PLATINUM FINISHING SYSTEMS")
    box(560, 60, 480, 90, "1 Wages, tips, other compensation", "48,250.00")
    box(1060, 60, 480, 90, "2 Federal income tax withheld", "4,610.00")
    box(560, 160, 480, 90, "3 Social security wages", "48,250.00")
    box(1060, 160, 480, 90, "4 Social security tax withheld", "2,991.50")
    box(560, 260, 480, 90, "5 Medicare wages and tips", "48,250.00")
    box(1060, 260, 480, 90, "6 Medicare tax withheld", "699.63")
    box(560, 360, 480, 90, "17 State income tax", "1,520.00")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_parse_w2_text_direct():
    text = """Form W-2 Wage and Tax Statement
Employer identification number 94-1234567
PLATINUM FINISHING SYSTEMS
1 Wages, tips, other compensation 48,250.00
2 Federal income tax withheld 4,610.00
3 Social security wages 48,250.00
17 State income tax 1,520.00"""
    out = parse_document(text)
    assert out["doc_type"] == "W-2"
    f = out["fields"]
    assert f["ein"]["value"] == "94-1234567"
    assert f["wages"]["value"] == 48250.00
    assert f["fed_withholding"]["value"] == 4610.00
    assert f["state_withholding"]["value"] == 1520.00
    assert f["employer"]["value"].startswith("PLATINUM")


def test_ocr_synthetic_w2_image():
    out = process_upload(make_w2_png(), "w2.png")
    f = out["fields"]
    assert out["doc_type"] == "W-2"
    assert f.get("wages", {}).get("value") == 48250.00
    assert f.get("fed_withholding", {}).get("value") == 4610.00
    assert f.get("ein", {}).get("value") == "94-1234567"


def test_detect_1099():
    assert detect_doc_type("Form 1099-INT Interest Income Payer XYZ Bank") == "1099-INT"
    assert detect_doc_type("1099-NEC Nonemployee compensation 12,000") == "1099-NEC"


def test_parse_1099_int():
    out = parse_document("Form 1099-INT\nPayer: Chase Bank\n1 Interest income 312.45")
    assert out["doc_type"] == "1099-INT"
    assert out["fields"]["interest"]["value"] == 312.45


def test_upload_review_apply_api():
    os.environ["DATABASE_URL"] = "sqlite:///./test_ocr_api.db"
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    tok = {"Authorization": "Bearer " + c.post("/auth/register",
           json={"email": "ocr@test.com", "password": "password123"}).json()["access_token"]}
    rid = c.post("/returns", headers=tok).json()["id"]

    # reject bad type
    r = c.post(f"/returns/{rid}/documents", headers=tok,
               files={"file": ("evil.exe", b"xx", "application/octet-stream")})
    assert r.status_code == 400

    # upload synthetic W-2
    r = c.post(f"/returns/{rid}/documents", headers=tok,
               files={"file": ("w2.png", make_w2_png(), "image/png")})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["doc_type"] == "W-2"
    assert doc["extracted"]["fields"]["wages"]["value"] == 48250.00

    # user corrects employer name, then applies
    r = c.put(f"/returns/{rid}/documents/{doc['id']}", headers=tok,
              json={"employer": "Platinum Finishing Systems"})
    assert r.status_code == 200
    r = c.post(f"/returns/{rid}/documents/{doc['id']}/apply", headers=tok)
    inc = r.json()["income"]
    assert inc["w2s"][0]["wages"] == 48250.00
    assert inc["w2s"][0]["employer"] == "Platinum Finishing Systems"

    # document listed with applied status
    docs = c.get(f"/returns/{rid}/documents", headers=tok).json()
    assert docs[0]["status"] == "applied"
