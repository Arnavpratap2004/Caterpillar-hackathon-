import type {AdaptiveRecommendation,HomeSummary,PerformanceEvaluation,PersonalBaseline,ReportSummary,Scenario,Task,TaskBenchmark,TrainingEvent,Machine,SimAttempt,Anomaly} from './types';
const BASE=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export async function api<T=unknown>(path:string, options?:RequestInit):Promise<T>{const r=await fetch(`${BASE}${path}`,{...options,headers:{'Content-Type':'application/json',...(options?.headers||{})},cache:'no-store'});if(!r.ok){let message=`Request failed (${r.status})`;try{const body=await r.json();message=body?.error?.message||body?.detail||message}catch{}throw new Error(message)}return r.json()}
export const getHome=()=>Promise.all([api<HomeSummary>('/operators/OP-001/summary'),api<Task[]>('/tasks/today'),api<Machine[]>('/machines'),api<AdaptiveRecommendation>('/recommendations/current')]);
export const getEvaluation=(sessionId='WS-DEMO')=>api<PerformanceEvaluation>(`/performance/evaluate/${sessionId}`);
export const getTasks=()=>api<Task[]>('/tasks/today');
export const getContractTasks=(date?:string)=>api<{tasks:Task[];date:string}>(`/api/tasks${date?`?date=${encodeURIComponent(date)}`:''}`);
export const getScenarios=()=>api<Scenario[]>('/training/scenarios');
export const getReports=()=>api<ReportSummary>('/reports/summary');
export const getBenchmarks=()=>api<TaskBenchmark[]>('/benchmarks');
export const getPersonalBaseline=(operatorId='OP-001',scenarioId='SCN-PROX-01')=>api<PersonalBaseline>(`/performance/${operatorId}/personal-baseline?scenario_id=${scenarioId}`);
export const getBenchmarkComparison=(operatorId='OP-001')=>api(`/performance/${operatorId}/benchmark-comparison`);
export const startWork=(task_id='T-001',machine_id='M-320')=>api<{session_id:string}>('/work/sessions',{method:'POST',body:JSON.stringify({operator_id:'OP-001',machine_id,task_id})}).then((s)=>api<{session_id:string}>(`/work/sessions/${s.session_id}/start`,{method:'POST'}));
export const finishWork=(id:string)=>api(`/work/sessions/${id}/complete`,{method:'POST'});
export const analyze=(session_id:string,text:string)=>api<import('./types').ReflectionResponse>('/reflections',{method:'POST',body:JSON.stringify({session_id,text})});
export async function completeTraining(scenario_id:string,control_events:TrainingEvent[]=[]){const run=await api<{run_id:string}>('/training/runs',{method:'POST',body:JSON.stringify({scenario_id,operator_id:'OP-001'})});return api(`/training/runs/${run.run_id}/complete`,{method:'POST',body:JSON.stringify({scenario_id,operator_id:'OP-001',score:86,hazard_response_sec:1.9,efficiency_score:88,safety_score:94,control_events})})}
export const reviewJob=(jobId:string,transcript:string,actualMinutes?:number)=>api(`/api/jobs/${encodeURIComponent(jobId)}/review`,{method:'POST',body:JSON.stringify({transcript,actual_minutes:actualMinutes})});
export const saveSimAttempt=(moduleId:string,score:number,durationSec:number,penalties=0,objectives:Record<string,unknown>={})=>api('/api/sim-attempts',{method:'POST',body:JSON.stringify({module_id:moduleId,score,duration_sec:durationSec,penalties,objectives})});
export const getSimAttempts=()=>api<{attempts:SimAttempt[]}>('/api/sim-attempts');
export const getAnomalies=()=>api<{anomalies:Anomaly[]}>('/api/anomalies');
export const createIncident=(sessionId:string,code='MANUAL_PROXIMITY')=>api('/api/incidents',{method:'POST',body:JSON.stringify({session_id:sessionId,code,severity:'high'})});
export {BASE};
