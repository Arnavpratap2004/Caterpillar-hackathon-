# Smart Operator Companion

10-hour hackathon prototype for the loop: **TRAIN → WORK → OBSERVE → REFLECT → COMPARE → ADAPT**.

Performance now uses three explainable reference points: **fixed task benchmark + personal operator baseline + context-aware adjustment**. Every completed session returns benchmark status, personal deviation, context factors, contributing factors, and an objective score before reflection calibration is calculated.

## Run locally

Terminal 1:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The backend seeds SQLite automatically at `backend/smart_operator.db`; no API key is required. Set `LLM_API_KEY` to connect an OpenAI-compatible provider (offline fallback remains enabled).

The demo user is **Raghav Sharma / OP-001**. Start with Training Hub or Home → Start Simulation, then start the Excavation task, finish Work, and submit the Reflect text. The seeded path returns objective performance 58, confidence 87, calibration gap 29, and `BLIND_SPOT`, routing to Proximity Hazard Response.

## Useful checks

```bash
PYTHONPATH=backend python -m pytest backend/tests
cd frontend && npm run build
```

The API is intentionally small and SQLite-backed, with `/ws/work/{session_id}` streaming synthetic correlated telemetry. New evaluation APIs include `/benchmarks`, `/performance/evaluate/{session_id}`, `/performance/{operator_id}/benchmark-comparison`, and `/performance/{operator_id}/personal-baseline`. It is clearly marked demonstration mode and does not claim a live CAT connection.
