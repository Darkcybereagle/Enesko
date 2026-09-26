# ENESKO

Enesko is a modular intelligent mall operations platform. This repository currently implements **Phase 1 (Mall Core)** and **Phase 2 (Knowledge + Conversational Core)**.

## What works now

- Mall, floor, zone, category, store and facility data
- Store/category search
- Verified knowledge documents with freshness/expiry
- Conversational assistant endpoint
- Store-finder tool
- Safe refusal when no verified source exists
- Human-handoff flag
- Conversation logging
- Simple browser test page
- Swagger API docs
- Automated tests
- PostgreSQL-ready configuration (SQLite default for easiest first test)

## Requirements

- Python 3.11+ recommended
- pip
- PostgreSQL is optional for this first local test

## Install on Windows PowerShell

```powershell
git clone https://github.com/Darkcybereagle/Enesko.git
cd Enesko
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
cd backend
python -m app.seed
uvicorn app.main:app --reload
```

Open:

- Test page: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Very simple test

On the test page type:

```text
Where can I buy sports shoes?
```

Expected: Enesko returns the seeded demo sports store.

Then type:

```text
How many parking spaces are free right now?
```

Expected: Enesko refuses to invent live availability and requests a verified source/human handoff.

## Automated tests

From `backend`:

```powershell
pytest -q
```

## PostgreSQL

Edit `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/enesko
```

Create the `enesko` database first, then run:

```powershell
python -m app.seed
uvicorn app.main:app --reload
```

## Data safety

Seeded mall/store information is **DEMO DATA**. Production ICM deployment must replace it with authorized, verified mall data and integrations.
