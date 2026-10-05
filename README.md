# MeetMind AI

**Turn every meeting into actionable intelligence.**

MeetMind AI is an evidence-based meeting intelligence workspace. It turns meeting conversations into decisions, action items, risks, open questions, and follow-up—while linking factual insights back to transcript timestamps. The included Apollo dataset is clearly labelled demo data so the product can be presented without an external AI key.

## What is implemented

- Premium responsive React + TypeScript workspace with light/dark mode.
- Dashboard with AI Pulse, health score, recent meetings, and workload metrics.
- New meeting flow for media, transcript, and browser recording entry points, with AI processing state.
- Meeting intelligence view with grounded summary, transcript search, evidence markers, decisions, risks, timeline-ready structure, and meeting copilot.
- Action center with filters, priorities, due dates, owners, and status.
- FastAPI endpoints for health, auth, meetings, upload validation, processing, Q&A, and actions.
- Demo mode with realistic Apollo meeting intelligence and hallucination-safe fallback answers.
- Tests for API health, evidence shape, and unknown-question refusal.
- Resumable processing pipeline state for transcription, language detection, cleaning, extraction, intelligence, and indexing stages.
- Real transcript downloads in TXT, SRT, VTT, and JSON formats with authorization checks.

## Run locally

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The UI is at `http://localhost:5173`; API docs are at `http://127.0.0.1:8000/docs`.

## Configuration

`AI_PROVIDER=demo` keeps the application functional without external services. The provider boundary is intentionally environment-driven; a production adapter can be added behind the processing and Q&A endpoints. `DATABASE_URL` defaults to SQLite for a frictionless demo and is ready to be replaced with PostgreSQL. Never expose provider keys to the frontend.

## Demo workflow

1. Open Overview and select **Project Apollo · Sprint Planning**.
2. Review AI Summary, decisions, transcript highlights, and Risk Radar.
3. Open **Ask meeting**, choose a suggested question, and inspect the linked evidence.
4. Open **Action center** to review owners, deadlines, and blocked work.
5. Use **Analyze a meeting → Explore demo** to show the processing experience.

## Tests

```powershell
$env:PYTHONPATH = "backend"
pytest backend/tests
cd frontend
npm run build
```

## Documentation

See [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md), and [docs/academic-project.md](docs/academic-project.md).

## Current delivery boundary

The implemented product path is evidence-grounded meeting capture and intelligence: auth, owner-scoped persistence, demo mode, transcript ingestion, resumable processing state, summaries, decisions, actions, risks, questions, Q&A, comparison, search, notifications, exports, localization catalogs, and privacy controls. External providers remain explicitly configurable; missing credentials return `NOT CONFIGURED`/`503` rather than fabricated success.

The remaining enterprise-scale items from the extended roadmap—production WebRTC signaling/TURN, provider OAuth connectors, background workers, cross-user collaboration, and browser E2E coverage—require deployment infrastructure and credentials and are not represented as fake integrations.

## Known next steps

The UI and API currently use the controlled demo dataset. Production completion would add PostgreSQL persistence/Alembic migrations, a replaceable transcription/LLM adapter, durable JWT refresh/revocation, object storage, real PDF/DOCX exports, and browser-level tests. These are intentionally documented rather than represented by fake buttons.
