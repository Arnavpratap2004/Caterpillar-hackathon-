# Smart Operator Companion

10-hour hackathon prototype for the loop: **TRAIN → WORK → OBSERVE → REFLECT → COMPARE → ADAPT**.

Performance now uses three explainable reference points: **fixed task benchmark + personal operator baseline + context-aware adjustment**. Scheduled task playback estimates are reported in minutes; completed-session operating evidence is normalized to hours so the demo benchmark and baseline remain comparable. Every completed session returns benchmark status, personal deviation, context factors, contributing factors, and an objective score before reflection calibration is calculated.

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

Open http://localhost:3000. The backend seeds SQLite automatically at `backend/smart_operator.db`; no API key is required. For a clean demo reset, run `PYTHONPATH=backend python backend/app/seed/seed_database.py --reset` (or the installed Windows Python command). Set `LLM_API_KEY` or `OPENROUTER_API_KEY` to connect an OpenAI-compatible/Jev-compatible provider (offline fallback remains enabled). Copy `.env.example` to configure local values.

The demo user is **Raghav Sharma / OP-001**. The seeded contract task is **T002-today** (CAT 320, rainy trench, deterministic seed `170923`). Use My Tasks → Start Work, confirm the seatbelt, play the synthetic telemetry, finish Work, and submit the Reflect debrief. The seeded path returns objective performance 58, confidence 87, calibration gap 29, and `BLIND_SPOT`, routing to Proximity Hazard Response. The original legacy routes remain available.

## Useful checks

```bash
PYTHONPATH=backend python -m pytest backend/tests
cd frontend && npm run lint && npx tsc --noEmit && npm run build
```

On Windows when the `python` app alias is disabled, use the installed interpreter directly:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m uvicorn app.main:app --reload --port 8000
```

The API is intentionally small and SQLite-backed, with `/ws/work/{session_id}` streaming synthetic correlated telemetry. Evaluation APIs include both legacy routes and the combined-plan contracts: `/api/tasks`, `/api/jobs/{id}/start`, `/api/jobs/{id}/review`, `/api/incidents`, `/api/sim-attempts`, `/api/anomalies`, `/api/benchmarks`, `/api/performance/{operator_id}/comparison`, `/api/calibration/{operator_id}`, and `/api/recommendations/{operator_id}`. Training runs persist control events; live telemetry persists context fields and de-duplicated safety incidents. It is clearly marked demonstration mode and does not claim a live CAT connection.
