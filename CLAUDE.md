# TaxPrep: notes for AI assistants

- Federal 1040 / 1040-NR / 8843 with CA and NY returns. FastAPI backend in `taxprep/backend`, Next.js frontend in `taxprep/frontend`.
- Status, hosting and release blockers: `TAX_YEAR_HANDOFF.md`, `WEBSITE.md`, `taxprep/FIXES.md`. History: `WORK_LOG.md` (add an entry for your work).
- **New tax year or new/revised forms:** follow `.claude/skills/tax-year-update/SKILL.md` and use the kit in `taxprep/backend/tools/taxyear/`. If an official form PDF cannot be downloaded, ask the user to upload it.
- Tests: `cd taxprep/backend && python -m pytest -q`; frontend: `cd taxprep/frontend && npm run build`.
- The site has capped open sign-up (`MAX_USERS`) and holds real taxpayer data (see `docs/SECURITY.md`). Never commit secrets, real taxpayer data, generated returns or `.local-secrets.json`, and never print stored SSNs or return data in logs, tests or chat. Use made-up data in tests.
