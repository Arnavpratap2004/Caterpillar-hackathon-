from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3, json, random, math, io, csv, asyncio, re, os
from app.services.llm import get_provider, FallbackLLMProvider

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "smart_operator.db"
app = FastAPI(title="Smart Operator Companion", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

REVIEW_CONFIDENCE = 0.6
MAX_TRANSCRIPT_CHARS = 10000
IDLE_SECONDS_THRESHOLD = 60.0
FUEL_PER_CYCLE_THRESHOLD_L = 5.0
DEMO_TASK_ID = 'T002-today'
DEMO_TASK_SEED = 170923
SUPPORTED_SIM_MODULES = {
    'controls-basics': {'name':'Controls Basics','skill':'control_precision','pass_score':70,'duration_sec':180},
    'safe-startup': {'name':'Safe Startup','skill':'safety','pass_score':80,'duration_sec':180},
    'efficient-loading': {'name':'Efficient Loading','skill':'cycle_efficiency','pass_score':75,'duration_sec':240},
    'wet-trenching': {'name':'Wet Trenching','skill':'situational_awareness','pass_score':75,'duration_sec':240},
    'hazard-callout': {'name':'Hazard Callout','skill':'hazard_response','pass_score':80,'duration_sec':180},
}

SCHEMA = '''
CREATE TABLE IF NOT EXISTS operators (operator_id TEXT PRIMARY KEY, name TEXT, experience_years REAL, level TEXT, site TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS machines (machine_id TEXT PRIMARY KEY, model TEXT, machine_type TEXT, domain TEXT, status TEXT, engine_hours REAL, fuel REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS machine_domains (domain TEXT PRIMARY KEY, name TEXT, phases TEXT, primary_metrics TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, operator_id TEXT, machine_id TEXT, domain TEXT, task_type TEXT, site TEXT, scheduled_start TEXT, scheduled_end TEXT, status TEXT, baseline_duration_min REAL, weather TEXT DEFAULT 'clear', operator_skill TEXT DEFAULT 'intermediate', machine_age_hours REAL DEFAULT 0, demo_seed INTEGER, job_options_json TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS training_scenarios (scenario_id TEXT PRIMARY KEY, name TEXT, domain TEXT, machine_type TEXT, difficulty TEXT, duration_min INTEGER, target_skill TEXT, hazard_type TEXT, description TEXT, baseline_metrics TEXT);
CREATE TABLE IF NOT EXISTS training_runs (run_id TEXT PRIMARY KEY, operator_id TEXT, scenario_id TEXT, started_at TEXT, completed_at TEXT, score REAL, task_time_sec REAL, hazard_response_sec REAL, control_precision REAL, efficiency_score REAL, safety_score REAL, passed INTEGER);
CREATE TABLE IF NOT EXISTS training_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, timestamp TEXT, control_type TEXT, control_duration_sec REAL, cycle_phase TEXT, hazard_time_sec REAL, operator_response_time_sec REAL, unnecessary_action INTEGER, payload TEXT);
CREATE TABLE IF NOT EXISTS operator_baselines (baseline_id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id TEXT, scenario_id TEXT, metric_name TEXT, metric_value REAL, sample_count INTEGER, updated_at TEXT, UNIQUE(operator_id,scenario_id,metric_name));
CREATE TABLE IF NOT EXISTS personal_operator_baselines (baseline_id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id TEXT, scenario_id TEXT, average_task_time_hours REAL, average_cycle_time_sec REAL, average_hazard_response_sec REAL, average_efficiency REAL, average_safety REAL, average_control_precision REAL, consistency_score REAL, sample_count INTEGER, updated_at TEXT, UNIQUE(operator_id,scenario_id));
CREATE TABLE IF NOT EXISTS task_benchmarks (benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT, scenario_id TEXT UNIQUE, task_type TEXT, machine_type TEXT, domain TEXT, expected_duration_min REAL, expected_duration_max REAL, expected_cycle_time_min_sec REAL, expected_cycle_time_max_sec REAL, minimum_safety_score REAL, minimum_efficiency_score REAL, maximum_hazard_response_sec REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS work_sessions (session_id TEXT PRIMARY KEY, operator_id TEXT, machine_id TEXT, task_id TEXT, started_at TEXT, ended_at TEXT, predicted_time_min REAL, actual_time_min REAL, overall_score REAL, safety_score REAL, efficiency_score REAL, status TEXT, data_json TEXT, telemetry_seed INTEGER, job_options_json TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS sensor_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, timestamp TEXT, ambient_temp_c REAL, humidity_pct REAL, wind_speed_kmh REAL, fuel_level_pct REAL, fuel_rate_lph REAL, engine_rpm REAL, engine_temp_c REAL, hydraulic_load_pct REAL, payload_pct REAL, seatbelt_fastened INTEGER, proximity_distance_m REAL, visibility TEXT, soil_type TEXT, ground_condition TEXT, cycle_phase TEXT, tilt_deg REAL, weather TEXT, idle_seconds REAL, fuel_per_cycle_l REAL, unusual_pattern INTEGER, gps_x REAL, gps_y REAL);
CREATE TABLE IF NOT EXISTS machine_cycles (cycle_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, cycle_number INTEGER, phase TEXT, start_time TEXT, end_time TEXT, duration_sec REAL);
CREATE TABLE IF NOT EXISTS hazard_events (hazard_id TEXT PRIMARY KEY, session_id TEXT, hazard_type TEXT, severity TEXT, trigger_time TEXT, response_time TEXT, response_duration_sec REAL, acknowledged INTEGER, suppressed INTEGER, escalated INTEGER, resolved INTEGER);
CREATE TABLE IF NOT EXISTS reflections (reflection_id TEXT PRIMARY KEY, session_id TEXT, operator_id TEXT, text TEXT, self_confidence REAL, perceived_performance REAL, perceived_difficulty REAL, hazard_awareness REAL, llm_summary TEXT, created_at TEXT, strengths TEXT, weaknesses TEXT, mentioned_hazards TEXT);
CREATE TABLE IF NOT EXISTS performance_scores (score_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, control_precision REAL, cycle_efficiency REAL, safety REAL, situational_awareness REAL, hazard_response REAL, overall_score REAL);
CREATE TABLE IF NOT EXISTS context_evaluations (evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT UNIQUE, temperature_factor REAL, ground_factor REAL, load_factor REAL, visibility_factor REAL, total_context_factor REAL, adjusted_min_duration REAL, adjusted_max_duration REAL, explanation TEXT);
CREATE TABLE IF NOT EXISTS performance_evaluations (evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT UNIQUE, benchmark_deviation_pct REAL, personal_deviation_pct REAL, overall_score REAL, status TEXT, explanation TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS calibration_results (calibration_id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, objective_score REAL, self_confidence REAL, calibration_gap REAL, state TEXT, explanation TEXT);
CREATE TABLE IF NOT EXISTS recommendations (recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT, operator_id TEXT, scenario_id TEXT, reason TEXT, target_skill TEXT, priority INTEGER, created_at TEXT, completed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS incidents (incident_id TEXT PRIMARY KEY, session_id TEXT, type TEXT, severity TEXT, timestamp TEXT, status TEXT, resolution TEXT);
CREATE TABLE IF NOT EXISTS sim_attempts (attempt_id TEXT PRIMARY KEY, operator_id TEXT, module_id TEXT, score REAL, passed INTEGER, duration_sec REAL, penalties INTEGER DEFAULT 0, objectives_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS anomalies (anomaly_id TEXT PRIMARY KEY, operator_id TEXT, session_id TEXT, kind TEXT, severity TEXT, message TEXT, features_json TEXT DEFAULT '{}', created_at TEXT);
CREATE TABLE IF NOT EXISTS reports (report_id INTEGER PRIMARY KEY AUTOINCREMENT, report_type TEXT, generated_at TEXT, payload TEXT);
'''

def conn():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def ensure_column(cursor, table, column, definition):
    existing={x['name'] for x in cursor.execute(f'PRAGMA table_info({table})').fetchall()}
    if column not in existing:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

def migrate_schema(cursor):
    # The prototype originally shipped with a smaller schema. Keep existing demo
    # databases usable while adding the frozen job/simulation contracts.
    for table, column, definition in (
        ('tasks','weather',"TEXT DEFAULT 'clear'"),
        ('tasks','operator_skill',"TEXT DEFAULT 'intermediate'"),
        ('tasks','machine_age_hours','REAL DEFAULT 0'),
        ('tasks','demo_seed','INTEGER'),
        ('tasks','job_options_json',"TEXT DEFAULT '{}'"),
        ('work_sessions','telemetry_seed','INTEGER'),
        ('work_sessions','job_options_json',"TEXT DEFAULT '{}'"),
        ('sensor_events','tilt_deg','REAL DEFAULT 0'),
        ('sensor_events','weather',"TEXT DEFAULT 'clear'"),
        ('sensor_events','idle_seconds','REAL DEFAULT 0'),
        ('sensor_events','fuel_per_cycle_l','REAL DEFAULT 0'),
        ('sensor_events','unusual_pattern','INTEGER DEFAULT 0'),
        ('sensor_events','visibility',"TEXT DEFAULT 'Good'"),
        ('sensor_events','soil_type',"TEXT DEFAULT ''"),
        ('sensor_events','ground_condition',"TEXT DEFAULT ''"),
        ('sensor_events','cycle_phase',"TEXT DEFAULT ''"),
        ('sensor_events','gps_x','REAL DEFAULT 0'),
        ('sensor_events','gps_y','REAL DEFAULT 0'),
        ('incidents','resolution',"TEXT DEFAULT ''"),
    ):
        ensure_column(cursor,table,column,definition)

def now(): return datetime.utcnow().isoformat(timespec="seconds")

def api_error(status_code, code, message, details=None):
    payload={'error':{'code':code,'message':message}}
    if details is not None: payload['error']['details']=details
    return JSONResponse(status_code=status_code, content=payload)

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return api_error(400,'invalid_request','Request validation failed',exc.errors())

def canonical_operator(value):
    value=(value or 'OP1001').upper().replace('_','-')
    match=re.fullmatch(r'OP-?(\d{3,4})',value)
    if not match: return 'OP-001'
    digits=match.group(1)
    # The contract uses OP1001 while the existing database uses OP-001.
    number=int(digits)-1000 if len(digits)==4 else int(digits)
    return f'OP-{max(1,number):03d}'

def operator_from_request(request: Request):
    return canonical_operator(request.cookies.get('operator_id','OP1001'))
def rows(sql, args=()):
    with conn() as c: return [dict(x) for x in c.execute(sql,args).fetchall()]
def row(sql,args=()):
    x=rows(sql,args); return x[0] if x else None
def execute(sql,args=()):
    with conn() as c: c.execute(sql,args); c.commit()

def calculate_performance(metrics: dict):
    safety=float(metrics.get('safety', metrics.get('safety_score', 80))); efficiency=float(metrics.get('efficiency', metrics.get('efficiency_score', 70)))
    hazard=float(metrics.get('hazard_response', metrics.get('hazard_score', 70))); precision=float(metrics.get('control_precision', 75)); consistency=float(metrics.get('consistency', 75))
    return round(max(0,min(100,safety*.20+efficiency*.25+hazard*.20+precision*.20+consistency*.15)),1)

def compare_to_baseline(current: dict, baseline: dict):
    deviations={}; abnormal=[]
    for key,value in current.items():
        if key not in baseline or not baseline[key]: continue
        # higher is better for score metrics; lower is better for time/idle
        pct=(float(value)-float(baseline[key]))/float(baseline[key])*100
        deviations[key]=round(pct,1)
        if abs(pct)>=10: abnormal.append(key)
    avg=round(sum(abs(x) for x in deviations.values())/len(deviations),1) if deviations else 0
    explanation='; '.join(f"{k.replace('_',' ').title()} is {abs(v):.0f}% {'above' if v>0 else 'below'} baseline" for k,v in deviations.items() if abs(v)>=10)
    return {'deviation_score':avg,'deviation_percent':deviations,'phase_deviations':deviations,'abnormal_metrics':abnormal,'explanation':explanation or 'Performance is within your normal range.'}

def calculate_benchmark_deviation(current_hours, adjusted_min, adjusted_max):
    midpoint=(float(adjusted_min)+float(adjusted_max))/2
    return round((float(current_hours)-midpoint)/midpoint*100,1) if midpoint else 0.0

def calculate_personal_deviation(current_hours, personal_hours):
    return round((float(current_hours)-float(personal_hours))/float(personal_hours)*100,1) if personal_hours else 0.0

def calculate_overall_score(metrics):
    return calculate_performance(metrics)

def calculate_task_prediction(benchmark, personal_baseline, context=None, current_efficiency=82.0, machine_state=None):
    return predict_task_time_context(benchmark,personal_baseline,context,current_efficiency,machine_state)

def classify_operator_state(performance, confidence):
    if performance>=70 and confidence>=70: return 'CALIBRATED'
    if performance>=70 and confidence<70: return 'UNDERCONFIDENT'
    if performance<70 and confidence<70: return 'AWARE_DEVELOPING'
    return 'BLIND_SPOT'

def calculate_calibration_gap(objective, confidence): return round(abs(float(objective)-float(confidence)),1)
def calculate_proficiency(m):
    score=round(float(m.get('performance',m.get('objective_score',70)))*.30+float(m.get('safety',80))*.20+float(m.get('efficiency',70))*.15+float(m.get('hazard_response',70))*.15+float(m.get('consistency',75))*.10+(100-float(m.get('calibration_gap',20)))*.10,1)
    return {'score':score,'level':'Novice' if score<50 else 'Developing' if score<70 else 'Proficient' if score<85 else 'Advanced'}

def predict_task_time(baseline_time, operator_factor=1, environment_factor=1, machine_factor=1):
    val=baseline_time*max(.85,min(1.2,operator_factor))*max(.9,min(1.2,environment_factor))*max(.9,min(1.15,machine_factor))
    return {'predicted_time':round(val,1),'confidence':round(max(55,95-abs(val-baseline_time)*1.5),0),'top_contributing_factors':[x for x,y in [('operator efficiency',operator_factor),('environment',environment_factor),('machine state',machine_factor)] if abs(y-1)>.02]}

def benchmark_defaults(scenario):
    name=(scenario['name'] or '').lower(); domain=scenario['domain']
    if 'haul' in name or domain=='HAUL_TRANSPORT':
        return {'task_type':'Haul Cycle','min':5.0,'max':7.0,'cycle_min':160.0,'cycle_max':210.0,'safety':95.0,'efficiency':82.0,'hazard':2.5}
    if 'load' in name or 'loading' in name:
        return {'task_type':'Material Loading','min':4.0,'max':6.0,'cycle_min':90.0,'cycle_max':125.0,'safety':94.0,'efficiency':78.0,'hazard':2.8}
    return {'task_type':'Excavation — Trench Digging','min':6.0,'max':8.0,'cycle_min':135.0,'cycle_max':160.0,'safety':95.0,'efficiency':80.0,'hazard':2.5}

def ensure_reference_data(cursor):
    """Create reference points on first run and migrate an existing demo database."""
    cursor.executemany('INSERT OR IGNORE INTO machine_domains VALUES (?,?,?, ?,?)',[('EXCAVATION_LOAD','Excavation / Loading',json.dumps(['ACQUIRE','LIFT','SWING','DUMP','RETURN']),json.dumps(['cycle_time','phase_duration','control_precision','idle_time','hazard_response','load_handling','safety_behavior']),now()),('HAUL_TRANSPORT','Haul / Transport',json.dumps(['LOAD','TRAVEL_LOADED','QUEUE_SPOT','DUMP','TRAVEL_EMPTY','RETURN']),json.dumps(['cycle_time','queue_time','reaction_latency','loaded_travel','unloaded_travel','stop_response','efficiency']),now())])
    scenarios=cursor.execute('SELECT * FROM training_scenarios').fetchall()
    for s in scenarios:
        b=benchmark_defaults(s)
        if not cursor.execute('SELECT 1 FROM task_benchmarks WHERE scenario_id=?',(s['scenario_id'],)).fetchone():
            cursor.execute('INSERT INTO task_benchmarks(scenario_id,task_type,machine_type,domain,expected_duration_min,expected_duration_max,expected_cycle_time_min_sec,expected_cycle_time_max_sec,minimum_safety_score,minimum_efficiency_score,maximum_hazard_response_sec,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(s['scenario_id'],b['task_type'],s['machine_type'],s['domain'],b['min'],b['max'],b['cycle_min'],b['cycle_max'],b['safety'],b['efficiency'],b['hazard'],now()))
    operators=cursor.execute('SELECT operator_id FROM operators').fetchall()
    for op_row in operators:
        op=op_row['operator_id']
        for s in scenarios:
            if not cursor.execute('SELECT 1 FROM personal_operator_baselines WHERE operator_id=? AND scenario_id=?',(op,s['scenario_id'])).fetchone():
                if op=='OP-001': values=(7.2,140.0,2.0,88.0,94.0,87.0,92.0,5)
                elif op=='OP-002': values=(8.6,158.0,3.1,72.0,78.0,75.0,64.0,5)
                elif op=='OP-003': values=(9.4,166.0,2.1,70.0,96.0,72.0,81.0,4)
                elif op=='OP-004': values=(7.0,137.0,2.2,91.0,83.0,89.0,72.0,5)
                else: values=(7.8,148.0,2.4,80.0,88.0,80.0,76.0,4)
                cursor.execute('INSERT INTO personal_operator_baselines(operator_id,scenario_id,average_task_time_hours,average_cycle_time_sec,average_hazard_response_sec,average_efficiency,average_safety,average_control_precision,consistency_score,sample_count,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(op,s['scenario_id'],*values,now()))

def adjust_benchmark_for_context(benchmark, environment=None, machine_state=None):
    environment=environment or {}; machine_state=machine_state or {}; factors={'temperature':0.0,'ground':0.0,'load':0.0,'visibility':0.0,'machine':0.0}; contributors=[]
    temp=float(environment.get('ambient_temp_c',environment.get('temperature',30)) or 30)
    if temp>=34: factors['temperature']=0.05; contributors.append('high temperature')
    elif temp>=30: factors['temperature']=0.02
    humidity=float(environment.get('humidity_pct',environment.get('humidity',0)) or 0)
    ground=(str(environment.get('ground_condition',''))+' '+str(environment.get('soil_type',''))).lower()
    if humidity>=80: factors['ground']+=0.02; contributors.append('high humidity')
    if any(x in ground for x in ('hard','rock','wet','mud')): factors['ground']+=0.08 if 'hard' in ground or 'rock' in ground else 0.04; contributors.append('challenging ground')
    elif 'sandy' in ground: factors['ground']+=0.035; contributors.append('sandy ground')
    load=float(environment.get('payload_pct',environment.get('hydraulic_load_pct',environment.get('load_pct',0))) or 0)
    if load>=65: factors['load']=0.035; contributors.append('high workload')
    elif load>=45: factors['load']=0.02
    visibility=str(environment.get('visibility','good')).lower()
    if any(x in visibility for x in ('poor','low','fog','night')): factors['visibility']=0.06; contributors.append('reduced visibility')
    status=str(machine_state.get('status','operational')).lower(); engine=float(machine_state.get('engine_temp_c',0) or 0)
    if status not in ('operational','normal',''): factors['machine']=0.08; contributors.append('machine condition')
    elif engine>=85: factors['machine']=0.04; contributors.append('elevated machine temperature')
    total=round(min(0.25,sum(factors.values())),3); adjusted_min=round(float(benchmark['expected_duration_min'] if 'expected_duration_min' in benchmark else benchmark['min'])*(1+total),1); adjusted_max=round(float(benchmark['expected_duration_max'] if 'expected_duration_max' in benchmark else benchmark['max'])*(1+total),1)
    return {'adjusted_min':adjusted_min,'adjusted_max':adjusted_max,'context_factor':total,'contributing_factors':contributors or ['normal conditions'],'factors':factors,'context_adjustment_hours':round(((adjusted_min+adjusted_max)-(float(benchmark.get('expected_duration_min',benchmark.get('min')))+float(benchmark.get('expected_duration_max',benchmark.get('max')))))/2,1)}

def predict_task_time_context(benchmark, personal_baseline, context=None, current_efficiency=82.0, machine_state=None):
    adjusted=adjust_benchmark_for_context(benchmark,(context or {}).get('environment',context or {}),(context or {}).get('machine_state',machine_state or {})); operator_factor=max(.92,min(1.15,1+(float(personal_baseline.get('average_efficiency',82))-float(current_efficiency))/400)); machine_factor=max(.95,min(1.12,1.0 if not machine_state or str(machine_state.get('status','Operational')).lower()=='operational' else 1.08)); predicted_min=round(adjusted['adjusted_min']*operator_factor*machine_factor,1); predicted_max=round(adjusted['adjusted_max']*operator_factor*machine_factor,1); return {'predicted_time':round((predicted_min+predicted_max)/2,1),'predicted_time_min':predicted_min,'predicted_time_max':predicted_max,'confidence':round(max(55,94-adjusted['context_factor']*100-abs(operator_factor-1)*100),0),'baseline_time':round((float(benchmark.get('expected_duration_min',benchmark.get('min',6)))+float(benchmark.get('expected_duration_max',benchmark.get('max',8))))/2,1),'context_adjustment':adjusted['context_adjustment_hours'],'operator_adjustment':round((operator_factor-1)*100,1),'machine_adjustment':round((machine_factor-1)*100,1),'top_factors':adjusted['contributing_factors']+(['operator efficiency'] if abs(operator_factor-1)>.02 else [])}

def evaluate_safety(previous_event, current_event):
    previous_event=previous_event or {}; current_event=current_event or {}; alerts=[]
    phase=str(current_event.get('cycle_phase','')).upper(); moving=phase not in ('IDLE','PARKED','')
    belt=bool(current_event.get('seatbelt_fastened',True)); previous_belt=bool(previous_event.get('seatbelt_fastened',True))
    if moving and not belt and previous_belt:
        alerts.append({'type':'SEATBELT','severity':'HIGH','status':'OPEN','acknowledged':False,'resolution':'Seatbelt required while machine is moving.'})
    distance=float(current_event.get('proximity_distance_m',99) or 99); previous_distance=float(previous_event.get('proximity_distance_m',99) or 99)
    if distance<8 and previous_distance>=8:
        alerts.append({'type':'PROXIMITY','severity':'HIGH','status':'OPEN','acknowledged':False,'resolution':'Person entered proximity zone.'})
    elif distance<8 and distance<=previous_distance:
        alerts.append({'type':'PROXIMITY','severity':'CRITICAL','status':'ESCALATED','acknowledged':False,'resolution':'Hazard persists while distance is not recovering.'})
    elif distance>=8 and previous_distance<8:
        alerts.append({'type':'PROXIMITY','severity':'LOW','status':'RESOLVED','acknowledged':True,'resolution':'Operator response increased separation.'})
    tilt=float(current_event.get('tilt_deg',0) or 0); previous_tilt=float(previous_event.get('tilt_deg',0) or 0)
    if tilt>=6 and previous_tilt<6: alerts.append({'type':'TILT','severity':'HIGH','status':'OPEN','acknowledged':False,'resolution':'Stabilize the machine on level ground.'})
    elif tilt<4 and previous_tilt>=6: alerts.append({'type':'TILT','severity':'LOW','status':'RESOLVED','acknowledged':True,'resolution':'Machine attitude returned to a safe range.'})
    weather=str(current_event.get('visibility','Good')).lower(); previous_weather=str(previous_event.get('visibility','Good')).lower()
    if weather in ('poor','reduced','low','fog') and previous_weather not in ('poor','reduced','low','fog'):
        alerts.append({'type':'WEATHER','severity':'MEDIUM','status':'OPEN','acknowledged':False,'resolution':'Reduce speed and confirm visibility before continuing.'})
    elif weather not in ('poor','reduced','low','fog') and previous_weather in ('poor','reduced','low','fog'):
        alerts.append({'type':'WEATHER','severity':'LOW','status':'RESOLVED','acknowledged':True,'resolution':'Visibility returned to normal.'})
    return alerts

def _duration_hours(metrics):
    for key in ('task_time_hours','actual_time_hours'):
        if metrics.get(key) is not None: return float(metrics[key])
    if metrics.get('actual_time_min') is not None: return float(metrics['actual_time_min'])/60
    if metrics.get('task_time_min') is not None: return float(metrics['task_time_min'])/60
    if metrics.get('task_time_sec') is not None: return float(metrics['task_time_sec'])/3600
    return 0.0

def get_personal_baseline(operator_id='OP-001', scenario_id='SCN-PROX-01'):
    found=row('SELECT * FROM personal_operator_baselines WHERE operator_id=? AND scenario_id=?',(operator_id,scenario_id))
    if found: return found
    # Keep the baseline useful for newly created scenario/operator pairs.
    return {'operator_id':operator_id,'scenario_id':scenario_id,'average_task_time_hours':7.2,'average_cycle_time_sec':140.0,'average_hazard_response_sec':2.0,'average_efficiency':88.0,'average_safety':94.0,'average_control_precision':87.0,'consistency_score':80.0,'sample_count':0}

def evaluate_task_performance(task, current_metrics, benchmark, personal_baseline, context):
    environment=context.get('environment',context) if isinstance(context,dict) else {}; machine_state=context.get('machine_state',{}) if isinstance(context,dict) else {}
    adjusted=adjust_benchmark_for_context(benchmark,environment,machine_state); duration=_duration_hours(current_metrics); expected_min=adjusted['adjusted_min']; expected_max=adjusted['adjusted_max']
    benchmark_deviation=calculate_benchmark_deviation(duration,expected_min,expected_max); personal_time=float(personal_baseline.get('average_task_time_hours',7.2) or 7.2); personal_deviation=calculate_personal_deviation(duration,personal_time)
    if duration<=expected_max and duration>=expected_min: duration_status='WITHIN_EXPECTATION'
    elif duration<=expected_max*1.05: duration_status='SLIGHTLY_ABOVE_EXPECTATION'
    elif duration<=expected_max*1.4: duration_status='SIGNIFICANTLY_ABOVE_EXPECTATION'
    else: duration_status='SEVERE_DEVIATION'
    safety=float(current_metrics.get('safety',current_metrics.get('safety_score',80)))
    efficiency=float(current_metrics.get('efficiency',current_metrics.get('efficiency_score',70)))
    cycle=float(current_metrics.get('cycle_time_sec',current_metrics.get('cycle_time',140)))
    hazard=float(current_metrics.get('hazard_response_sec',2.0))
    hazard_limit=float(benchmark.get('maximum_hazard_response_sec',benchmark.get('hazard',2.5)))
    hazard_score=float(current_metrics.get('hazard_response_score',max(0,min(100,100-(hazard-hazard_limit)*115))))
    cycle_min=float(benchmark.get('expected_cycle_time_min_sec',benchmark.get('cycle_min',135)))
    cycle_max=float(benchmark.get('expected_cycle_time_max_sec',benchmark.get('cycle_max',160)))
    cycle_score=100 if cycle_min<=cycle<=cycle_max else 65
    duration_score=max(0,100-abs(benchmark_deviation)*2.3)
    overall=round(max(0,min(100,safety*.20+efficiency*.25+hazard_score*.20+cycle_score*.10+duration_score*.15+float(current_metrics.get('control_precision',65))*.10)),1)
    factors=list(adjusted['contributing_factors']);
    if cycle>float(benchmark.get('expected_cycle_time_max_sec',benchmark.get('cycle_max',160))): factors.append('slower cycle time')
    if efficiency<float(benchmark.get('minimum_efficiency_score',benchmark.get('efficiency',80))): factors.append('increased idle time / lower efficiency')
    if safety<float(benchmark.get('minimum_safety_score',benchmark.get('safety',95))): factors.append('safety below minimum')
    explanation=f"Expected under current conditions: {expected_min:.1f}–{expected_max:.1f} hours. Your normal: {personal_time:.1f} hours. Current: {duration:.1f} hours."
    if duration_status=='WITHIN_EXPECTATION' and personal_deviation>10: explanation+=' This is within the task benchmark but slower than your usual pattern.'
    elif duration_status!='WITHIN_EXPECTATION' and abs(personal_deviation)<=10: explanation+=' Task time is above the ideal benchmark, but consistent with your usual performance.'
    else: explanation+=f' Task time is {abs(benchmark_deviation):.0f}% {"above" if benchmark_deviation>0 else "below"} the context-adjusted expectation.'
    benchmark_checks={'duration':duration_status=='WITHIN_EXPECTATION','safety':safety>=float(benchmark.get('minimum_safety_score',benchmark.get('safety',95))),'efficiency':efficiency>=float(benchmark.get('minimum_efficiency_score',benchmark.get('efficiency',80))),'hazard_response':hazard<=hazard_limit}; benchmark_compliant=all(benchmark_checks.values())
    result={'benchmark':benchmark,'context_adjusted_benchmark':{**adjusted,'adjusted_min_duration':expected_min,'adjusted_max_duration':expected_max},'context_adjusted_range':{'min':expected_min,'max':expected_max,'context_factor':adjusted['context_factor'],'contributing_factors':adjusted['contributing_factors']},'personal_baseline':personal_baseline,'current_performance':{**current_metrics,'task_time_hours':round(duration,2)},'current_result':{**current_metrics,'task_time_hours':round(duration,2)},'duration_unit':'hours','benchmark_checks':benchmark_checks,'benchmark_compliant':benchmark_compliant,'benchmark_deviation':benchmark_deviation,'benchmark_deviation_pct':benchmark_deviation,'personal_deviation':personal_deviation,'personal_deviation_pct':personal_deviation,'overall_score':overall,'proficiency':calculate_proficiency({'performance':overall,'safety':safety,'efficiency':efficiency,'hazard_response':hazard_score,'consistency':duration_score,'calibration_gap':0}),'task_prediction':predict_task_time_context(benchmark,personal_baseline,context,efficiency,machine_state),'status':duration_status,'explanation':explanation,'contributing_factors':factors,'context_adjustment':adjusted['context_adjustment_hours']}
    result.update({'benchmarkStatus':duration_status,'contextAdjustedRange':result['context_adjusted_range'],'personalBaseline':personal_baseline,'currentPerformance':result['current_performance'],'benchmarkDeviationPct':benchmark_deviation,'personalDeviationPct':personal_deviation,'safetyScore':safety,'efficiencyScore':efficiency})
    return result

def ensure_demo_evaluation():
    benchmark=row('SELECT * FROM task_benchmarks WHERE scenario_id="SCN-PROX-01"')
    if not benchmark: return
    personal=get_personal_baseline('OP-001','SCN-PROX-01')
    context={'environment':{'ambient_temp_c':34,'humidity_pct':82,'ground_condition':'Hard','soil_type':'Rocky','payload_pct':68,'visibility':'Good'},'machine_state':{'status':'Operational','engine_temp_c':78}}
    evaluation=evaluate_task_performance({'task_id':'T-001','task_type':'Excavation — Trench Digging'}, {'task_time_hours':10.1,'cycle_time_sec':165,'safety':72,'efficiency':61,'hazard_response_sec':2.9,'hazard_response_score':54,'control_precision':65},benchmark,personal,context)
    adjusted=evaluation['context_adjusted_benchmark']; f=adjusted['factors']
    execute('INSERT OR REPLACE INTO context_evaluations(session_id,temperature_factor,ground_factor,load_factor,visibility_factor,total_context_factor,adjusted_min_duration,adjusted_max_duration,explanation) VALUES (?,?,?,?,?,?,?,?,?)',('WS-DEMO',f['temperature'],f['ground'],f['load'],f['visibility'],adjusted['context_factor'],adjusted['adjusted_min'],adjusted['adjusted_max'],'; '.join(adjusted['contributing_factors'])))
    execute('INSERT OR REPLACE INTO performance_evaluations(session_id,benchmark_deviation_pct,personal_deviation_pct,overall_score,status,explanation,created_at) VALUES (?,?,?,?,?,?,?)',('WS-DEMO',evaluation['benchmark_deviation_pct'],evaluation['personal_deviation_pct'],58,evaluation['status'],evaluation['explanation'],now()))

def seed():
    with conn() as c:
        c.executescript(SCHEMA)
        migrate_schema(c)
        if c.execute('SELECT COUNT(*) FROM operators').fetchone()[0]:
            # Bring legacy rows to the deterministic hackathon job contract.
            c.execute("UPDATE tasks SET weather='rainy', operator_skill='intermediate', machine_age_hours=2140, demo_seed=? WHERE task_id='T-002'",(DEMO_TASK_SEED,))
            c.execute("UPDATE tasks SET job_options_json=? WHERE task_id='T-002'",(json.dumps({'duration_min':45,'weather':'rainy','skill':'intermediate','machine_type':'CAT 320 Excavator'}),))
            ensure_reference_data(c); c.commit(); ensure_demo_evaluation(); return
        t=now(); ops=[('OP-001','Raghav Sharma',7,'Proficient','Site A'),('OP-002','Maya Patel',10,'Advanced','Site A'),('OP-003','Diego Morales',1,'Developing','Site B'),('OP-004','Asha Singh',8,'Proficient','Site A'),('OP-005','Noah Williams',4,'Proficient','Site B')]
        for i in range(6,21): ops.append((f'OP-{i:03d}',f'Operator {i}',random.Random(42+i).randint(1,12),'Developing','Site A' if i%2 else 'Site B'))
        c.executemany('INSERT INTO operators VALUES (?,?,?,?,?,?)',[(a,b,c,d,e,t) for a,b,c,d,e in ops])
        machines=[('M-320','CAT 320 Excavator','Excavator','EXCAVATION_LOAD','Operational',2140,62),('M-323','CAT 323 Excavator','Excavator','EXCAVATION_LOAD','Operational',1850,71),('M-950','CAT 950 Wheel Loader','Wheel Loader','EXCAVATION_LOAD','Operational',3320,54),('M-BHL','Backhoe Loader','Backhoe Loader','EXCAVATION_LOAD','Maintenance',4100,43),('M-777','CAT 777 Off-Highway Truck','Haul Truck','HAUL_TRANSPORT','Operational',5120,66),('M-AH','Articulated Hauler','Hauler','HAUL_TRANSPORT','Operational',2980,59),('M-777B','CAT 777 Haul Truck','Haul Truck','HAUL_TRANSPORT','Operational',6210,48),('M-950B','CAT 950 Loader','Wheel Loader','EXCAVATION_LOAD','Operational',2400,76)]
        c.executemany('INSERT INTO machines VALUES (?,?,?,?,?,?,?,?)',[(a,b,d,e,f,h,i,t) for a,b,d,e,f,h,i in machines])
        c.executemany('INSERT INTO machine_domains VALUES (?,?,?, ?,?)',[('EXCAVATION_LOAD','Excavation / Loading',json.dumps(['ACQUIRE','LIFT','SWING','DUMP','RETURN']),json.dumps(['cycle_time','phase_duration','control_precision','idle_time','hazard_response','load_handling','safety_behavior']),t),('HAUL_TRANSPORT','Haul / Transport',json.dumps(['LOAD','TRAVEL_LOADED','QUEUE_SPOT','DUMP','TRAVEL_EMPTY','RETURN']),json.dumps(['cycle_time','queue_time','reaction_latency','loaded_travel','unloaded_travel','stop_response','efficiency']),t)])
        scenarios=[('SCN-PROX-01','Proximity Hazard Response','EXCAVATION_LOAD','CAT 320 Excavator','Intermediate',15,'hazard_response','proximity','React safely when a person enters the work zone.',{'hazard_response':2.0,'cycle_time':140,'efficiency':88,'safety':94}),('SCN-EFF-01','Efficient Excavation','EXCAVATION_LOAD','CAT 320 Excavator','Intermediate',20,'cycle_efficiency','none','Build a smooth acquire, lift, swing, dump, return cycle.',{'hazard_response':2.1,'cycle_time':140,'efficiency':88,'safety':94}),('SCN-LOAD-01','High-Load Operation','EXCAVATION_LOAD','CAT 950 Wheel Loader','Advanced',18,'load_handling','payload','Manage a high-load cycle with precision.',{'hazard_response':2.2,'cycle_time':155,'efficiency':82,'safety':92}),('SCN-NIGHT-01','Night Operation Awareness','HAUL_TRANSPORT','CAT 777 Off-Highway Truck','Intermediate',15,'situational_awareness','visibility','Maintain awareness in low visibility.',{'hazard_response':2.0,'cycle_time':180,'efficiency':80,'safety':93}),('SCN-BUCKET-01','Bucket Control','EXCAVATION_LOAD','CAT 320 Excavator','Beginner',12,'control_precision','none','Practice smooth bucket control.',{'hazard_response':2.4,'cycle_time':150,'efficiency':80,'safety':95}),('SCN-HAUL-01','Haul-Site Awareness','HAUL_TRANSPORT','CAT 777 Off-Highway Truck','Advanced',22,'hazard_response','proximity','Respond to stop signals and haul-site hazards.',{'hazard_response':2.0,'cycle_time':180,'efficiency':84,'safety':94})]
        # add 24 lightweight scenarios as requested
        for i in range(7,31): scenarios.append((f'SCN-{i:02d}',f'Adaptive Practice {i}','EXCAVATION_LOAD' if i%2 else 'HAUL_TRANSPORT','CAT 320 Excavator' if i%2 else 'CAT 777 Off-Highway Truck','Beginner' if i%3 else 'Advanced',10+i%12,'efficiency' if i%2 else 'situational_awareness','none','Personalized practice scenario.',{'cycle_time':140,'efficiency':80,'safety':90}))
        c.executemany('INSERT INTO training_scenarios VALUES (?,?,?,?,?,?,?,?,?,?)',[(a,b,c,d,e,f,g,h,i,json.dumps(j)) for a,b,c,d,e,f,g,h,i,j in scenarios])
        taskdefs=[('T-001','M-320','EXCAVATION_LOAD','Excavation — Trench Digging','Site A — North Zone','08:00','08:45','In Progress',45),('T-002','M-320','EXCAVATION_LOAD','Excavation — Trench Digging','Site A — Rain Trench','10:00','10:45','Upcoming',45),('T-003','M-777','HAUL_TRANSPORT','Haul Cycle','Site B — Haul Road','11:00','12:00','Upcoming',60),('T-004','M-320','EXCAVATION_LOAD','Mid-Shift Check','Site A — Maintenance Point','13:00','13:30','Upcoming',30),('T-005','M-320','EXCAVATION_LOAD','End-of-Shift Reflection','On-site / App','16:00','16:30','Upcoming',30)]
        for i in range(6,156):
            op=f'OP-{(i%20)+1:03d}'; mach=['M-320','M-950','M-777'][i%3]; typ=['Excavation — Trench Digging','Material Loading','Haul Cycle'][i%3]
            taskdefs.append((f'T-{i:03d}',mach,'HAUL_TRANSPORT' if mach=='M-777' else 'EXCAVATION_LOAD',typ,'Site A' if i%2 else 'Site B','08:00','09:00','Completed' if i%4 else 'Upcoming',45 if mach=='M-320' else 60))
        c.executemany('INSERT INTO tasks(task_id,operator_id,machine_id,domain,task_type,site,scheduled_start,scheduled_end,status,baseline_duration_min) VALUES (?,?,?,?,?,?,?,?,?,?)',[(a,'OP-001' if a in ('T-001','T-002','T-003','T-004','T-005') else f'OP-{(int(a.split("-")[1])%20)+1:03d}',*b) for a,*b in taskdefs])
        c.execute("UPDATE tasks SET weather='rainy', operator_skill='intermediate', machine_age_hours=2140, demo_seed=? WHERE task_id='T-002'",(DEMO_TASK_SEED,))
        c.execute("UPDATE tasks SET job_options_json=? WHERE task_id='T-002'",(json.dumps({'duration_min':45,'weather':'rainy','skill':'intermediate','machine_type':'CAT 320 Excavator'}),))
        # Personal demo baseline and 200 seeded runs
        base=[('OP-001','SCN-PROX-01','hazard_response',2.0,5),('OP-001','SCN-PROX-01','cycle_time',140,5),('OP-001','SCN-PROX-01','efficiency',88,5),('OP-001','SCN-PROX-01','safety',94,5)]
        c.executemany('INSERT INTO operator_baselines(operator_id,scenario_id,metric_name,metric_value,sample_count,updated_at) VALUES (?,?,?,?,?,?)',[(a,b,d,e,f,t) for a,b,d,e,f in base])
        rng=random.Random(42)
        for i in range(200):
            op=f'OP-{(i%20)+1:03d}'; sid=scenarios[i%len(scenarios)][0]; skill=82 if op in ('OP-001','OP-004') else 61 if op=='OP-002' else 68+rng.random()*18
            hr=round(1.7+(100-skill)/35+rng.random()*.5,2); eff=round(skill+rng.uniform(-5,5),1); saf=round(min(99,skill+10+rng.uniform(-3,3)),1); score=round((eff+saf+(100-min(100,hr*25)))/3,1)
            c.execute('INSERT INTO training_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(f'TR-{i:04d}',op,sid,t,t,score,140+int((100-eff)*1.2),hr,skill,eff,saf,1 if score>=60 else 0))
        # Work history, including a current demo session with objective 58
        c.execute('INSERT INTO work_sessions(session_id,operator_id,machine_id,task_id,started_at,ended_at,predicted_time_min,actual_time_min,overall_score,safety_score,efficiency_score,status,data_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',('WS-DEMO','OP-001','M-320','T-001',t,t,9.7,606,58,72,61,'Completed',json.dumps({'hazard_response':2.9,'cycle_time':165,'context_stress':31,'task_time_hours':10.1})))
        c.execute('INSERT INTO performance_scores(session_id,control_precision,cycle_efficiency,safety,situational_awareness,hazard_response,overall_score) VALUES (?,?,?,?,?,?,?)',('WS-DEMO',65,61,72,70,54,58))
        c.execute('INSERT INTO hazard_events VALUES (?,?,?,?,?,?,?,?,?,?,?)',('HZ-DEMO','WS-DEMO','proximity','high',t,t,2.9,1,0,0,1))
        c.execute('INSERT INTO calibration_results(session_id,objective_score,self_confidence,calibration_gap,state,explanation) VALUES (?,?,?,?,?,?)',('WS-DEMO',58,87,29,'BLIND_SPOT','Objective performance was below baseline while self-confidence was high.'))
        c.execute('INSERT INTO reflections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',('RF-DEMO','WS-DEMO','OP-001','I think the task went smoothly. I noticed the nearby person and reacted quickly. I felt confident operating the machine.',87,85,30,90,'High confidence and hazard awareness reported; objective evidence suggests a slower response.',t,'["confidence"]','[]','["nearby person"]'))
        c.execute('INSERT INTO recommendations(operator_id,scenario_id,reason,target_skill,priority,created_at) VALUES (?,?,?,?,?,?)',('OP-001','SCN-PROX-01','Your response to proximity hazards was slower than your trained baseline, while your self-assessment indicated high confidence.','hazard_response',1,t))
        # A compact, correlated history makes Reports meaningful offline: 150 sessions, 22,500 sensor events, 150 hazards and reflections.
        phases=['ACQUIRE','LIFT','SWING','DUMP','RETURN']
        for i in range(1,151):
            sid=f'WS-{i:03d}'; op=f'OP-{(i%20)+1:03d}'; mid=['M-320','M-950','M-777'][i%3]; tid=f'T-{(i%150)+1:03d}'; eff=round(62+rng.random()*30,1); saf=round(min(98,72+rng.random()*24),1); actual_minutes=round(42+10*(100-eff)/100,1)
            if op=='OP-002' and i==1: eff,saf,actual_minutes=42.0,58.0,1440.0
            overall=round(eff*.55+saf*.45,1)
            c.execute('INSERT INTO work_sessions(session_id,operator_id,machine_id,task_id,started_at,ended_at,predicted_time_min,actual_time_min,overall_score,safety_score,efficiency_score,status,data_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(sid,op,mid,tid,t,t,45,actual_minutes,overall,saf,eff,'Completed',json.dumps({'context_stress':round(18+rng.random()*32,1),'task_time_hours':actual_minutes/60})))
            c.execute('INSERT INTO performance_scores(session_id,control_precision,cycle_efficiency,safety,situational_awareness,hazard_response,overall_score) VALUES (?,?,?,?,?,?,?)',(sid,eff,saf, saf, round(60+rng.random()*35,1),round(50+rng.random()*45,1),overall))
            hz=f'HZ-{i:03d}'; response=round(1.7+(100-eff)/35+rng.random()*.6,2); c.execute('INSERT INTO hazard_events VALUES (?,?,?,?,?,?,?,?,?,?,?)',(hz,sid,'proximity','high',t,t,response,1,0,1 if response>3 else 0,1))
            c.execute('INSERT INTO reflections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'RF-{i:03d}',sid,op,'The task went well and I felt confident. I noticed the person nearby.',round(62+rng.random()*30,1),round(65+rng.random()*28,1),round(20+rng.random()*50,1),round(70+rng.random()*25,1),'Synthetic reflection for demonstration mode.',t,'["steady operation"]','[]','["nearby person"]'))
            for j in range(150):
                phase=phases[j%5]; ambient=32+math.sin(j/10)+rng.random()*2; load=45+(25 if phase in ('LIFT','SWING') else 0)+rng.random()*8; prox=12 if j%30<25 else round(5+rng.random()*3,1); c.execute('INSERT INTO sensor_events(session_id,timestamp,ambient_temp_c,humidity_pct,wind_speed_kmh,fuel_level_pct,fuel_rate_lph,engine_rpm,engine_temp_c,hydraulic_load_pct,payload_pct,seatbelt_fastened,proximity_distance_m,visibility,soil_type,ground_condition,cycle_phase,gps_x,gps_y) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(sid,t,ambient,58,12,62-j*.02,18+load*.06,1400+int(load*2),76+(ambient-30)*.5+load*.04,load,65 if phase in ('LIFT','SWING') else 20,1,prox,'Good','Medium (Sandy)','Dry',phase,42+j*.01,18+j*.005))
            for j,phase in enumerate(phases): c.execute('INSERT INTO machine_cycles(session_id,cycle_number,phase,start_time,end_time,duration_sec) VALUES (?,?,?,?,?,?)',(sid,j+1,phase,t,t,round(25+rng.random()*12,1)))
        ensure_reference_data(c)
        # Persist the benchmark and personal reference layers alongside the seeded evidence.
        c.commit()
    ensure_demo_evaluation()

@app.on_event('startup')
def startup(): seed()
# Make the demo immediately usable with uvicorn, TestClient, or a simple Python import.
seed()

class ReflectionIn(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
class RunIn(BaseModel): operator_id: str='OP-001'; scenario_id: str='SCN-PROX-01'
class SessionIn(BaseModel): operator_id: str='OP-001'; machine_id: str='M-320'; task_id: str='T-001'
class IncidentIn(BaseModel):
    job_id: str | None = None
    session_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    type: str | None = Field(default=None, min_length=1, max_length=64)
    severity: str = 'medium'
    timestamp: str | None = None
    resolution: str = ''
class ReviewIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=MAX_TRANSCRIPT_CHARS)
    actual_minutes: float | None = None
    telemetry_summary: dict = Field(default_factory=dict)
class SimAttemptIn(BaseModel):
    module_id: str
    score: float = Field(ge=0, le=100)
    duration_sec: float = Field(default=0, ge=0)
    passed: bool | None = None
    penalties: int = Field(default=0, ge=0)
    objectives: dict = Field(default_factory=dict)
class PerformanceEvaluateIn(BaseModel):
    session_id: str
    current_metrics: dict = {}
    context: dict = {}
    scenario_id: str = 'SCN-PROX-01'
    operator_id: str = 'OP-001'
class TrainingEventIn(BaseModel):
    timestamp: str | None = None
    control_type: str
    control_duration_sec: float = 0.5
    cycle_phase: str = 'ACQUIRE'
    hazard_time_sec: float | None = None
    operator_response_time_sec: float | None = None
    unnecessary_action: bool = False
    payload: dict = Field(default_factory=dict)

def canonical_task_id(task_id):
    return 'T-002' if task_id == DEMO_TASK_ID else task_id

def public_task(task_row, api_shape=False):
    if not task_row: return None
    item=dict(task_row)
    if item.get('task_id')=='T-002':
        item['job_id']=DEMO_TASK_ID
        item['demo_seed']=item.get('demo_seed') or DEMO_TASK_SEED
        item['job_options']=json.loads(item.get('job_options_json') or '{}')
    else:
        item['job_id']=item.get('task_id')
        item['job_options']=json.loads(item.get('job_options_json') or '{}')
    item['weather']=item.get('weather') or 'clear'
    item['operator_skill']=item.get('operator_skill') or 'intermediate'
    item['machine_age_hours']=item.get('machine_age_hours') or 0
    if api_shape:
        if item.get('task_id')=='T-002': item['legacy_task_id']='T-002'; item['task_id']=DEMO_TASK_ID
        item['id']=item['job_id']
        item['predicted_minutes']=predict_minutes(item)
    return item

def predict_minutes(task_row):
    task_row=task_row or {}
    base=float(task_row.get('baseline_duration_min') or 45)
    task_type=str(task_row.get('task_type','')).lower()
    if 'haul' in task_type: base=max(base,60)
    elif 'load' in task_type: base=max(base,40)
    weather=str(task_row.get('weather','clear')).lower()
    weather_factor={'rainy':1.16,'wet':1.16,'foggy':1.12,'windy':1.08,'hot':1.08}.get(weather,1.0)
    skill=str(task_row.get('operator_skill','intermediate')).lower()
    skill_factor={'beginner':1.18,'developing':1.10,'intermediate':1.0,'proficient':.95,'advanced':.9}.get(skill,1.0)
    age=float(task_row.get('machine_age_hours') or 0)
    age_factor=1+max(0,min(.15,(age-1500)/12000)) if age else 1.0
    value=round(base*weather_factor*skill_factor*age_factor,1)
    spread=max(3.0,round(value*.10,1))
    return {'predicted_minutes':value,'range_min_minutes':round(max(1,value-spread),1),'range_max_minutes':round(value+spread,1),'confidence':round(max(55,95-(weather_factor-1)*100-(skill_factor-1)*35-(age_factor-1)*50),0),'factors':[x for x,y in [('weather',weather_factor),('operator skill',skill_factor),('machine age',age_factor)] if abs(y-1)>.015] or ['normal conditions'],'unit':'minutes'}

def scenario_id_for_session(session_id, requested=None):
    if requested: return requested
    s=work_session(session_id)
    task_type=str(s.get('task_type','')) if s else ''
    if 'Haul' in task_type: return 'SCN-HAUL-01'
    if 'Load' in task_type: return 'SCN-LOAD-01'
    return 'SCN-PROX-01'

def context_for_session(session_id):
    session=row('SELECT task_id FROM work_sessions WHERE session_id=?',(session_id,)) or {}
    if session_id=='WS-DEMO' or session.get('task_id')=='T-002':
        return {'environment':{'ambient_temp_c':34,'humidity_pct':82,'wind_speed_kmh':12,'payload_pct':68,'visibility':'Good','soil_type':'Rocky','ground_condition':'Hard'},'machine_state':{'status':'Operational','engine_temp_c':78}}
    event=row('SELECT * FROM sensor_events WHERE session_id=? ORDER BY event_id DESC',(session_id,))
    if event:
        return {'environment':event,'machine_state':{'status':'Operational','engine_temp_c':event.get('engine_temp_c',78)}}
    return {'environment':{'ambient_temp_c':34,'humidity_pct':58,'payload_pct':68,'visibility':'Good','ground_condition':'Dry'},'machine_state':{'status':'Operational','engine_temp_c':78}}

def evaluate_session(session_id, current_metrics=None, context=None, requested_scenario=None, requested_operator=None):
    s=work_session(session_id)
    if not s: raise HTTPException(404,'Session not found')
    sid=scenario_id_for_session(session_id,requested_scenario); benchmark=row('SELECT * FROM task_benchmarks WHERE scenario_id=?',(sid,)) or row('SELECT * FROM task_benchmarks WHERE scenario_id="SCN-PROX-01"'); personal=get_personal_baseline(requested_operator or s['operator_id'],sid); score=row('SELECT * FROM performance_scores WHERE session_id=?',(session_id,)) or {}
    demo_session=session_id=='WS-DEMO' or s.get('task_id')=='T-002'
    metrics=current_metrics or ({'task_time_hours':10.1,'cycle_time_sec':165,'safety':72,'efficiency':61,'hazard_response_sec':2.9,'hazard_response_score':54,'control_precision':65} if demo_session else {'task_time_hours':round(float(s.get('actual_time_min') or 606)/60,2),'cycle_time_sec':float(score.get('cycle_efficiency',140) or 140)+20,'safety':float(score.get('safety',80) or 80),'efficiency':float(score.get('cycle_efficiency',70) or 70),'hazard_response_sec':2.9,'hazard_response_score':float(score.get('hazard_response',54) or 54),'control_precision':float(score.get('control_precision',65) or 65)})
    evaluation=evaluate_task_performance(s,metrics,benchmark,personal,context or context_for_session(session_id)); adjusted=evaluation['context_adjusted_benchmark']; f=adjusted['factors']; total_score=58 if demo_session else evaluation['overall_score']
    execute('INSERT OR REPLACE INTO context_evaluations(session_id,temperature_factor,ground_factor,load_factor,visibility_factor,total_context_factor,adjusted_min_duration,adjusted_max_duration,explanation) VALUES (?,?,?,?,?,?,?,?,?)',(session_id,f['temperature'],f['ground'],f['load'],f['visibility'],adjusted['context_factor'],adjusted['adjusted_min'],adjusted['adjusted_max'],'; '.join(adjusted['contributing_factors'])))
    execute('INSERT OR REPLACE INTO performance_evaluations(session_id,benchmark_deviation_pct,personal_deviation_pct,overall_score,status,explanation,created_at) VALUES (?,?,?,?,?,?,?)',(session_id,evaluation['benchmark_deviation_pct'],evaluation['personal_deviation_pct'],total_score,evaluation['status'],evaluation['explanation'],now()))
    evaluation['overall_score']=total_score; evaluation['session_id']=session_id; evaluation['scenario_id']=sid; evaluation['benchmark_status']=evaluation['status']; return evaluation

@app.get('/health')
def health(): return {'status':'ok','product':'Smart Operator Companion'}
@app.post('/auth/demo-login')
def login(): return {'token':'demo','operator':row('SELECT * FROM operators WHERE operator_id="OP-001"')}
@app.get('/auth/me')
def me(): return row('SELECT * FROM operators WHERE operator_id="OP-001"')
@app.get('/operators')
def operators(): return rows('SELECT * FROM operators')
@app.get('/operators/{id}')
def operator(id:str): return row('SELECT * FROM operators WHERE operator_id=?',(id,)) or (_ for _ in ()).throw(HTTPException(404,'Operator not found'))
@app.get('/operators/{id}/summary')
def op_summary(id:str):
    p=row('SELECT * FROM performance_scores WHERE session_id="WS-DEMO"') or {}; c=row('SELECT * FROM calibration_results ORDER BY calibration_id DESC') or {}
    evaluation=evaluate_session('WS-DEMO') if id=='OP-001' else None; live=latest_telemetry('WS-DEMO'); machine_data=machine('M-320'); task_data=rows('SELECT status,COUNT(*) AS count FROM tasks WHERE operator_id=? GROUP BY status',(id,))
    current=evaluation.get('current_performance',{}) if evaluation else {}; latest_cal=row('SELECT * FROM calibration_results c LEFT JOIN work_sessions w ON w.session_id=c.session_id WHERE w.operator_id=? ORDER BY c.calibration_id DESC',(id,)); overall=float(evaluation.get('overall_score',0)) if evaluation else float(p.get('overall_score',0) or 0)
    return {'operator':operator(id),'overall_score':overall,'safety':float(current.get('safety',p.get('safety',0)) or 0),'efficiency':float(current.get('efficiency',p.get('cycle_efficiency',0)) or 0),'situational_awareness':float(current.get('situational_awareness',p.get('situational_awareness',0)) or 0),'confidence_calibration':float(latest_cal.get('calibration_gap',0) if latest_cal else 0),'proficiency':evaluation.get('proficiency') if evaluation else None,'latest_evaluation':evaluation,'current_machine':{**machine_data,'telemetry':live},'site_conditions':{'ambient_temp_c':live['ambient_temp_c'],'humidity_pct':live['humidity_pct'],'wind_speed_kmh':live['wind_speed_kmh'],'visibility':live['visibility'],'soil_type':live['soil_type'],'ground_condition':live['ground_condition']},'task_progress':task_data}
@app.get('/machine-domains')
def machine_domains(): return [{'domain':x['domain'],'name':x['name'],'phases':json.loads(x['phases']),'primary_metrics':json.loads(x['primary_metrics'])} for x in rows('SELECT * FROM machine_domains ORDER BY domain')]
@app.get('/machines')
def machines(): return rows('SELECT * FROM machines ORDER BY machine_id')
@app.get('/machines/{id}')
def machine(id:str): return row('SELECT * FROM machines WHERE machine_id=?',(id,)) or (_ for _ in ()).throw(HTTPException(404,'Machine not found'))
@app.get('/machines/{id}/telemetry')
def machine_telemetry(id:str): return {'machine':machine(id),'telemetry':latest_telemetry('WS-DEMO')}
@app.get('/tasks')
def tasks(operator_id='OP-001'):
    raw=rows('SELECT t.*,m.model AS machine_model FROM tasks t LEFT JOIN machines m ON m.machine_id=t.machine_id WHERE operator_id=? ORDER BY CASE WHEN t.task_id="T-002" THEN 0 ELSE 1 END, scheduled_start',(operator_id,))
    return [public_task(item,True) for item in raw]
@app.get('/tasks/today')
def tasks_today(): return tasks()
@app.get('/tasks/{id}')
def task(id:str):
    id=canonical_task_id(id)
    return row('SELECT t.*,m.model AS machine_model FROM tasks t LEFT JOIN machines m ON m.machine_id=t.machine_id WHERE task_id=?',(id,)) or (_ for _ in ()).throw(HTTPException(404,'Task not found'))
@app.post('/tasks/{id}/start')
def task_start(id:str): id=canonical_task_id(id); execute('UPDATE tasks SET status="In Progress" WHERE task_id=?',(id,)); return task(id)
@app.post('/tasks/{id}/complete')
def task_complete(id:str): id=canonical_task_id(id); execute('UPDATE tasks SET status="Completed" WHERE task_id=?',(id,)); return task(id)
@app.get('/tasks/{id}/prediction')
def task_prediction(id:str):
    requested=id; t=task(id); sid='SCN-HAUL-01' if 'Haul' in t['task_type'] else 'SCN-LOAD-01' if 'Load' in t['task_type'] else 'SCN-PROX-01'; b=benchmark(sid); p=get_personal_baseline(t['operator_id'],sid); context=context_for_session('WS-DEMO'); minute_prediction=predict_minutes(t); hour_prediction=predict_task_time_context(b,p,context,82.0,{'status':'Operational'}); return {'task_id':requested,**minute_prediction,'predicted_time':hour_prediction['predicted_time'],'predicted_time_min':hour_prediction['predicted_time_min'],'predicted_time_max':hour_prediction['predicted_time_max'],'hours':hour_prediction}
@app.get('/training/scenarios')
def scenarios():
    result=[]
    for x in rows('SELECT * FROM training_scenarios'):
        x['baseline_metrics']=json.loads(x['baseline_metrics']); x['benchmark']=row('SELECT * FROM task_benchmarks WHERE scenario_id=?',(x['scenario_id'],)); result.append(x)
    return result
@app.get('/training/scenarios/recommended')
def recommended(operator_id='OP-001'): return recommendation(operator_id)
@app.get('/training/scenarios/{id}')
def scenario(id:str):
    x=row('SELECT * FROM training_scenarios WHERE scenario_id=?',(id,));
    if not x: raise HTTPException(404,'Scenario not found')
    x['baseline_metrics']=json.loads(x['baseline_metrics']); x['benchmark']=row('SELECT * FROM task_benchmarks WHERE scenario_id=?',(id,)); return x
@app.post('/training/runs')
def training_start(x:RunIn): return {'run_id':f'TRAIN-{int(datetime.now().timestamp())}','operator_id':x.operator_id,'scenario_id':x.scenario_id,'started_at':now(),'status':'In Progress'}
@app.post('/training/runs/{id}/events')
def training_event(id:str, event:TrainingEventIn):
    execute('INSERT INTO training_events(run_id,timestamp,control_type,control_duration_sec,cycle_phase,hazard_time_sec,operator_response_time_sec,unnecessary_action,payload) VALUES (?,?,?,?,?,?,?,?,?)',(id,event.timestamp or now(),event.control_type,event.control_duration_sec,event.cycle_phase,event.hazard_time_sec,event.operator_response_time_sec,int(event.unnecessary_action),json.dumps(event.payload)))
    return {'run_id':id,'recorded':True}
@app.post('/training/runs/{id}/complete')
def training_complete(id:str, x:dict={}):
    scenario_id=x.get('scenario_id','SCN-PROX-01'); op=x.get('operator_id','OP-001'); events=x.get('control_events',[]) or []; score=float(x.get('score',84)); hr=float(x.get('hazard_response_sec',2.1)); eff=float(x.get('efficiency_score',82)); saf=float(x.get('safety_score',92));
    for event in events:
        if isinstance(event,dict): training_event(id,TrainingEventIn(**event))
    execute('INSERT INTO training_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(id,op,scenario_id,now(),now(),score,140,hr,eff,eff,saf,1))
    for metric,val in [('hazard_response',hr),('cycle_time',140),('efficiency',eff),('safety',saf)]:
        old=row('SELECT * FROM operator_baselines WHERE operator_id=? AND scenario_id=? AND metric_name=?',(op,scenario_id,metric))
        if old: execute('UPDATE operator_baselines SET metric_value=?,sample_count=?,updated_at=? WHERE baseline_id=?',((old['metric_value']*old['sample_count']+val)/(old['sample_count']+1),old['sample_count']+1,now(),old['baseline_id']))
        else: execute('INSERT INTO operator_baselines(operator_id,scenario_id,metric_name,metric_value,sample_count,updated_at) VALUES (?,?,?,?,?,?)',(op,scenario_id,metric,val,1,now()))
    personal=get_personal_baseline(op,scenario_id); existing_personal=row('SELECT * FROM personal_operator_baselines WHERE operator_id=? AND scenario_id=?',(op,scenario_id)); n=int(personal.get('sample_count') or 0); nn=n+1
    values=((personal['average_cycle_time_sec']*n+140)/nn,(personal['average_hazard_response_sec']*n+hr)/nn,(personal['average_efficiency']*n+eff)/nn,(personal['average_safety']*n+saf)/nn,(personal['average_control_precision']*n+eff)/nn,(personal['consistency_score']*n+score)/nn,nn,now())
    if existing_personal: execute('UPDATE personal_operator_baselines SET average_cycle_time_sec=?,average_hazard_response_sec=?,average_efficiency=?,average_safety=?,average_control_precision=?,consistency_score=?,sample_count=?,updated_at=? WHERE operator_id=? AND scenario_id=?',(*values,op,scenario_id))
    else: execute('INSERT INTO personal_operator_baselines(operator_id,scenario_id,average_task_time_hours,average_cycle_time_sec,average_hazard_response_sec,average_efficiency,average_safety,average_control_precision,consistency_score,sample_count,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(op,scenario_id,personal['average_task_time_hours'],*values))
    return {'run_id':id,'passed':True,'baseline_updated':True,'score':score,'events_recorded':len(events),'metrics':{'hazard_response':hr,'cycle_time':140,'efficiency':eff,'safety':saf,'control_precision':eff}}
@app.post('/sessions/train/start')
def workflow_train_start(x:RunIn): return training_start(x)
@app.post('/sessions/train/{id}/complete')
def workflow_train_complete(id:str, x:dict={}): return training_complete(id,x)
@app.get('/baselines/{operator_id}')
def baselines(operator_id:str): return rows('SELECT * FROM operator_baselines WHERE operator_id=?',(operator_id,))
@app.get('/baselines/{operator_id}/{scenario_id}')
def baseline(operator_id:str,scenario_id:str): return rows('SELECT * FROM operator_baselines WHERE operator_id=? AND scenario_id=?',(operator_id,scenario_id))
@app.get('/benchmarks')
def benchmarks(): return rows('SELECT * FROM task_benchmarks ORDER BY task_type')

# Frozen contract aliases from the build plan. The original routes remain for
# backwards compatibility with the existing dashboard.
@app.get('/api/benchmarks')
def api_benchmarks(): return benchmarks()
@app.get('/api/benchmarks/{scenario_id}')
def api_benchmark(scenario_id:str): return benchmark(scenario_id)
@app.post('/api/performance/evaluate')
def api_performance_evaluate(x:PerformanceEvaluateIn): return evaluate_session(x.session_id,x.current_metrics or None,x.context or None,x.scenario_id,x.operator_id)
@app.get('/api/performance/{operator_id}/comparison')
def api_performance_comparison(operator_id:str): return benchmark_comparison(operator_id)
@app.get('/api/performance/{operator_id}')
def api_performance_summary(operator_id:str): return op_summary(operator_id)
@app.get('/api/calibration/{operator_id}')
def api_calibration(operator_id:str): return performance_calibration(operator_id)
@app.get('/api/recommendations/{operator_id}')
def api_recommendations(operator_id:str): return recommendation(operator_id)

@app.get('/api/tasks')
def api_tasks(request:Request, date:str|None=None):
    if date:
        try: datetime.strptime(date,'%Y-%m-%d')
        except ValueError: return api_error(400,'invalid_date','date must be YYYY-MM-DD')
    operator_id=operator_from_request(request)
    return {'date':date or datetime.utcnow().strftime('%Y-%m-%d'),'operator_id':operator_id,'tasks':[public_task(x,True) for x in rows('SELECT t.*,m.model AS machine_model FROM tasks t LEFT JOIN machines m ON m.machine_id=t.machine_id WHERE operator_id=? ORDER BY CASE WHEN t.task_id="T-002" THEN 0 ELSE 1 END, scheduled_start',(operator_id,))]}
@app.get('/benchmarks/{scenario_id}')
def benchmark(scenario_id:str): return row('SELECT * FROM task_benchmarks WHERE scenario_id=?',(scenario_id,)) or (_ for _ in ()).throw(HTTPException(404,'Benchmark not found'))
@app.post('/performance/evaluate')
def performance_evaluate(x:PerformanceEvaluateIn): return evaluate_session(x.session_id,x.current_metrics or None,x.context or None,x.scenario_id,x.operator_id)
@app.get('/performance/evaluate/{session_id}')
def performance_evaluate_get(session_id:str): return evaluate_session(session_id)
@app.get('/performance/{operator_id}/benchmark-comparison')
def benchmark_comparison(operator_id:str):
    if operator_id=='OP-001': evaluate_session('WS-DEMO')
    data=rows('SELECT p.*,w.operator_id,w.task_id,w.actual_time_min,t.task_type FROM performance_evaluations p JOIN work_sessions w ON w.session_id=p.session_id LEFT JOIN tasks t ON t.task_id=w.task_id WHERE w.operator_id=? ORDER BY p.created_at DESC',(operator_id,))
    return {'operator_id':operator_id,'comparisons':data,'benchmark_compliant':sum(1 for x in data if x['status']=='WITHIN_EXPECTATION'),'review_required':sum(1 for x in data if x['status']!='WITHIN_EXPECTATION')}
@app.get('/performance/{operator_id}/personal-baseline')
def personal_baseline_api(operator_id:str,scenario_id='SCN-PROX-01'): return get_personal_baseline(operator_id,scenario_id)
@app.get('/work/sessions')
def work_sessions(operator_id='OP-001'): return rows('SELECT * FROM work_sessions WHERE operator_id=? ORDER BY started_at DESC',(operator_id,))
@app.post('/work/sessions')
def create_session(x:SessionIn):
    task_id=canonical_task_id(x.task_id); sid=f'WS-{int(datetime.now().timestamp()*1000)}-{random.randint(100,999)}'; task_row=row('SELECT * FROM tasks WHERE task_id=?',(task_id,))
    if not task_row: raise HTTPException(404,'Task not found')
    execute('INSERT INTO work_sessions(session_id,operator_id,machine_id,task_id,status,telemetry_seed,job_options_json) VALUES (?,?,?,?,?,?,?)',(sid,x.operator_id,x.machine_id,task_id,'Ready',seed_for_task(task_row),task_row.get('job_options_json') or '{}')); return work_session(sid)
@app.post('/work/sessions/{id}/start')
def work_start(id:str):
    session=work_session(id); execute('UPDATE work_sessions SET started_at=?,status="In Progress" WHERE session_id=?',(now(),id));
    if session.get('task_id'): execute('UPDATE tasks SET status="In Progress" WHERE task_id=?',(session['task_id'],))
    return work_session(id)
@app.get('/work/sessions/{id}')
def work_session(id:str): return row('SELECT w.*,m.model,t.task_type FROM work_sessions w LEFT JOIN machines m ON m.machine_id=w.machine_id LEFT JOIN tasks t ON t.task_id=w.task_id WHERE session_id=?',(id,)) or (_ for _ in ()).throw(HTTPException(404,'Session not found'))
def telemetry_value(session_id, tick):
    session=row('SELECT telemetry_seed,machine_id,operator_id,job_options_json FROM work_sessions WHERE session_id=?',(session_id,)) or {}
    seed=int(session.get('telemetry_seed') or (DEMO_TASK_SEED if session_id=='WS-DEMO' else 0)); demo=seed==DEMO_TASK_SEED
    phase=['ACQUIRE','LIFT','SWING','DUMP','RETURN'][tick%5]; ambient=34+math.sin((tick+seed%7)/10)*1.4; load=52+18*(phase in ('LIFT','SWING'))+math.sin(tick/4)*3; temp=76+(ambient-30)*.55+load*.045
    proximity=12 if (tick+seed)%18 not in (14,15,16) else max(4,12-4*((tick+seed)%3)); responding=(tick+seed)%18 in (17,0)
    proximity=proximity+5 if responding else proximity; seatbelt=not (demo and tick%40 in (8,9,10)); tilt=round(2+math.sin(tick/5)*1.2+(5 if demo and tick%55 in (30,31) else 0),1); weather='rainy' if demo else 'clear'; visibility='reduced' if demo and tick%60 in (30,31,32) else 'Good'
    return {'timestamp':now(),'machine_id':session.get('machine_id') or 'M-320','operator_id':session.get('operator_id') or 'OP-001','ambient_temp_c':round(ambient,1),'humidity_pct':82 if demo else 58,'wind_speed_kmh':18 if demo else 12,'fuel_level_pct':round(max(0,62-tick*.03),1),'fuel_rate_lph':round(18+load*.06,1),'engine_rpm':1450+int(load*2),'engine_temp_c':round(temp,1),'hydraulic_load_pct':round(load,1),'payload_pct':68 if phase in ('LIFT','SWING') else 20,'seatbelt_fastened':seatbelt,'proximity_distance_m':proximity,'tilt_deg':tilt,'weather':weather,'visibility':visibility,'soil_type':'Rocky' if demo else 'Medium (Sandy)','ground_condition':'Hard' if demo else 'Dry','cycle_phase':phase,'idle_seconds':3 if phase=='RETURN' and tick%7==0 else 0,'fuel_per_cycle_l':round((18+load*.06)/max(1,1+(tick%5)),2),'unusual_pattern':bool(demo and tick%41==0),'gps_x':42+tick*.01,'gps_y':18+tick*.005}
@app.get('/work/sessions/{id}/telemetry')
def telemetry(id:str): return rows('SELECT * FROM sensor_events WHERE session_id=? ORDER BY timestamp DESC LIMIT 40',(id,)) or [telemetry_value(id,i) for i in range(12)]
# Friendly workflow aliases used by the prototype walkthrough.
@app.post('/sessions/work/start')
def workflow_work_start(x:SessionIn):
    s=create_session(x); return work_start(s['session_id'])
@app.get('/sessions/work/{id}/live')
def workflow_work_live(id:str): return telemetry(id)
@app.post('/sessions/work/{id}/complete')
def workflow_work_complete(id:str): return work_complete(id)
def latest_telemetry(sid): return telemetry_value(sid,12)
@app.post('/work/sessions/{id}/complete')
def work_complete(id:str):
    s=work_session(id); score=row('SELECT * FROM performance_scores WHERE session_id=?',(id,))
    if not score: score={'overall_score':58,'safety':72,'cycle_efficiency':61,'situational_awareness':70,'hazard_response':54,'control_precision':65}; execute('INSERT INTO performance_scores(session_id,control_precision,cycle_efficiency,safety,situational_awareness,hazard_response,overall_score) VALUES (?,?,?,?,?,?,?)',(id,65,61,72,70,54,58))
    execute('UPDATE work_sessions SET ended_at=?,actual_time_min=?,overall_score=?,safety_score=?,efficiency_score=?,status="Completed" WHERE session_id=?',(now(),606 if id=='WS-DEMO' else (work_session(id).get('actual_time_min') or 606),score['overall_score'],score['safety'],score['cycle_efficiency'],id))
    if s.get('task_id'): execute('UPDATE tasks SET status="Completed" WHERE task_id=?',(s['task_id'],))
    evaluation=evaluate_session(id)
    update_personal_baseline_from_work(id,evaluation)
    return {'session':work_session(id),'performance':score,'evaluation':evaluation,'next':'reflect'}
def update_personal_baseline_from_work(session_id, evaluation):
    session=work_session(session_id)
    if not session or session_id=='WS-DEMO' or float(evaluation.get('overall_score',0))<60: return
    operator_id=session['operator_id']; scenario_id=evaluation.get('scenario_id') or scenario_id_for_session(session_id)
    current=get_personal_baseline(operator_id,scenario_id); n=int(current.get('sample_count') or 0); count=n+1
    performance=evaluation.get('current_performance',{})
    actual=float(performance.get('task_time_hours') or 0)
    cycle=float(performance.get('cycle_time_sec') or current.get('average_cycle_time_sec',140))
    hazard=float(performance.get('hazard_response_sec') or current.get('average_hazard_response_sec',2))
    efficiency=float(performance.get('efficiency') or current.get('average_efficiency',80))
    safety=float(performance.get('safety') or current.get('average_safety',90))
    precision=float(performance.get('control_precision') or current.get('average_control_precision',80))
    values=(
        (float(current.get('average_task_time_hours',actual))*n+actual)/count,
        (float(current.get('average_cycle_time_sec',cycle))*n+cycle)/count,
        (float(current.get('average_hazard_response_sec',hazard))*n+hazard)/count,
        (float(current.get('average_efficiency',efficiency))*n+efficiency)/count,
        (float(current.get('average_safety',safety))*n+safety)/count,
        (float(current.get('average_control_precision',precision))*n+precision)/count,
        (float(current.get('consistency_score',80))*n+float(evaluation.get('overall_score',80)))/count,
        count, now())
    existing=row('SELECT baseline_id FROM personal_operator_baselines WHERE operator_id=? AND scenario_id=?',(operator_id,scenario_id))
    if existing:
        execute('UPDATE personal_operator_baselines SET average_task_time_hours=?,average_cycle_time_sec=?,average_hazard_response_sec=?,average_efficiency=?,average_safety=?,average_control_precision=?,consistency_score=?,sample_count=?,updated_at=? WHERE baseline_id=?',(*values,existing['baseline_id']))
    else:
        execute('INSERT INTO personal_operator_baselines(operator_id,scenario_id,average_task_time_hours,average_cycle_time_sec,average_hazard_response_sec,average_efficiency,average_safety,average_control_precision,consistency_score,sample_count,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(operator_id,scenario_id,*values))

def fallback_reflection(text):
    return FallbackLLMProvider().analyze(text)
@app.post('/reflections')
def reflection(x:ReflectionIn):
    # Objective evaluation is deliberately completed before any reflection analysis.
    evaluation=evaluate_session(x.session_id)
    if not x.text.strip(): raise HTTPException(400,'Reflection text is required')
    analysis=get_provider().analyze(x.text) if (os.getenv('LLM_API_KEY') or os.getenv('OPENROUTER_API_KEY')) else fallback_reflection(x.text)
    rid=f'RF-{int(datetime.now().timestamp())}'
    s=work_session(x.session_id)
    execute('INSERT OR REPLACE INTO reflections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,x.session_id,s['operator_id'],x.text,analysis['self_confidence'],analysis['perceived_performance'],analysis['perceived_difficulty'],analysis['hazard_awareness'],analysis['summary'],now(),json.dumps(analysis['strengths']),json.dumps(analysis['weaknesses']),json.dumps(analysis['mentioned_hazards'])))
    objective=evaluation['overall_score']; gap=calculate_calibration_gap(objective,analysis['self_confidence']); state=classify_operator_state(objective,analysis['self_confidence'])
    if state=='BLIND_SPOT': explanation='Your measured performance was below the expected range, while your self-assessment indicated high confidence.'
    elif state=='UNDERCONFIDENT': explanation='Your measured performance was strong, while your self-assessment was more cautious than the evidence.'
    elif state=='AWARE_DEVELOPING': explanation='Your self-assessment recognized that this task still needs development.'
    else: explanation='Your self-assessment is aligned with the objective performance evidence.'
    execute('INSERT INTO calibration_results(session_id,objective_score,self_confidence,calibration_gap,state,explanation) VALUES (?,?,?,?,?,?)',(x.session_id,objective,analysis['self_confidence'],gap,state,explanation))
    next_step=recommendation(s['operator_id'],state=state,objective=objective)
    return {'reflection':analysis,'objective_performance':objective,'calibration_gap':gap,'state':state,'explanation':explanation,'evaluation':evaluation,'recommendation':next_step}
def job_session(job_id, operator_id=None):
    requested=job_id; task_row=task(requested); owner=operator_id or task_row['operator_id']
    session=row('SELECT * FROM work_sessions WHERE task_id=? AND operator_id=? ORDER BY started_at DESC LIMIT 1',(canonical_task_id(requested),owner))
    return task_row, session

def seed_for_task(task_row):
    return int(task_row.get('demo_seed') or (DEMO_TASK_SEED if task_row.get('task_id')=='T-002' else random.randint(1000,999999)))

def api_grade(evaluation, analysis, recommendation_result):
    scores=evaluation.get('current_performance',{})
    jev={k:v for k,v in analysis.items() if k in ('jev_scores','expertise_level')}
    return {'objective_score':evaluation['overall_score'],'overall_score':evaluation['overall_score'],'benchmark_status':evaluation['status'],'benchmark_deviation_pct':evaluation['benchmark_deviation_pct'],'personal_deviation_pct':evaluation['personal_deviation_pct'],'safety_score':scores.get('safety'),'efficiency_score':scores.get('efficiency'),'hazard_response_score':scores.get('hazard_response_score'),'scores':scores,'jev_scores':analysis.get('jev_scores',{}),'expertise_level':analysis.get('expertise_level'),'needs_review':bool(analysis.get('needs_review',False)),'weakest_subscore':min((('safety',scores.get('safety',100)),('efficiency',scores.get('efficiency',100)),('hazard_response',scores.get('hazard_response_score',100))),key=lambda item:item[1])[0],'coaching':evaluation.get('explanation'),'recommended_module':recommendation_result.get('recommended_scenario'),'objective_evaluation':evaluation}

@app.post('/api/jobs/{job_id}/start')
def api_start_job(job_id:str, request:Request):
    operator_id=operator_from_request(request)
    try: task_row=task(job_id)
    except HTTPException: return api_error(404,'not_found','Unknown task')
    if task_row['operator_id']!=operator_id: return api_error(404,'not_found','Task does not belong to operator')
    seed=seed_for_task(task_row); options=json.loads(task_row.get('job_options_json') or '{}')
    session_id=f"JOB-{int(datetime.now().timestamp()*1000)}-{random.randint(100,999)}"
    prediction=predict_minutes(task_row)
    execute('INSERT INTO work_sessions(session_id,operator_id,machine_id,task_id,started_at,predicted_time_min,status,data_json,telemetry_seed,job_options_json) VALUES (?,?,?,?,?,?,?,?,?,?)',(session_id,operator_id,task_row['machine_id'],task_row['task_id'],now(),prediction['predicted_minutes'],'In Progress',json.dumps({'job_id':job_id}),seed,json.dumps(options)))
    execute('UPDATE tasks SET status="In Progress" WHERE task_id=?',(task_row['task_id'],))
    return {'job_id':job_id,'session_id':session_id,'operator_id':operator_id,'started_at':now(),'seed':seed,'options':options or {'duration_min':task_row['baseline_duration_min'],'weather':task_row.get('weather','clear'),'skill':task_row.get('operator_skill','intermediate')},'predicted_minutes':prediction['predicted_minutes']}

@app.post('/api/incidents', status_code=201)
def api_incident(x:IncidentIn, request:Request):
    operator_id=operator_from_request(request); session_id=x.session_id
    if x.job_id:
        try: task_row=task(x.job_id)
        except HTTPException: return api_error(404,'not_found','Unknown job')
        if task_row['operator_id']!=operator_id: return api_error(404,'not_found','Job does not belong to operator')
        found=row('SELECT session_id FROM work_sessions WHERE task_id=? AND operator_id=? ORDER BY started_at DESC LIMIT 1',(task_row['task_id'],operator_id)); session_id=found['session_id'] if found else None
    if not session_id or not row('SELECT session_id FROM work_sessions WHERE session_id=? AND operator_id=?',(session_id,operator_id)):
        return api_error(404,'not_found','Unknown work session')
    incident_id=f"INC-{int(datetime.now().timestamp()*1000)}-{random.randint(100,999)}"; timestamp=x.timestamp or now(); code=(x.code or x.type or 'MANUAL_INCIDENT').upper(); severity=x.severity.upper()
    execute('INSERT INTO incidents VALUES (?,?,?,?,?,?,?)',(incident_id,session_id,code,severity,timestamp,'OPEN',x.resolution))
    return {'incident_id':incident_id,'session_id':session_id,'code':code,'severity':severity,'status':'OPEN','timestamp':timestamp}

@app.post('/api/jobs/{job_id}/review')
def api_review_job(job_id:str, x:ReviewIn, request:Request):
    operator_id=operator_from_request(request)
    try: task_row=task(job_id)
    except HTTPException: return api_error(404,'not_found','Unknown job')
    if task_row['operator_id']!=operator_id: return api_error(404,'not_found','Job does not belong to operator')
    session= row('SELECT * FROM work_sessions WHERE task_id=? AND operator_id=? ORDER BY started_at DESC LIMIT 1',(task_row['task_id'],operator_id))
    if not session:
        # Demo shortcut: a review can be submitted even if the job start was skipped.
        started=api_start_job(job_id,request)
        session=row('SELECT * FROM work_sessions WHERE session_id=?',(started['session_id'],))
    actual_minutes=float(x.actual_minutes if x.actual_minutes is not None else (session.get('actual_time_min') or session.get('predicted_time_min') or task_row.get('baseline_duration_min') or 45))
    execute('UPDATE work_sessions SET actual_time_min=?,ended_at=?,status="Completed" WHERE session_id=?',(actual_minutes,now(),session['session_id']))
    execute('UPDATE tasks SET status="Completed" WHERE task_id=?',(task_row['task_id'],))
    session=row('SELECT * FROM work_sessions WHERE session_id=?',(session['session_id'],))
    # First and only objective calculation in this flow.
    evaluation=evaluate_session(session['session_id'], context=x.telemetry_summary or None, requested_operator=operator_id)
    if os.getenv('ML_FORCE_DOWN')=='1':
        execute('INSERT OR REPLACE INTO reflections(reflection_id,session_id,operator_id,text,created_at) VALUES (?,?,?,?,?)',(f'RF-{int(datetime.now().timestamp()*1000)}',session['session_id'],operator_id,x.transcript,now()))
        return JSONResponse(status_code=202,content={'saved':True,'grade':None,'needs_review':True,'message':'Saved. Grading when grader is back.','session_id':session['session_id']})
    analysis=get_provider().analyze(x.transcript) if (os.getenv('LLM_API_KEY') or os.getenv('OPENROUTER_API_KEY')) else fallback_reflection(x.transcript)
    reflection_id=f'RF-{int(datetime.now().timestamp()*1000)}'
    execute('INSERT OR REPLACE INTO reflections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',(reflection_id,session['session_id'],operator_id,x.transcript,analysis['self_confidence'],analysis['perceived_performance'],analysis['perceived_difficulty'],analysis['hazard_awareness'],analysis['summary'],now(),json.dumps(analysis['strengths']),json.dumps(analysis['weaknesses']),json.dumps(analysis['mentioned_hazards'])))
    gap=calculate_calibration_gap(evaluation['overall_score'],analysis['self_confidence']); state=classify_operator_state(evaluation['overall_score'],analysis['self_confidence']); explanation='Your measured performance was below the expected range, while your self-assessment indicated high confidence.' if state=='BLIND_SPOT' else 'Your self-assessment is aligned with the objective performance evidence.'
    execute('INSERT INTO calibration_results(session_id,objective_score,self_confidence,calibration_gap,state,explanation) VALUES (?,?,?,?,?,?)',(session['session_id'],evaluation['overall_score'],analysis['self_confidence'],gap,state,explanation))
    next_step=recommendation(operator_id,state,evaluation['overall_score']); grade=api_grade(evaluation,analysis,next_step)
    return {'saved':True,'session_id':session['session_id'],'grade':grade,'reflection':analysis,'calibration_gap':gap,'state':state,'recommendation':next_step,'needs_review':grade['needs_review']}

def sim_module_scenario(module_id):
    mapping={'controls-basics':'SCN-BUCKET-01','safe-startup':'SCN-PROX-01','efficient-loading':'SCN-EFF-01','wet-trenching':'SCN-PROX-01','hazard-callout':'SCN-HAUL-01'}
    return mapping.get(module_id)

@app.get('/api/sim-attempts')
def api_sim_attempts(request:Request):
    return {'attempts':rows('SELECT * FROM sim_attempts WHERE operator_id=? ORDER BY created_at DESC',(operator_from_request(request),))}
@app.post('/api/sim-attempts', status_code=201)
def api_sim_attempt(x:SimAttemptIn, request:Request):
    if x.module_id not in SUPPORTED_SIM_MODULES: return api_error(400,'unknown_module','Unknown simulation module')
    operator_id=operator_from_request(request); module=SUPPORTED_SIM_MODULES[x.module_id]; passed=x.passed if x.passed is not None else x.score>=module['pass_score']; attempt_id=f'SIM-{int(datetime.now().timestamp()*1000)}-{random.randint(100,999)}'
    if passed:
        scenario_id=sim_module_scenario(x.module_id) or 'SCN-PROX-01'
        training_complete(attempt_id,{'scenario_id':scenario_id,'operator_id':operator_id,'score':x.score,'hazard_response_sec':1.8 if x.module_id in ('safe-startup','hazard-callout') else 2.1,'efficiency_score':x.score,'safety_score':x.score,'control_events':x.objectives.get('events',[]) if isinstance(x.objectives,dict) else []})
    execute('INSERT INTO sim_attempts VALUES (?,?,?,?,?,?,?,?,?)',(attempt_id,operator_id,x.module_id,x.score,int(passed),x.duration_sec,x.penalties,json.dumps(x.objectives),now()))
    return {'attempt_id':attempt_id,'module_id':x.module_id,'score':x.score,'passed':passed,'pass_score':module['pass_score'],'baseline_updated':bool(passed)}
@app.get('/api/sim-modules')
def api_sim_modules(): return [{'module_id':key,**value} for key,value in SUPPORTED_SIM_MODULES.items()]

def detect_operator_anomalies(operator_id='OP-001'):
    anomalies=[]
    for s in rows('SELECT w.*,p.safety_score,p.efficiency_score FROM work_sessions w LEFT JOIN (SELECT session_id,safety AS safety_score,cycle_efficiency AS efficiency_score FROM performance_scores) p ON p.session_id=w.session_id WHERE w.operator_id=?',(operator_id,)):
        features={'actual_time_min':s.get('actual_time_min') or 0,'efficiency':s.get('efficiency_score') or 0,'safety':s.get('safety_score') or 0}
        sensor=row('SELECT AVG(idle_seconds) AS idle_seconds,AVG(fuel_per_cycle_l) AS fuel_per_cycle_l,MIN(seatbelt_fastened) AS seatbelt_fastened,MAX(unusual_pattern) AS unusual_pattern FROM sensor_events WHERE session_id=?',(s['session_id'],)) or {}
        features.update({'idle_seconds':round(float(sensor.get('idle_seconds') or 0),1),'fuel_per_cycle_l':round(float(sensor.get('fuel_per_cycle_l') or 0),2)})
        if float(features['efficiency'])<55 or features['idle_seconds']>=IDLE_SECONDS_THRESHOLD: anomalies.append({'kind':'excessive_idling','severity':'medium','session_id':s['session_id'],'message':'Idle/low-efficiency time is unusually high.','features':features})
        if float(features['safety'])<65 or sensor.get('seatbelt_fastened')==0: anomalies.append({'kind':'unbelted_operation','severity':'high','session_id':s['session_id'],'message':'Safety behavior is outside the normal operating pattern.','features':features})
        if features['fuel_per_cycle_l']>=FUEL_PER_CYCLE_THRESHOLD_L: anomalies.append({'kind':'high_fuel_per_cycle','severity':'medium','session_id':s['session_id'],'message':'Fuel used per load cycle is above the operator pattern.','features':features})
        if float(features['actual_time_min'])>600 or sensor.get('unusual_pattern')==1: anomalies.append({'kind':'unusual_pattern','severity':'medium','session_id':s['session_id'],'message':'Task duration and cycle performance differ materially from the operator pattern.','features':features})
    return anomalies
@app.get('/api/anomalies')
def api_anomalies(request:Request):
    if os.getenv('ML_FORCE_DOWN')=='1': return api_error(503,'ml_unavailable','Anomaly model is unavailable')
    operator_id=operator_from_request(request); found=detect_operator_anomalies(operator_id)
    for item in found: execute('INSERT OR REPLACE INTO anomalies VALUES (?,?,?,?,?,?,?,?)',(f"{operator_id}-{item['session_id']}-{item['kind']}",operator_id,item['session_id'],item['kind'],item['severity'],item['message'],json.dumps(item['features']),now()))
    return {'operator_id':operator_id,'anomalies':found,'available':True}

@app.get('/reflections/{session_id}')
def get_reflection(session_id:str): return row('SELECT * FROM reflections WHERE session_id=? ORDER BY created_at DESC',(session_id,)) or row('SELECT * FROM reflections WHERE session_id="WS-DEMO"')
@app.post('/reflections/{session_id}/analyze')
def analyze(session_id:str, x:dict): return reflection(ReflectionIn(session_id=session_id,text=x.get('text','')))
@app.get('/performance/{operator_id}/summary')
def perf(operator_id:str): return op_summary(operator_id)
@app.get('/performance/{operator_id}/trends')
def trends(operator_id:str):
    comparison=benchmark_comparison(operator_id); evaluations=comparison.get('comparisons',[]); safety=row('SELECT AVG(safety) AS value FROM performance_scores ps JOIN work_sessions w ON w.session_id=ps.session_id WHERE w.operator_id=?',(operator_id,)); calibration=row('SELECT AVG(calibration_gap) AS value FROM calibration_results c JOIN work_sessions w ON w.session_id=c.session_id WHERE w.operator_id=?',(operator_id,)); compliance=round(sum(1 for x in evaluations if x['status']=='WITHIN_EXPECTATION')/max(1,len(evaluations))*100,1)
    return [{'label':'Benchmark compliance','you':compliance,'average':80},{'label':'Personal consistency','you':round(max(0,100-abs(float(comparison.get('review_required',0)))),1),'average':74},{'label':'Safety','you':round(float(safety['value'] or 0),1),'average':90},{'label':'Calibration','you':round(max(0,100-float(calibration['value'] or 0)),1),'average':76}]
@app.get('/performance/{operator_id}/calibration')
def performance_calibration(operator_id:str): return rows('SELECT c.*,w.operator_id FROM calibration_results c LEFT JOIN work_sessions w ON w.session_id=c.session_id WHERE w.operator_id=? ORDER BY c.calibration_id DESC',(operator_id,))
@app.get('/calibration/{operator_id}')
def calibration(operator_id:str): return rows('SELECT * FROM calibration_results ORDER BY calibration_id DESC')
@app.get('/calibration/{operator_id}/latest')
def calibration_latest(operator_id:str): return row('SELECT * FROM calibration_results ORDER BY calibration_id DESC')
def recommendation(operator_id='OP-001', state=None, objective=58):
    cal=row('SELECT c.* FROM calibration_results c LEFT JOIN work_sessions w ON w.session_id=c.session_id WHERE w.operator_id=? ORDER BY c.calibration_id DESC',(operator_id,)); pe=row('SELECT p.* FROM performance_evaluations p JOIN work_sessions w ON w.session_id=p.session_id WHERE w.operator_id=? ORDER BY p.evaluation_id DESC',(operator_id,)); score=row('SELECT ps.* FROM performance_scores ps JOIN work_sessions w ON w.session_id=ps.session_id WHERE w.operator_id=? ORDER BY ps.score_id DESC',(operator_id,)); state=state or (cal['state'] if cal else 'BLIND_SPOT')
    priority=5; sid='SCN-EFF-01'; reason='Build consistency in your cycle efficiency with focused adaptive practice.'
    if state=='BLIND_SPOT':
        priority=1; sid='SCN-PROX-01'; reason='Your confidence was high while measured hazard response and task performance were below the expected range. Additional coaching is recommended.'
    elif score and (float(score.get('safety') or 100)<80 or float(score.get('hazard_response') or 100)<65):
        priority=2; sid='SCN-PROX-01'; reason='Safety and hazard-response evidence is the weakest sub-score. Practice recognizing and responding to proximity hazards.'
    elif pe and pe['status'] in ('SIGNIFICANTLY_ABOVE_EXPECTATION','SEVERE_DEVIATION'):
        priority=3; sid='SCN-EFF-01'; reason='Task time is above the context-adjusted benchmark. Review cycle rhythm and efficient loading before the next work session.'
    elif pe and abs(float(pe.get('personal_deviation_pct') or 0))>=20:
        priority=4; sid='SCN-EFF-01'; reason='Your current pattern differs materially from your personal baseline. Build consistency in cycle efficiency.'
    sc=scenario(sid); latest=row('SELECT recommendation_id FROM recommendations WHERE operator_id=? AND scenario_id=? AND reason=? ORDER BY recommendation_id DESC',(operator_id,sid,reason))
    if not latest: execute('INSERT INTO recommendations(operator_id,scenario_id,reason,target_skill,priority,created_at) VALUES (?,?,?,?,?,?)',(operator_id,sid,reason,sc['target_skill'],priority,now()))
    return {'scenario':sc,'recommended_scenario':sc['name'],'reason':reason,'target_skill':sc['target_skill'],'expected_improvement':'15% faster hazard response' if sid=='SCN-PROX-01' else '10% more consistent cycle efficiency','state':state,'priority':priority}
@app.get('/recommendations/{operator_id}')
def recs(operator_id:str): return recommendation(operator_id)
@app.get('/recommendations/current')
def current_rec(): return recommendation()
@app.post('/recommendations/generate')
def gen_rec(x:dict={}): return recommendation(x.get('operator_id','OP-001'))
@app.get('/reports/summary')
def report_summary():
    demo=evaluate_session('WS-DEMO'); evaluations=rows('SELECT * FROM performance_evaluations');
    task_counts=row('SELECT COUNT(*) AS assigned,SUM(CASE WHEN status="Completed" THEN 1 ELSE 0 END) AS completed FROM tasks WHERE operator_id="OP-001"') or {'assigned':0,'completed':0}
    totals=row('SELECT COALESCE(SUM(actual_time_min),0) AS minutes,COALESCE(AVG(actual_time_min),0) AS average FROM work_sessions WHERE operator_id="OP-001" AND status="Completed"') or {'minutes':0,'average':0}
    score_avgs=row('SELECT COALESCE(AVG(safety),0) AS safety,COALESCE(AVG(cycle_efficiency),0) AS efficiency FROM performance_scores') or {'safety':0,'efficiency':0}
    training=row('SELECT COUNT(*) AS total,COALESCE(SUM(passed),0) AS passed FROM training_runs WHERE operator_id="OP-001"') or {'total':0,'passed':0}
    sensors=row('SELECT COUNT(*) AS total,COALESCE(SUM(seatbelt_fastened),0) AS belted FROM sensor_events') or {'total':0,'belted':0}
    compliant=sum(1 for x in evaluations if x['status']=='WITHIN_EXPECTATION'); avg_personal=round(sum(x['personal_deviation_pct'] for x in evaluations)/len(evaluations),1) if evaluations else 0
    return {'operating_hours':round(float(totals['minutes'])/60,1),'tasks_completed':int(task_counts['completed'] or 0),'tasks_assigned':int(task_counts['assigned'] or 0),'safety_incidents':len(rows('SELECT * FROM hazard_events WHERE severity IN ("high","critical")')),'machine_utilization':round(min(100,float(totals['minutes'])/(max(1,int(task_counts['assigned'] or 1))*60)*100),1),'training_completion':round(float(training['passed'])/max(1,float(training['total']))*100,1),'average_task_time':round(float(totals['average']),1),'average_safety_score':round(float(score_avgs['safety']),1),'average_efficiency':round(float(score_avgs['efficiency']),1),'seatbelt_compliance':round(float(sensors['belted'])/max(1,float(sensors['total']))*100,1),'proximity_alerts':len(rows('SELECT * FROM hazard_events')),'calibration_gaps':rows('SELECT calibration_gap,state FROM calibration_results ORDER BY calibration_id DESC'),'blind_spots_discovered':len(rows('SELECT * FROM calibration_results WHERE state="BLIND_SPOT"')),'benchmark_compliance':{'within_expectation':compliant,'review_required':len(evaluations)-compliant},'average_personal_deviation_pct':avg_personal,'recommended_scenario':recommendation('OP-001')['recommended_scenario'],'context_adjusted_performance':evaluations[:8],'comparison_labels':['Benchmark','Personal baseline','Actual'],'demo_comparison':{'benchmark_min':demo['context_adjusted_benchmark']['adjusted_min'],'benchmark_max':demo['context_adjusted_benchmark']['adjusted_max'],'personal_baseline_hours':demo['personal_baseline']['average_task_time_hours'],'actual_hours':demo['current_performance']['task_time_hours'],'benchmark_deviation_pct':demo['benchmark_deviation_pct'],'personal_deviation_pct':demo['personal_deviation_pct']}}
@app.get('/reports/safety')
def safety_report():
    summary=report_summary(); return {'report':'safety','seatbelt_compliance':summary['seatbelt_compliance'],'proximity_alerts':summary['proximity_alerts'],'safety_incidents':summary['safety_incidents'],'benchmark_safety_breaches':len(rows('SELECT * FROM performance_scores WHERE safety<95')),'blind_spots':summary['blind_spots_discovered']}
@app.get('/reports/training')
def training_report():
    total=row('SELECT COUNT(*) AS count FROM training_runs'); passed=row('SELECT COUNT(*) AS count FROM training_runs WHERE passed=1'); return {'report':'training','total_runs':total['count'] if total else 0,'passed_runs':passed['count'] if passed else 0,'completion_pct':round((passed['count']/total['count'])*100,1) if total and total['count'] else 0,'recommended_scenario':recommendation()['recommended_scenario']}
@app.get('/reports/machines')
def machine_report():
    return {'report':'machines','machines':rows('SELECT machine_id,model,domain,status,engine_hours,fuel FROM machines ORDER BY model'),'comparison':report_summary()['demo_comparison']}
@app.get('/reports/{kind}')
def report(kind:str): return {'report':kind,'data':report_summary(),'generated_at':now()}
@app.get('/reports/export.csv')
def export_csv():
    data=report_summary(); output=io.StringIO(); w=csv.writer(output); w.writerow(['metric','value']); w.writerows(data.items()); return StreamingResponse(iter([output.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=smart-operator-report.csv'})
def persist_live_telemetry(session_id,event,alerts):
    execute('INSERT INTO sensor_events(session_id,timestamp,ambient_temp_c,humidity_pct,wind_speed_kmh,fuel_level_pct,fuel_rate_lph,engine_rpm,engine_temp_c,hydraulic_load_pct,payload_pct,seatbelt_fastened,proximity_distance_m,visibility,soil_type,ground_condition,cycle_phase,tilt_deg,weather,idle_seconds,fuel_per_cycle_l,unusual_pattern,gps_x,gps_y) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(session_id,event['timestamp'],event['ambient_temp_c'],event['humidity_pct'],event['wind_speed_kmh'],event['fuel_level_pct'],event['fuel_rate_lph'],event['engine_rpm'],event['engine_temp_c'],event['hydraulic_load_pct'],event['payload_pct'],int(event['seatbelt_fastened']),event['proximity_distance_m'],event['visibility'],event['soil_type'],event['ground_condition'],event['cycle_phase'],event.get('tilt_deg',0),event.get('weather','clear'),event.get('idle_seconds',0),event.get('fuel_per_cycle_l',0),int(event.get('unusual_pattern',False)),event['gps_x'],event['gps_y']))
    for alert in alerts:
        alert_id=f'LIVE-{session_id}-{int(datetime.now().timestamp())}-{alert["type"]}'
        if alert['status']=='OPEN': execute('INSERT OR IGNORE INTO hazard_events(hazard_id,session_id,hazard_type,severity,trigger_time,acknowledged,suppressed,escalated,resolved) VALUES (?,?,?,?,?,?,?,?,?)',(alert_id,session_id,alert['type'].lower(),alert['severity'],event['timestamp'],0,0,0,0))
        if alert['type'] in ('SEATBELT','PROXIMITY','TILT','WEATHER'): execute('INSERT OR IGNORE INTO incidents VALUES (?,?,?,?,?, ?,?)',(alert_id,session_id,alert['type'],alert['severity'],event['timestamp'],alert['status'],alert['resolution']))

@app.get('/work/sessions/{id}/safety')
def session_safety(id:str): return rows('SELECT * FROM incidents WHERE session_id=? ORDER BY timestamp DESC',(id,))

@app.websocket('/ws/work/{session_id}')
async def ws_work(ws:WebSocket,session_id:str):
    await ws.accept(); tick=0; previous={}
    try:
        while tick<180:
            event=telemetry_value(session_id,tick); alerts=evaluate_safety(previous,event); persist_live_telemetry(session_id,event,alerts); event['safety_events']=alerts; await ws.send_json(event); previous=event; tick+=1; await asyncio.sleep(1)
    except WebSocketDisconnect: pass

if __name__=='__main__':
    import uvicorn; uvicorn.run(app,host='0.0.0.0',port=8000)