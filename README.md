# ENESKO

ENESKO is an intelligent mall operations platform. Category 1 implements the functional mall-operation domains and APIs (Phases 1–13). Category 2 adds production-oriented platform engineering and the prototype-facing product interfaces.

## Category 2 applications

- Customer Web — Next.js, port 3000
- Admin Operations Dashboard — Next.js, port 3001
- Tenant Portal — Next.js, port 3002
- FastAPI backend — port 8000
- Authentication — JWT + Argon2
- Authorization — ENESKO RBAC roles
- Audit — mutation metadata audit trail
- Database lifecycle — Alembic baseline, SQLite for local demo and PostgreSQL-ready configuration

## Local setup

Use Python 3.13 for this project.

```powershell
git pull origin main
.\venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
cd backend
alembic upgrade head
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

Demo staff login: `admin@enesko.local` / `EneskoDemo2026!`

Demo tenant login: `tenant@enesko.local` / `TenantDemo2026!`

These credentials and the default JWT secret are development-only. Change them before production.

## Verification

Backend release gate: all pytest tests must pass.

Frontend release gate: all three Next.js applications must complete `npm run build`.

Swagger: http://127.0.0.1:8000/docs

Health: http://127.0.0.1:8000/health

## Data policy

Seeded mall, cinema, parking, tenant and integration information is demo data unless explicitly verified. ENESKO must not present demo or unconfigured external integrations as live operational truth.
