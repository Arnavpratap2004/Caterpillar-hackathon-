# CAT Smart Operator Assistant

**Smart Operator Companion** is a local-first FastAPI + Next.js prototype for the operator loop:

> **TRAIN → WORK → OBSERVE → REFLECT → COMPARE → ADAPT**

It combines scheduled-task estimation, synthetic machine telemetry, deterministic safety rules, objective performance evaluation, operator reflection, confidence calibration, and targeted simulation practice. It is a demonstration product: it does **not** connect to a CAT machine, CAN bus, production identity provider, or production fleet.

## Audit status

This README describes the code currently in this repository, not an aspirational product plan. The source was audited across `backend/`, `frontend/`, the generated CSV data, the SQLite seed path, tests, and the external build-plan document at `C:\Users\Arnav\Downloads\COMBINED.md`.

| Symbol | Meaning |
| --- | --- |
| ✅ | Implemented in the current source and exercised by the app/tests |
| 🟡 | Implemented as a prototype, simplified, or browser-dependent |
| 🧪 | Synthetic, seeded, or demo-only behavior |
| 📌 | Planned/specification item that is not implemented here |

## What is implemented

| Area | Status | Verified behavior |
| --- | --- | --- |
| Home dashboard and task list | ✅ | Backend-driven operator summary, tasks, machine state, conditions, recommendations, and progress |
| Task-time prediction | ✅ | Deterministic minutes prediction from baseline duration, weather, skill, and machine age; completed-session evaluation is normalized to hours |
| Work telemetry | 🧪✅ | A seeded WebSocket stream sends correlated temperature, load, fuel, phase, belt, proximity, tilt, weather, ground, GPS, and anomaly fields |
| Safety | ✅🧪 | Seatbelt, proximity, tilt, visibility/rain, onset/escalation/resolution, incident persistence, condition-adjusted margins, and closing-speed warnings |
| Live operator guidance | ✅ | Deterministic guidance is attached to telemetry; no LLM call is required for safety decisions |
| Reflection | ✅🟡 | Editable text and browser SpeechRecognition input; optional OpenAI-compatible/OpenRouter analysis with a deterministic offline fallback |
| Compare/calibration | ✅ | Objective evaluation happens before reflection analysis; calibration states and `OVERCONFIDENCE_RISK` are returned and displayed |
| Adaptive recommendation | ✅ | Backend routes the weakest evidence/calibration state to a training scenario |
| Training hub | ✅🟡 | Scenario library, guided tour, primitive 3D scene, timer, controls, score, penalties, saved attempts, and baseline updates for passing attempts |
| Anomaly detection | ✅🧪 | Deterministic rules for idling, unbelted operation, fuel per cycle, long/unusual sessions, and seeded unusual patterns |
| Reports | ✅🧪 | Seeded operational summary, benchmark comparison, safety/training/machine reports, and CSV export |
| Voice safety notes | 🟡 | Work-page browser speech input appends notes and keyword matches can log an incident; support depends on browser permissions/API |
| Authentication | 🟡🧪 | Demo login and operator cookie normalization only; no real authentication or authorization system |
| CAT integration | 📌 | No live CAT hardware, CAN, telematics, or fleet service integration is present |
| Trained ML models | 📌 | No GradientBoosting, IsolationForest, joblib model, or separate ML service is present in the current repository |

## The end-to-end demo

The deterministic seeded operator is **Raghav Sharma (`OP-001`)**. The public demo task is **`T002-today`**:

- CAT 320 Excavator
- rainy trench task
- intermediate operator skill
- 45-minute task option
- seed `170923`
- stored internally as legacy database task `T-002`

The public API exposes `T002-today` while retaining `T-002` compatibility. After a clean seed, the demo evaluation is designed to show:

- objective score: **58**
- self-confidence from the seeded reflection/fallback path: **87**
- calibration gap: **29 points**
- state: **`BLIND_SPOT`**
- signal: **`OVERCONFIDENCE_RISK`**
- recommended scenario: **Proximity Hazard Response**
- current context-adjusted benchmark: approximately **7.1–9.5 hours**
- personal baseline: **7.2 hours**
- demo current evidence: **10.1 hours**

### Presenter path

1. Start the backend and frontend and open `http://localhost:3000`.
2. Open **My Tasks** and select the first `T002-today` task.
3. Use **Work**, confirm the safety checkbox, and start the job.
4. Watch the synthetic telemetry. Rain/wet conditions activate a 10 m proximity margin; the seeded feed produces working-condition guidance, an approaching warning, and then a proximity warning.
5. Log the incident manually or use a voice note containing words such as `stop`, `hazard`, `person`, `worker`, or `proximity`.
6. End the task. The backend writes objective performance and the frontend moves to **Reflect**.
7. Type or speak a debrief such as: `I think the task went smoothly. I felt confident and reacted quickly when the nearby worker appeared.`
8. Submit the reflection. The UI shows objective performance, self-perception, calibration state, Jev-style language signals, and the recommended next scenario.
9. Select **Train Again**, complete the guided simulation, and return to **Training Hub** to see the saved attempt.
10. Open **Reports** or download `/reports/export.csv`.

The legacy `/work/sessions` + `/reflections` path and the combined-plan `/api/jobs/*` path both remain available.

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ Next.js 14 / React 18 browser UI                            │
│ frontend/app/page.tsx · frontend/lib/api.ts · React state    │
│ Home · My Tasks · Work · Reflect · Training · Machines        │
│ Reports · Settings                                           │
└───────────────┬───────────────────────────────┬──────────────┘
                │ REST JSON                     │ WebSocket JSON
                ▼                               ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI application: backend/app/main.py                    │
│ routes, Pydantic request models, compatibility aliases,     │
│ seed/migration, deterministic prediction/evaluation/safety  │
└───────────────┬───────────────────────────────┬──────────────┘
                │ raw sqlite3                    │ optional reflection LLM
                ▼                               ▼
┌──────────────────────────────┐       ┌──────────────────────┐
│ backend/smart_operator.db    │       │ OpenAI-compatible    │
│ SQLite; seeded demo history  │       │ or OpenRouter API    │
└──────────────────────────────┘       └──────────────────────┘
```

Important implementation details:

- The runtime database access is raw `sqlite3`; SQLAlchemy is listed as an optional dependency but is not the active ORM.
- `main.py` contains the runtime composition, schema, seed, compatibility routes, and most deterministic engines. `backend/app/services/` also contains reusable evaluation, safety, scoring, prediction, and LLM helpers; the current runtime keeps some compatibility logic in `main.py`.
- The browser reads important dashboard, evaluation, environment, report, and training-attempt values from the API. It has safe empty-state values when the backend is unavailable, but it does not pretend those values are live.
- Reflection interpretation is a separate branch. The LLM/fallback receives the operator's words; objective telemetry evaluation remains deterministic and is persisted before reflection calibration.
- The catch-all route `frontend/app/[...slug]/page.tsx` re-exports the single dashboard page. Navigation is client-side view state rather than separate page implementations.

## Repository map

```text
.
├── .env.example                         Backend/LLM/API environment template
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py                      FastAPI app, schema, seed, routes, engines
│   │   ├── services/
│   │   │   ├── evaluation.py             Context/deviation/calibration helpers
│   │   │   ├── llm.py                    Optional provider + offline fallback
│   │   │   ├── prediction.py              Pure simple prediction helper
│   │   │   ├── safety.py                  Pure deterministic hazard rules
│   │   │   └── scoring.py                 Pure scoring helpers
│   │   └── seed/
│   │       ├── generate_dataset.py        Reproducible CSV generator, seed 42
│   │       └── seed_database.py            Reset/initialize SQLite demo data
│   ├── data/                              CSV exports and reference data
│   ├── tests/
│   │   ├── test_api_contract.py            API/golden-path/fallback tests
│   │   └── test_engines.py                 Evaluation/safety/calibration tests
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                       All dashboard views and simulator UI
│   │   ├── [...slug]/page.tsx              Legacy/catch-all view entry
│   │   ├── globals.css                     CAT-style responsive UI
│   │   └── layout.tsx
│   ├── lib/api.ts                          Typed fetch helpers
│   ├── lib/types.ts                        Frontend API/domain types
│   ├── package.json
│   └── package-lock.json
└── backend/smart_operator.db              Local generated file; ignored by Git
```

There are no `apps/`, `packages/`, `docs/demo.md`, model files, image files, screenshots, GLTF files, or separate ML service in this repository.

## Technology stack

### Backend

- Python 3.13 was used for verification
- FastAPI `0.115.6`
- Uvicorn `0.34.0`
- Pydantic `2.10.4`
- SQLite through the Python standard-library `sqlite3` module
- Pytest for backend tests
- Optional SQLAlchemy dependency, currently unused by the runtime

### Frontend

- Next.js `14.2.21`
- React `18.3.1`
- TypeScript `5.7.x`
- Three.js `0.171.0` and `@react-three/fiber` `8.17.x` for the primitive training scene
- Lucide React icons
- Recharts is installed as a dependency, but the current visible report charts are CSS bars rather than Recharts components
- Tailwind/PostCSS packages are present, while the primary UI styling is in `frontend/app/globals.css`
- npm with the checked-in `frontend/package-lock.json`

## Local setup

### Prerequisites

- Node.js and npm
- Python 3.13 on Windows, or a compatible Python 3.11+ environment
- Ports `3000` and `8000` available

On this Windows machine, invoking `python` resolves to the Microsoft Store alias. Use the installed interpreter explicitly:

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
```

### Backend (PowerShell)

From the repository root:

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
& $py -m pip install -r backend\requirements.txt
cd backend
& $py -m uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`; Swagger is at `http://localhost:8000/docs`.

### Frontend

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`.

For a clean install, `npm ci --ignore-scripts` also works in this repository. The frontend build generates `.next/types`; run `npm run build` before a standalone `npx tsc --noEmit` on a fresh checkout because `frontend/tsconfig.json` includes those generated types.

### Environment variables

Root `.env.example`:

```dotenv
DATABASE_URL=sqlite:///./backend/smart_operator.db
LLM_API_KEY=
OPENROUTER_API_KEY=
LLM_MODEL=
LLM_BASE_URL=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`frontend/.env.example` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`.

- The frontend should receive `NEXT_PUBLIC_API_URL` through `frontend/.env.local` or the shell.
- The backend reads `LLM_API_KEY`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `ML_FORCE_DOWN`, and `APP_URL` from the process environment.
- The current backend uses the fixed path `backend/smart_operator.db`; `DATABASE_URL` is a configuration template, not an active database switch.
- The Python code does not load dotenv files itself. Set variables in the shell or use Uvicorn's environment-file support if desired.
- No API key is required for the offline fallback.

### Reset the deterministic database

Stop the backend first, then run:

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
cd backend
& $py app\seed\seed_database.py --reset
```

The database is ignored by Git and is recreated automatically when the FastAPI module starts. `backend/data/seed.sql` only enables SQLite foreign keys; the authoritative schema/data seed is currently in `backend/app/main.py` and `seed_database.py`.

### Regenerate CSV data

```powershell
$py = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
cd backend
& $py app\seed\generate_dataset.py
```

The generator uses deterministic random seed `42` and writes to `backend/data/`. CSV generation is an export/data-fixture path; the running app seeds SQLite directly rather than importing every CSV.

## API reference

Base URL: `http://localhost:8000`.

### Health, identity, operators, and machines

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok","product":"Smart Operator Companion"}` |
| `POST` | `/auth/demo-login` | Returns a demo token/operator object; does not establish production auth |
| `GET` | `/auth/me` | Returns the fixed demo operator |
| `GET` | `/operators` | Lists operators |
| `GET` | `/operators/{id}` | Reads one operator |
| `GET` | `/operators/{id}/summary` | Home summary, latest evaluation, machine telemetry, conditions, task counts |
| `GET` | `/machine-domains` | Machine domains, phases, and primary metrics |
| `GET` | `/machines` | Lists seeded machines |
| `GET` | `/machines/{id}` | Reads one machine |
| `GET` | `/machines/{id}/telemetry` | Machine plus latest demo telemetry |

### Tasks and prediction

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/tasks` | Legacy task list |
| `GET` | `/tasks/today` | Legacy today list used by the frontend |
| `GET` | `/tasks/{id}` | Reads a task; accepts `T002-today` through the compatibility alias |
| `POST` | `/tasks/{id}/start` | Marks a task in progress |
| `POST` | `/tasks/{id}/complete` | Marks a task complete |
| `GET` | `/tasks/{id}/prediction` | Returns deterministic minute estimate, range, confidence, and factors |
| `GET` | `/api/tasks?date=YYYY-MM-DD` | Combined-plan envelope: `{date, operator_id, tasks}` |

Invalid dates return:

```json
{"error":{"code":"invalid_date","message":"date must be YYYY-MM-DD"}}
```

### Work sessions and telemetry

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/work/sessions` | Lists operator sessions |
| `POST` | `/work/sessions` | Creates a session |
| `GET` | `/work/sessions/{id}` | Reads a session |
| `POST` | `/work/sessions/{id}/start` | Starts a session and its task |
| `GET` | `/work/sessions/{id}/telemetry` | Returns persisted or generated telemetry frames |
| `POST` | `/work/sessions/{id}/complete` | Completes work and evaluates objective performance |
| `GET` | `/work/sessions/{id}/safety` | Lists persisted incidents |
| `POST` | `/sessions/work/start` | Friendly workflow alias |
| `GET` | `/sessions/work/{id}/live` | Friendly live-telemetry alias |
| `POST` | `/sessions/work/{id}/complete` | Friendly completion alias |
| `WS` | `/ws/work/{session_id}` | Streams generated telemetry approximately once per second, up to 180 frames |

A WebSocket frame can include `ambient_temp_c`, `humidity_pct`, `engine_temp_c`, `hydraulic_load_pct`, `fuel_level_pct`, `cycle_phase`, `seatbelt_fastened`, `proximity_distance_m`, `proximity_limit_m`, `proximity_closing_speed_mps`, `tilt_deg`, `weather`, `visibility`, `ground_condition`, `unusual_pattern`, `safety_events`, and `operator_guidance`.

### Objective evaluation, comparison, and calibration

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/performance/evaluate` | Evaluate a session with optional current metrics/context |
| `GET` | `/performance/evaluate/{session_id}` | Evaluate/read a session and calibration signal |
| `GET` | `/performance/{operator_id}/benchmark-comparison` | Historical benchmark comparison |
| `GET` | `/performance/{operator_id}/personal-baseline` | Personal baseline for a scenario |
| `GET` | `/performance/{operator_id}/summary` | Legacy summary alias |
| `GET` | `/performance/{operator_id}/trends` | Trend values |
| `GET` | `/performance/{operator_id}/calibration` | Operator calibration history |
| `GET` | `/calibration/{operator_id}` | Legacy calibration list |
| `GET` | `/calibration/{operator_id}/latest` | Latest calibration record |
| `GET` | `/benchmarks` | All task benchmarks |
| `GET` | `/benchmarks/{scenario_id}` | One benchmark |
| `POST` | `/api/performance/evaluate` | Combined-plan evaluation alias |
| `GET` | `/api/performance/{operator_id}` | Combined-plan summary alias |
| `GET` | `/api/performance/{operator_id}/comparison` | Combined-plan comparison alias |
| `GET` | `/api/calibration/{operator_id}` | Combined-plan calibration alias |
| `GET` | `/api/benchmarks` and `/api/benchmarks/{scenario_id}` | Combined-plan benchmark aliases |

Evaluation keeps these reference points separate:

1. fixed task benchmark,
2. context-adjusted benchmark (temperature, humidity/ground, load, visibility, machine state),
3. personal operator baseline,
4. current operating evidence.

It returns benchmark/personal deviations, context contributors, duration status, subscores, proficiency estimate, and task prediction. Reflection text is not used to calculate objective score.

### Combined job/review contract

| Method | Route | Request | Result |
| --- | --- | --- | --- |
| `POST` | `/api/jobs/{job_id}/start` | none | Creates a seeded work session and returns `job_id`, `session_id`, `seed`, options, and predicted minutes |
| `POST` | `/api/incidents` | `{session_id or job_id, code/type, severity, ...}` | Persists an incident; `201` on success |
| `POST` | `/api/jobs/{job_id}/review` | `{transcript, actual_minutes?, telemetry_summary?}` | `200` with grade, reflection, calibration, recommendation |
| `POST` | `/api/jobs/{job_id}/review` with `ML_FORCE_DOWN=1` | same | `202`, saves the review, returns `grade: null`, `needs_review: true`, and a fallback recommendation |
| `GET` | `/api/anomalies` | none | Deterministic anomalies; `503 ml_unavailable` when `ML_FORCE_DOWN=1` |
| `GET` | `/api/recommendations/{operator_id}` | none | Adaptive recommendation |

The default operator is derived from cookie `operator_id`; `OP1001` is normalized to the database identifier `OP-001`. The frontend's legacy helpers explicitly use `OP-001`.

API errors use this shape where handled by the application:

```json
{"error":{"code":"...","message":"..."}}
```

### Reflection and training

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/reflections` | Runs objective evaluation first, analyzes reflection, saves calibration, recommends training |
| `GET` | `/reflections/{session_id}` | Reads a saved reflection |
| `POST` | `/reflections/{session_id}/analyze` | Reflection compatibility alias |
| `GET` | `/training/scenarios` | Lists 30 seeded scenarios and benchmarks |
| `GET` | `/training/scenarios/{id}` | Reads one scenario |
| `GET` | `/training/scenarios/recommended` | Reads the current recommendation |
| `POST` | `/training/runs` | Starts a training run |
| `POST` | `/training/runs/{id}/events` | Persists a control event |
| `POST` | `/training/runs/{id}/complete` | Completes a run and updates baselines |
| `POST` | `/sessions/train/start` | Friendly training-start alias |
| `POST` | `/sessions/train/{id}/complete` | Friendly training-completion alias |
| `POST` | `/api/sim-attempts` | Saves one of five supported simulator module attempts |
| `GET` | `/api/sim-attempts` | Lists demo-operator attempts |
| `GET` | `/api/sim-modules` | Lists module IDs and pass thresholds |
| `GET` | `/baselines/{operator_id}` | Reads operator baselines |
| `GET` | `/baselines/{operator_id}/{scenario_id}` | Reads scenario-specific baselines |
| `GET` | `/recommendations/{operator_id}` | Legacy recommendation route |
| `GET` | `/recommendations/current` | Current demo recommendation |
| `POST` | `/recommendations/generate` | Regenerates a recommendation |

Supported simulation module IDs are `controls-basics`, `safe-startup`, `efficient-loading`, `wet-trenching`, and `hazard-callout`. The thresholds are 70, 80, 75, 75, and 80 respectively.

### Reports

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/reports/summary` | Backend-driven operational summary and benchmark comparison |
| `GET` | `/reports/safety` | Safety summary |
| `GET` | `/reports/training` | Training summary |
| `GET` | `/reports/machines` | Machine list and comparison |
| `GET` | `/reports/{kind}` | Generic report wrapper |
| `GET` | `/reports/export.csv` | Downloads a flattened metric/value CSV |

## Database and seed data

The schema is created in `main.py` and migrated additively with `migrate_schema()` / `ensure_column()` so older demo databases can still start. Current table groups are:

| Group | Tables |
| --- | --- |
| Reference | `operators`, `machines`, `machine_domains`, `tasks`, `training_scenarios`, `task_benchmarks` |
| Training | `training_runs`, `training_events`, `operator_baselines`, `personal_operator_baselines`, `sim_attempts`, `recommendations` |
| Work/telemetry | `work_sessions`, `sensor_events`, `machine_cycles`, `hazard_events`, `incidents` |
| Evaluation | `context_evaluations`, `performance_scores`, `performance_evaluations`, `calibration_results` |
| Reflection/analytics | `reflections`, `anomalies`, `reports` |

A fresh application seed currently contains approximately:

- 20 operators and 8 machines
- 155 SQLite tasks (the five named demo tasks plus generated task history)
- 30 training scenarios and 30 benchmarks
- 200 seeded training runs
- 151 work sessions, 151 hazard events, 151 reflections, and 750 machine-cycle rows
- 22,500 persisted synthetic sensor rows
- one seeded `WS-DEMO` evaluation/calibration path

The checked-in CSV fixtures currently contain:

| File | Rows | Role |
| --- | ---: | --- |
| `operators.csv` | 20 | Operator profiles |
| `machines.csv` | 8 | Machine export |
| `machine_domains.csv` | 2 | Domain/phase metadata |
| `tasks.csv` | 150 | Task export |
| `synthetic_tasks.csv` | 3,000 | Expanded task fixture |
| `training_scenarios.csv` | 30 | Scenario export |
| `task_benchmarks.csv` | 30 | Benchmark export |
| `training_runs.csv` | 200 | Training history fixture |
| `operator_baselines.csv` | 32 | Metric baselines |
| `personal_operator_baselines.csv` | 20 | Personal baselines |
| `work_sessions.csv` | 150 | Work history fixture |
| `hazard_events.csv` | 150 | Hazard history fixture |
| `reflections.csv` | 150 | Reflection history fixture |
| `sensor_events.csv` | 22,500 | Correlated telemetry history |
| `machine_cycles.csv` | 750 | Cycle history |
| `synthetic_telemetry.csv` | 2,000 | Compact synthetic telemetry export |

CSV IDs such as `M-1` in generated exports do not always match the richer IDs used by the direct SQLite seed (`M-320`, `M-777`, etc.). Do not assume the CSVs are a complete database dump.

## Prediction, evaluation, and safety logic

### Task prediction

`predict_minutes()` uses the task baseline duration and deterministic multipliers:

- weather: rainy/wet, foggy, windy, and hot adjustments;
- operator skill: beginner through advanced;
- machine age: bounded age adjustment.

It returns a predicted value, a range, a confidence, contributing factors, and `unit: "minutes"`.

Completed-session evaluation uses a separate hour-based model so a long operating session can be compared with the 6–8 hour-style task benchmarks and personal history. This unit split is intentional and shown in the UI.

### Context-adjusted benchmark

Context factors are explainable and capped at 25% total. Current rules can add time for high temperature, high humidity, hard/rocky or wet ground, high workload, reduced visibility, and non-operational machine state. The response includes both the factor breakdown and human-readable contributors.

### Objective score

The runtime score combines safety, efficiency, hazard response, cycle range, duration deviation, and control precision. The score is calculated from telemetry/session metrics before any reflection analysis. A seeded demo session is deliberately pinned to objective score 58 to make the calibration story reproducible.

### Safety rules

- Base proximity limit: **8 m**.
- Rain, reduced visibility, wet ground, or mud: **10 m condition-adjusted limit**.
- Base tilt limit: **6°**; wet/reduced-condition limit: **5°**.
- Seatbelt warning when moving without a belt.
- Proximity transitions: onset, persistent escalation, resolution, and `PROXIMITY_APPROACHING` when closing speed is at least 2 m/s before crossing the limit.
- Visibility/rain guidance is deterministic.
- `live_operator_guidance()` chooses safety, approaching-hazard, working-condition, idle, anomaly, or normal guidance without an LLM.

The backend persists sensor frames and de-duplicated live incident/hazard records while the WebSocket is active.

### Calibration and adaptation

`calibration_signal()` classifies a confidence/objective difference of at least 20 points as `OVERCONFIDENCE_RISK` or `UNDERCONFIDENCE`; smaller gaps are `CALIBRATED`. Recommendations then prioritize proximity/hazard practice for a blind spot or weak safety response, and efficiency practice for large task-time/consistency deviations.

## LLM, Jev, and fallback behavior

The only language-model responsibility is interpreting the operator's reflection. The system prompt explicitly prohibits inventing telemetry, task time, safety events, or machine state.

- With `OPENROUTER_API_KEY` or `LLM_API_KEY`, `backend/app/services/llm.py` calls an OpenAI-compatible chat-completions endpoint with JSON output and temperature `0`.
- `LLM_BASE_URL` and `LLM_MODEL` can override the endpoint/model.
- OpenRouter receives `HTTP-Referer` and `X-Title` headers.
- Network errors, malformed provider output, or no key fall back to `FallbackLLMProvider`.
- The fallback uses deterministic keyword-derived confidence, perceived performance, difficulty, hazard awareness, strengths, weaknesses, hazards, and summary.
- The current “Jev” output is deterministic language-derived `jev_scores` plus `expertise_level`; it is **not** an installed Jev/TypeSafe model or separate service.
- Offline fallback currently reports `needs_review: false`; the ML-down job-review path deliberately returns `202`, `grade: null`, `needs_review: true`, and a deterministic recommendation.

This separation is a product constraint: reflection language can explain self-perception, but it cannot override objective performance or safety evaluation.

## Simulator and telemetry

### Simulator

The visible simulator is a prototype inside `frontend/app/page.tsx`:

- React Three Fiber `Canvas` with primitive meshes for ground, machine body, boom, and bucket;
- no downloaded 3D model or GLTF asset;
- two-step guided tour;
- timer, control buttons, score, penalties, progress, and idempotent completion guard;
- control events are submitted to `/api/sim-attempts` and passing attempts update training baselines.

The five API module IDs exist, but the current client uses a generic control scene and maps target skills to module IDs. It does not implement the full module-specific mechanics described in the external build plan.

### Telemetry

`telemetry_value()` generates a deterministic frame from the session seed. The demo seed creates rainy conditions and staged seatbelt/proximity/tilt/visibility changes. `/ws/work/{session_id}` evaluates each frame against the previous frame, persists it, attaches alerts/guidance, and sends JSON to the browser.

The Work UI also has browser-side fallback updates if a WebSocket cannot be opened. This is a resilience/demo behavior, not a hardware telemetry adapter. The UI offers 1×, 10×, and 60× controls, pause/resume, and a voice-note action; the server's synthetic WebSocket loop itself remains approximately one frame per second.

## Frontend views and what is real

| View | Current behavior | Caveat |
| --- | --- | --- |
| Home | Reads summary, tasks, machine, recommendation, evaluation, and anomalies | Search and notification affordances are visual/demo controls |
| My Tasks | Lists tasks and fetches predictions per task | Date tabs and “Sync with Site” are not connected to alternate data sources |
| Work | Safety gate, telemetry, WebSocket, pause/speed controls, guidance, incidents, voice note, expected-vs-actual | Synthetic feed; no actual machine controls |
| Reflect | Editable 10,000-character debrief, speech input, calibration result, recommendation | SpeechRecognition is browser-dependent; LLM is optional |
| Training Hub | Scenarios, recommended next step, saved attempts, progress, simulator launch | Category/resource cards are presentational; mechanics are simplified |
| Machines | Lists selected seeded machine models and starts a work context | No fleet-management or real machine switching |
| Reports | Backend summary, benchmark bars, safety values, CSV link | Aggregates are seeded/demo data |
| Settings | Shows demo operator and synthetic mode | No persisted preferences or authentication settings |

## Testing and verification

### Backend

From the repository root on the verified Windows setup:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m pytest backend/tests
```

Latest verified result: **18 passed**. The run emits non-blocking deprecation warnings for FastAPI `on_event` and `datetime.utcnow()`.

### Frontend

```powershell
cd frontend
npm ci
npm run lint
npm run build
npx tsc --noEmit
```

Latest verified results:

- `npm run lint`: no ESLint warnings or errors
- `npm run build`: successful Next.js production build
- `npx tsc --noEmit`: clean after the build generated `.next/types`

The backend contract tests cover the seeded `T002-today` start/review path, objective score 58, calibration gap 29, blind-spot recommendation, unknown simulation-module rejection, and ML-down review fallback. Engine tests cover deviation, context adjustment, duration status, safety transitions, approach warnings, guidance, calibration, and recommendations.

## Screenshots and media

No screenshots, image assets, GLTF models, or other media are checked into this repository. The README intentionally contains no broken image links. To capture screenshots, run the two local servers and capture the Home, My Tasks, Work, Reflect, Training Hub, Machines, Reports, and Settings views at the target demo resolution.

The simulator's “3D” view is generated from Three.js primitive geometry at runtime; it does not depend on a missing model file.

## Known limitations and release risks

1. **Synthetic evidence:** telemetry, work history, machine values, hazards, and most report aggregates are seeded/generated. They are not claims about a real operator or machine.
2. **No production authentication:** demo login returns a token-shaped value but does not validate it; most identity is fixed to `OP-001` or a cookie.
3. **No CAT integration:** there is no CAN/telemetry adapter, machine command path, fleet service, offline sync queue, or real incident dispatch.
4. **No trained ML:** anomaly detection, prediction, scoring, and safety are deterministic rules/formulas. `ML_FORCE_DOWN=1` is a test switch, not a model health monitor.
5. **LLM availability and privacy:** external reflection analysis requires a provider/key and sends reflection text to that provider. The offline fallback is intentionally shallow.
6. **Browser speech support:** Web Speech/SpeechRecognition support and microphone permission vary by browser and platform; typed debrief remains the fallback.
7. **Database hardening:** SQLite is local, schema migration is additive and lightweight, writes use short-lived raw connections, and there is no production backup/retention strategy.
8. **Runtime structure:** `main.py` is a large prototype module and contains compatibility logic that would normally be separated into routers/services/repositories.
9. **UI placeholders:** search, date filters, some navigation cards, learning resources, and settings are not full product workflows.
10. **Reports:** CSV export is a flattened metric/value summary and does not provide a full analytics export.
11. **Warnings/security:** the verified test run reports FastAPI/date deprecations. `npm ci` reports five audit vulnerabilities in the current dependency tree (four high and one critical), and the pinned Next.js version has a published security advisory; review before production deployment.
12. **Distribution:** no `LICENSE` file is present in the repository; add licensing/brand approvals before external distribution.

## Differences from the external `COMBINED.md` build plan

The comparison source is outside this repository at `C:\Users\Arnav\Downloads\COMBINED.md`. It describes a planned four-person monorepo and should not be treated as a source file for the current implementation.

| `COMBINED.md` plan | Current repository |
| --- | --- |
| Bun monorepo with `apps/web`, `apps/ml`, `packages/db`, `packages/telemetry`, and `packages/sim` | One Next.js app and one FastAPI app; no `apps/` or `packages/` directories |
| Postgres/Drizzle-style database package, Docker, `bun install`, and `uv` ML environment | Local raw SQLite, Python requirements, npm, and no required Docker/Postgres/uv workflow |
| Six frozen API routes as the principal interface | Those combined routes are present, plus a larger legacy route surface preserved for the existing UI |
| `T002-today` selected with a `findDemoSeed` telemetry search | Public `T002-today` is mapped to stored `T-002` and fixed seed `170923`; no `findDemoSeed` helper is present |
| ML service with GradientBoosting task model and IsolationForest anomalies | Deterministic task multipliers and anomaly rules; no trained model files or ML service |
| Jev/TypeSafe classification through OpenRouter | Optional OpenAI-compatible reflection provider plus local deterministic Jev-style language signals; no Jev SDK/model |
| Telemetry package with playback, tracker, and seed search | FastAPI-generated WebSocket telemetry, server-side previous-frame safety evaluation, and a small browser fallback timer |
| Full five-module mechanics, cab camera, GLTF fallback, and package-level simulator | Primitive React Three Fiber scene, generic controls, guided tour, score/penalties, and five API module IDs |
| ML-down task prediction shown as unavailable | Review grading has the specified `202` fallback; ordinary deterministic task prediction remains available, while `/api/anomalies` can return `503 ml_unavailable` |
| `docs/demo.md`, architecture docs, and screenshot-oriented integration gate | This root README documents setup/demo/status; those separate docs and screenshot assets are absent |
| Stretch maintenance detection, fleet correlation, and operator switcher | Basic seeded anomaly detection and cookie normalization exist; maintenance correlation/fleet analytics are not implemented |
| Primary plan differentiator: spoken debrief routed through an LLM | Spoken/text debrief, calibration, explicit overconfidence coaching, context-aware margins, anticipatory closing-speed alerts, and deterministic live guidance are implemented; the LLM remains reflection-only |

The current implementation therefore preserves the useful contract ideas from `COMBINED.md` while intentionally choosing a smaller offline-safe architecture for the hackathon prototype.

## Practical next steps

1. Replace synthetic telemetry with a versioned CAT/fleet adapter and authenticated operator/session identity.
2. Move schema, repositories, routers, and engines out of `main.py`; add real migrations and database backup/retention.
3. Add a separate ML service only after defining evaluation datasets, model artifacts, drift checks, and safe fallbacks.
4. Replace the heuristic Jev signal with the approved provider/integration and add privacy/retention controls for reflections.
5. Implement module-specific simulator scoring and real assets while keeping primitive fallback geometry.
6. Add browser e2e tests, a reproducible fresh-clone rehearsal, screenshot fixtures, and production dependency/security review.
