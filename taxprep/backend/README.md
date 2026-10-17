# TaxPrep Backend

FastAPI tax-preparation API for **international students and visa holders**, TY2025:
residency (Green Card / Substantial Presence / exempt-individual / dual-status), Form 1040-NR with
tax treaties and Schedule NEC, Form 8843, Form 1040, California 540 / 540NR, New York IT-201 / IT-203.
Output is the **official agency PDFs, filled in** (templates in `app/pdf/templates/2025/`).

## Layout
- `rules/<year>/*.yaml` — every rate, threshold and treaty benefit (federal, california, newyork,
  treaties, questions, mailing). Add a year = add a folder (and its form templates).
- `app/engines/` — residency, federal (resident / nonresident / dual-status), treaty, CA, NY, interview.
- `app/pdf/` — `fill.py` (AcroForm fill + flatten), `official.py` (field maps), `forms.py` (package).
- `app/api/` — auth, returns (save / resume / calculate / package), documents (OCR), admin.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
```
Environment:
| var | purpose |
|-----|---------|
| `DATABASE_URL` | SQLite by default; Postgres in production |
| `JWT_SECRET` | **required** in production (the app refuses to start on Render with the default) |
| `DATA_KEY` | Fernet key — encrypts SSN/ITIN and passport numbers at rest. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ADMIN_EMAILS` + `ADMIN_SETUP_CODE` | an admin email can only be registered with the setup code |
| `CORS_ORIGINS`, `DB_SSLMODE`, `ACCESS_TOKEN_MINUTES` (default 240) | |

## Test
```bash
pip install -r requirements-dev.txt
pytest -q          # 78 tests: hand-computed engine values, API journey, official-form read-back
```

## API flow
1. `POST /auth/register` → token
2. `POST /returns` → id;  `GET /returns/{id}` resumes everything
3. `PUT /returns/{id}/taxpayer` (name, SSN, address…)
4. `PUT /returns/{id}/profile` → residency determination + next interview questions
5. `PUT /returns/{id}/answers` → adaptive questions
6. `PUT /returns/{id}/income` → W-2s, 1042-S, 1099 amounts, deductions, state
7. `POST /returns/{id}/calculate` → lines, explanations, warnings, checklist, mailing addresses
8. `GET /returns/{id}/package.pdf` → filled official forms + cover sheet

See `../FIXES.md` for the audit report and known limits.
