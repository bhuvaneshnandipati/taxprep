# TaxPrep Backend — Phase 1

FastAPI tax preparation API. Federal (1040 / 1040-NR) + California (540 / 540NR), TY2025.

## Architecture
- **Rules engine**: all tax law lives in `rules/<year>/*.yaml` (federal, california, treaties, questions). Code never hardcodes rates. Add a year = add a folder.
- **Engines** (`app/engines/`): residency (Green Card Test, SPT, exempt-individual), federal calc (ordinary + LTCG stacking, CTC/ACTC, AOTC/LLC, EITC, SE tax, Additional Medicare, NIIT), California calc (540/540NR, mental-health tax, exemption/renter credits), treaty engine (India, China, Korea, Canada, Germany, Philippines), adaptive interview graph.
- **API** (`app/api/`): JWT auth (bcrypt), returns CRUD with save/resume, interview endpoints, calculate endpoint returning form lines + plain-language explanations + filing checklist.
- **DB**: SQLAlchemy models (User, TaxReturn, AuditLog). SQLite for dev, PostgreSQL via `DATABASE_URL`.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://localhost:8000/docs
# or
docker compose up                     # API + PostgreSQL
```

## Test
```bash
pytest tests/ -v      # 25 tests: engine expected-value checks + full API journey
```

## API flow
1. `POST /auth/register` → token
2. `POST /returns` → return id
3. `PUT /returns/{id}/profile` → residency determination
4. `PUT /returns/{id}/answers` → adaptive next questions + progress
5. `PUT /returns/{id}/income` → W-2s, 1099 amounts, deductions
6. `POST /returns/{id}/calculate` → form lines, explanations, treaty applied, checklist

## Roadmap
Phase 2: PDF generation (1040, 1040-NR, 8843, 540) · Phase 3: Next.js frontend · Phase 4: OCR uploads · Phase 5: more states + full treaty table + admin panel · Phase 6: CI/CD, K8s
