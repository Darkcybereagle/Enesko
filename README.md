# ENESKO

ENESKO is an intelligent mall operations platform.

- **Category 1:** core mall-operation domains and APIs (Phases 1–13).
- **Category 2:** secured customer, staff and tenant product interfaces. **Complete & frozen.**
- **Category 3:** intelligent channels and external integration layer. **Implementation complete; external activation is configuration-dependent.**

## Applications

- Customer Web — Next.js, port 3000
- Admin Operations Dashboard — Next.js, port 3001
- Tenant Portal — Next.js, port 3002
- FastAPI backend — port 8000

## Category 3

Category 3 has **8 phases**:

1. AI tool orchestration
2. Grounded knowledge retrieval
3. Voice concierge
4. WhatsApp channel
5. Email channel
6. Cinema integration
7. Parking integration
8. Integration health and release gate

The Customer Web voice interface is ENESKO-branded, not a WhatsApp clone. WhatsApp remains a separate external channel using the native WhatsApp interface.

External providers never report fake success. When credentials/endpoints are absent, ENESKO returns an explicit `NOT_CONFIGURED` state and retains safe local fallbacks.

See `docs/CATEGORY_3.md` for the complete phase map, environment variables and release verification.

## Local setup

Use Python 3.13 for this project.

```powershell
cd C:\Users\hp\Desktop\Enesko
git pull origin main

.\venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt

cd backend
python -m alembic upgrade head
python -m app.seed
pytest -q

cd ..
npm install
npm run build
```

Category 3 adds no new Python or npm dependency beyond packages already present in the project requirements/workspaces.

## Runtime

Backend:

```powershell
cd C:\Users\hp\Desktop\Enesko\backend
..\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Customer Web:

```powershell
cd C:\Users\hp\Desktop\Enesko
npm run dev:customer
```

ENESKO OPS:

```powershell
cd C:\Users\hp\Desktop\Enesko
npm run dev:admin
```

Tenant Portal:

```powershell
cd C:\Users\hp\Desktop\Enesko
npm run dev:tenant
```

Local staff login: `admin@enesko.local` / `EneskoLocal2026!`

Local tenant login: `tenant@enesko.local` / `TenantLocal2026!`

Local accounts exist only for development/testing. Production identities and integration secrets must come from authorized deployment configuration.

## Verification

Backend release gate:

```powershell
cd C:\Users\hp\Desktop\Enesko\backend
pytest -q
```

Frontend release gate:

```powershell
cd C:\Users\hp\Desktop\Enesko
npm run build
```

Swagger: http://127.0.0.1:8000/docs

Health: http://127.0.0.1:8000/health

Category 3 status: http://127.0.0.1:8000/api/v1/category3/status

Integration status: http://127.0.0.1:8000/api/v1/integrations/status

## Data policy

ENESKO distinguishes public-reference information, staff-verified operational data, authorized integration data, reference models and test fixtures.

- Public directory facts retain source and verification metadata.
- Live operational claims come only from fresh staff updates or authorized integrations.
- Reference workspaces and route models are not presented as authorized live mall data.
- Test fixtures are isolated to `APP_ENV=test`.
- Unavailable live data is described as unavailable instead of guessed.
- External integrations are not described as live merely because an adapter is configured.
