# ENESKO Category 3 — Intelligent Channels & Integrations

**Status:** IMPLEMENTATION COMPLETE  
**External activation:** configuration-dependent  
**Release gate:** backend tests + all frontend builds + local voice/browser verification.

Category 3 extends the frozen Category 2 platform. It does not replace the existing case engine, tenant workflows, navigation engine, cinema records, parking records, customer UI, OPS dashboard or audit/RBAC layer.

## The 8 Category 3 phases

### 3.1 — AI tool orchestration
ENESKO uses one shared orchestration layer for web chat, browser voice, WhatsApp and email. The orchestration layer routes customer requests into existing ENESKO capabilities instead of duplicating business logic.

Current tools include:
- store/product discovery;
- verified knowledge retrieval;
- cinema lookup;
- parking lookup;
- indoor navigation;
- Lost & Found intake guidance;
- human handoff guidance;
- tenant operations context.

### 3.2 — Grounded knowledge retrieval
Answers are grounded in ENESKO operational records and verified knowledge documents. Expired knowledge is excluded. Operational truth comes from current database records, authorized staff updates or configured integrations. ENESKO must return an unavailable/unknown state rather than invent live facts.

This release uses verified database retrieval and deterministic tool routing. A future external model or embedding provider can be added behind this layer without changing the operational source-of-truth rules.

### 3.3 — Voice concierge
The Customer Web app includes an ENESKO-branded voice interface:
- large microphone/orb control;
- Ready / Listening / Thinking states;
- browser speech recognition when supported;
- browser speech synthesis for ENESKO responses;
- visible user/assistant transcript cards;
- typed fallback when microphone recognition is unavailable;
- quick voice actions;
- shared ENESKO tool orchestration;
- spoken indoor navigation through the existing route engine;
- VoiceSession transcript and summary persistence.

The web voice screen is intentionally **not a WhatsApp clone**. It is a mall-concierge surface. ENESKO inside WhatsApp naturally uses the WhatsApp interface.

The voice concierge also supports:
- a warm spoken Ikeja City Mall welcome when the customer opens Voice;
- English (Nigeria) speech mode using `en-NG`;
- Yorùbá speech mode using `yo-NG`;
- automatic Yorùbá detection for typed requests;
- Yorùbá operational replies using the same verified ENESKO tools and records;
- rotation across distinct speech-synthesis voices available on the customer's device.

Browser speech APIs expose voice language/name but not a reliable gender attribute, so the local browser implementation does not claim guaranteed male/female Nigerian voices. A production TTS provider can later supply controlled named Nigerian male/female voice profiles without changing the ENESKO conversation engine.

### 3.4 — WhatsApp channel
- Meta WhatsApp Cloud adapter;
- webhook verification;
- webhook signature verification when an app secret is configured;
- inbound text processing through the same ENESKO assistant;
- outbound automatic ENESKO reply;
- outbound staff messages;
- persisted inbound/outbound channel history;
- truthful NOT_CONFIGURED state when Meta credentials are absent.

No API version is hard-coded. Deployment must supply the currently supported Meta Graph API version.

### 3.5 — Email channel
- SMTP outbound adapter;
- authenticated inbound webhook;
- inbound email processing through the same ENESKO assistant;
- outbound automatic ENESKO reply;
- persisted inbound/outbound channel history;
- truthful NOT_CONFIGURED state when SMTP is absent.

### 3.6 — Cinema integration
- configured authorized JSON feed adapter;
- staff/admin-triggered synchronization;
- integration-provenance records;
- verified_at / expires_at freshness metadata;
- current public-reference fallback;
- configured status kept separate from actual fresh live-data availability.

### 3.7 — Parking integration
- configured authorized JSON feed adapter;
- staff/admin-triggered synchronization;
- fresh integration expiry;
- INTEGRATION_VERIFIED provenance;
- existing staff-updated parking fallback retained;
- configured status kept separate from actual fresh live-data availability.

### 3.8 — Integration health & release gate
- /api/v1/category3/status
- /api/v1/assistant/capabilities
- /api/v1/integrations/status
- protected /api/v1/integrations/health
- ENESKO OPS Integrations view
- backend end-to-end Category 3 tests

## External configuration

The following values are optional in local development and required only when activating their provider:

```env
WHATSAPP_GRAPH_URL=https://graph.facebook.com
WHATSAPP_API_VERSION=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=

SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
INBOUND_WEBHOOK_SECRET=

CINEMA_FEED_URL=
CINEMA_FEED_TOKEN=

PARKING_FEED_URL=
PARKING_FEED_TOKEN=
```

Do not commit real secrets to Git.

## Requirements

Category 3 does not add a new Python or npm dependency. It reuses:
- FastAPI;
- SQLAlchemy;
- Pydantic;
- HTTPX;
- existing Next.js/React workspaces;
- browser Web Speech APIs for web voice.

Browser speech recognition support varies by browser. Typed voice-console fallback remains available when recognition is unavailable.

## Local release test

From the repository root:

```powershell
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

There is no new Category 3 database migration because this release reuses the existing Category 1/2 tables and columns.

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

## Browser verification

1. Open Customer Web on http://localhost:3000.
2. Open **Voice concierge**.
3. Test typed fallback first: `Where can I buy sports shoes?`
4. Test: `Take me to Samsung` and verify the response uses the existing Entrance 2 -> Samsung reference route.
5. Test microphone input in a supported browser and allow microphone permission.
6. Confirm ENESKO speaks the response.
7. Open ENESKO OPS on http://localhost:3001 and open **Integrations**.
8. Voice should show ready; unconfigured external providers should honestly show Not configured.
9. Do not expect WhatsApp/email/cinema/parking external providers to be live until authorized credentials/endpoints are supplied.

## Freeze rule

Category 3 implementation is considered complete when pytest and all Next.js builds pass and the local voice/browser flow succeeds.

External provider activation is a deployment/integration task, not a reason to fake provider success. Once activated, each provider must be verified against its real sandbox/production account before ENESKO describes it as live.
