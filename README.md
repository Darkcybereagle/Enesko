# ENESKO

ENESKO is an intelligent mall operations platform. Category 1 implements the mall-operation domains and APIs (Phases 1–13). Category 2 adds production-oriented platform engineering and the customer, staff and tenant product interfaces.

## Category 2 applications

- Customer Web — Next.js, port 3000
- Admin Operations Dashboard — Next.js, port 3001
- Tenant Portal — Next.js, port 3002
- FastAPI backend — port 8000
- Authentication — JWT + Argon2
- Authorization — ENESKO RBAC roles
- Audit — mutation metadata audit trail
- Database lifecycle — Alembic migrations, SQLite for local development and PostgreSQL-ready configuration

## Local setup

Use Python 3.13 for this project.

```powershell
git pull origin main
.\venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd backend
python -m alembic upgrade head
python -m app.seed
pytest -q
```

Then run the backend:

```powershell
python -m uvicorn app.main:app --reload
```

In another PowerShell at the repository root:

```powershell
npm install
npm run build
```

Development interfaces can then be started individually:

```powershell
npm run dev:customer
npm run dev:admin
npm run dev:tenant
```

Local staff login: `admin@enesko.local` / `EneskoLocal2026!`

Local tenant login: `tenant@enesko.local` / `TenantLocal2026!`

These accounts exist only for local development and automated testing. The tenant account is attached to an ENESKO reference workspace, not to an asserted real ICM tenant relationship. Production identities must come from authorized mall onboarding and must use production secrets.

## Verification

Backend release gate: all pytest tests must pass.

Frontend release gate: all three Next.js applications must complete `npm run build`.

Swagger: http://127.0.0.1:8000/docs

Health: http://127.0.0.1:8000/health

## Data policy

ENESKO must distinguish public-reference information, staff-verified operational data, authorized integration data, reference models and test fixtures.

- Public directory facts may be seeded only when their source and verification metadata are retained.
- Live operational claims must come from fresh staff updates or authorized integrations.
- Reference workspaces and route models must never be presented as authorized live mall data.
- Test fixtures are isolated to `APP_ENV=test`.
- Unavailable live data must be described as unavailable rather than guessed.
